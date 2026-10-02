"""In-process fake OIDC provider. Educational contract checks, NOT an auth server."""
import argparse
import asyncio
import base64
import hashlib
import json
from pathlib import Path
import secrets
import time
from urllib.parse import parse_qs, urlencode, urlsplit

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
import httpx
import jwt

ISSUER = 'https://provider.study.invalid'
CLIENT = 'study-client'
REDIRECT = 'https://app.study.invalid/callback'


def challenge(verifier):
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()


def provider():
    app = FastAPI()
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    codes = {}

    @app.get('/authorize')
    async def authorize(request: Request):
        p = request.query_params
        if (p.get('client_id') != CLIENT or p.get('redirect_uri') != REDIRECT
                or p.get('response_type') != 'code' or p.get('code_challenge_method') != 'S256'
                or not p.get('code_challenge') or not p.get('state') or not p.get('nonce')
                or 'openid' not in p.get('scope', '').split()):
            return JSONResponse({'error': 'invalid_request'}, status_code=400)
        if p.get('deny') == '1':
            return RedirectResponse(REDIRECT + '?' + urlencode({'error': 'access_denied', 'state': p['state']}), 302)
        code = secrets.token_urlsafe(32)
        codes[code] = {'challenge': p['code_challenge'], 'nonce': p['nonce'], 'expires': time.time()+60}
        # Fixed fictional account; no password or real user authentication performed.
        return RedirectResponse(REDIRECT + '?' + urlencode({'code': code, 'state': p['state']}), 302)

    @app.post('/token')
    async def token(request: Request):
        p = {k: v[0] for k,v in parse_qs((await request.body()).decode()).items()}
        item = codes.pop(p.get('code', ''), None)  # consume on attempted exchange
        if (p.get('grant_type') != 'authorization_code' or p.get('client_id') != CLIENT
                or p.get('redirect_uri') != REDIRECT or item is None
                or item['expires'] <= time.time()
                or not secrets.compare_digest(item['challenge'], challenge(p.get('code_verifier','')))):
            return JSONResponse({'error': 'invalid_grant'}, status_code=400)
        now = int(time.time())
        claims = {'iss': ISSUER, 'aud': CLIENT, 'sub': 'fictional-user-1',
                  'iat': now, 'exp': now+60, 'nonce': item['nonce']}
        return {'token_type': 'Bearer', 'access_token': secrets.token_urlsafe(32),
                'id_token': jwt.encode(claims, key, algorithm='RS256')}
    return app, key


class Login:
    def __init__(self, client, public_key):
        self.client = client
        self.public_key = public_key  # pinned trusted provider key, no discovery/JWKS in this lab
        self.pending = {}

    async def start(self, browser, deny=False):
        state, verifier, nonce = [secrets.token_urlsafe(32) for _ in range(3)]
        self.pending[state] = {'browser': browser, 'verifier': verifier, 'nonce': nonce, 'expires': time.time()+60}
        p = {'client_id': CLIENT, 'redirect_uri': REDIRECT, 'response_type': 'code',
             'scope': 'openid', 'state': state, 'nonce': nonce,
             'code_challenge': challenge(verifier), 'code_challenge_method': 'S256'}
        if deny:p['deny']='1'
        response = await self.client.get('/authorize', params=p)
        assert response.status_code == 302
        return {k:v[0] for k,v in parse_qs(urlsplit(response.headers['location']).query).items()}

    def verify(self, token, nonce):
        claims = jwt.decode(token, self.public_key, algorithms=['RS256'], audience=CLIENT,
                            issuer=ISSUER, options={'require':['iss','aud','sub','iat','exp','nonce']})
        if not isinstance(claims['sub'], str) or not claims['sub']:
            raise ValueError('bad subject')
        if not secrets.compare_digest(claims['nonce'], nonce):
            raise ValueError('nonce mismatch')
        return claims

    async def callback(self, browser, params):
        state = params.get('state','')
        item = self.pending.get(state)
        if item is None or item['browser'] != browser or item['expires'] <= time.time():
            raise ValueError('invalid transaction binding')
        del self.pending[state]
        if 'error' in params:
            raise ValueError('authorization denied')
        response = await self.client.post('/token', data={'grant_type':'authorization_code',
            'client_id':CLIENT, 'redirect_uri':REDIRECT, 'code':params.get('code',''),
            'code_verifier':item['verifier']})
        if response.status_code != 200:raise ValueError('exchange failed')
        claims = self.verify(response.json()['id_token'], item['nonce'])
        return (claims['iss'], claims['sub'])  # a real app would now rotate/create its session


async def run():
    app, key = provider()
    results = []
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ISSUER,
                                 follow_redirects=False) as client:
        login = Login(client, key.public_key())
        async def rejected(label, operation):
            try:await operation()
            except (ValueError, jwt.PyJWTError):results.append(label);return
            raise AssertionError(label+' was accepted')
        p = await login.start('browser-A')
        assert await login.callback('browser-A',p) == (ISSUER,'fictional-user-1')
        results.append('successful code+PKCE+ID-token verification')
        await rejected('callback replay rejected',lambda:login.callback('browser-A',p))
        p = await login.start('browser-A',deny=True)
        await rejected('user denial rejected',lambda:login.callback('browser-A',p))
        p = await login.start('browser-A'); altered=dict(p,state='unknown')
        await rejected('unknown state rejected',lambda:login.callback('browser-A',altered))
        await rejected('other browser binding rejected',lambda:login.callback('browser-B',p))
        login.pending[p['state']]['expires']=0
        await rejected('expired login transaction rejected',lambda:login.callback('browser-A',p))
        p = await login.start('browser-A')
        login.pending[p['state']]['verifier']='wrong'
        await rejected('wrong PKCE verifier rejected',lambda:login.callback('browser-A',p))
        p = await login.start('browser-A')
        v = login.pending[p['state']]['verifier']
        data={'grant_type':'authorization_code','client_id':CLIENT,'redirect_uri':REDIRECT,
              'code':p['code'],'code_verifier':v}
        first = await client.post('/token',data=data); assert first.status_code==200
        second = await client.post('/token',data=data); assert second.status_code==400
        results.append('authorization code replay rejected')
        p = await login.start('browser-A')
        data.update(code=p['code'],code_verifier=login.pending[p['state']]['verifier'],redirect_uri='https://evil.invalid')
        assert (await client.post('/token',data=data)).status_code==400
        results.append('token redirect URI mismatch rejected')
        bad = await client.get('/authorize',params={'client_id':CLIENT,'redirect_uri':'https://evil.invalid'})
        assert bad.status_code==400 and 'location' not in bad.headers
        results.append('unregistered authorize redirect rejected without redirect')
        now=int(time.time())
        claims={'iss':ISSUER,'aud':CLIENT,'sub':'fictional-user-1','iat':now,'exp':now+60,'nonce':'expected'}
        for label,changes in [('issuer',{'iss':'https://evil.invalid'}),('audience',{'aud':'other'}),
                               ('expiry',{'exp':now-10}),('nonce',{'nonce':'wrong'})]:
            encoded=jwt.encode(dict(claims,**changes),key,algorithm='RS256')
            try:login.verify(encoded,'expected')
            except (ValueError,jwt.PyJWTError):results.append('wrong '+label+' rejected')
            else:raise AssertionError(label)
        other=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        try:login.verify(jwt.encode(claims,other,algorithm='RS256'),'expected')
        except jwt.InvalidSignatureError:results.append('wrong signature rejected')
        else:raise AssertionError('signature')
    return {'transport':'in-process ASGITransport; fictional provider, pinned RSA public key',
            'versions':{'PyJWT':jwt.__version__,'httpx':httpx.__version__},
            'passed':len(results),'checks':results,
            'not_tested':['real identity verification','HTTPS/browser cookies','JWKS rotation/discovery',
                          'real provider compatibility','refresh tokens','production session storage']}


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():p.error('Choose new output path')
    result=asyncio.run(run())
    with args.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2))
