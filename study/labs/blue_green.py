"""Two local app processes + educational proxy; bounded blue/green checks."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time


def get(port, path='/'):
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
    try:
        c.request('GET',path,headers={'Connection':'close'})
        r=c.getresponse();data=json.loads(r.read());return r.status,data
    finally:c.close()


def worker(fd, version):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            if self.path!='/health':time.sleep(0.04)
            body=json.dumps({'version':version}).encode()
            self.send_response(200);self.send_header('Content-Length',str(len(body)))
            self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(body)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler,bind_and_activate=False)
    server.socket.close();server.socket=socket.socket(fileno=fd)
    server.server_address=server.socket.getsockname()
    server.serve_forever()


def run():
    processes=[];sockets=[]
    state={'target':None,'active':{},'seen_old':threading.Event()}
    guard=threading.Lock()
    result={'transport':'actual loopback HTTP/1.1; two app subprocesses; educational in-process proxy'}
    def start(version):
        s=socket.socket();s.bind(('127.0.0.1',0));s.listen(128);sockets.append(s)
        p=subprocess.Popen([sys.executable,__file__,'--worker-fd',str(s.fileno()),'--version',version],pass_fds=(s.fileno(),),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        processes.append(p);port=s.getsockname()[1]
        deadline=time.monotonic()+10
        while True:
            if p.poll() is not None:raise RuntimeError('worker startup failed')
            try:
                status,data=get(port,'/health')
                if status==200 and data['version']==version:break
            except (OSError,ValueError):pass
            if time.monotonic()>deadline:raise TimeoutError('worker readiness')
            time.sleep(0.02)
        return p,s,port
    proxy=None;thread=None
    try:
        pa,sa,a=start('blue-v1');pb,sb,b=start('green-v2')
        state['target']=a;state['active']={a:0,b:0}
        class Proxy(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                with guard:
                    target=state['target'];state['active'][target]+=1
                    if target==a:state['seen_old'].set()
                try:
                    status,data=get(target,self.path)
                    body=json.dumps(data).encode()
                    self.send_response(status);self.send_header('Content-Length',str(len(body)))
                    self.end_headers();self.wfile.write(body)
                finally:
                    with guard:state['active'][target]-=1
        proxy=ThreadingHTTPServer(('127.0.0.1',0),Proxy)
        thread=threading.Thread(target=proxy.serve_forever,daemon=True);thread.start()
        front=proxy.server_address[1]
        assert get(front)[1]['version']=='blue-v1'
        # Candidate is reachable but unhealthy from the deployment policy's perspective.
        candidate_health={'status':503,'version':'bad-candidate'}
        with guard:
            if candidate_health['status']==200:state['target']=b
            assert state['target']==a
        result['unhealthy_candidate_kept_old_target']=True
        assert get(b,'/health')==(200,{'version':'green-v2'})
        state['seen_old'].clear()
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures=[pool.submit(get,front) for _ in range(8)]
            assert state['seen_old'].wait(timeout=3)
            with guard:
                active_at_switch=state['active'][a]
                state['target']=b
            futures += [pool.submit(get,front) for _ in range(32)]
            responses=[f.result(timeout=10) for f in futures]
        assert active_at_switch>0 and all(status==200 for status,_ in responses)
        versions=[data['version'] for _,data in responses]
        assert 'blue-v1' in versions and 'green-v2' in versions
        with guard:assert state['active'][a]==0
        # Rollback while old process is still available, then switch forward again.
        with guard:state['target']=a
        assert get(front)[1]['version']=='blue-v1'
        with guard:state['target']=b
        with guard:assert state['active'][a]==0
        pa.terminate();pa.wait(timeout=5);sa.close()
        after=[get(front) for _ in range(10)]
        assert all(status==200 and data['version']=='green-v2' for status,data in after)
        result.update(active_old_at_switch=active_at_switch,transition_requests=len(responses),
                      transition_errors=0,version_counts={v:versions.count(v) for v in sorted(set(versions))},
                      rollback_observed=True,after_old_stop_requests=10,after_old_stop_errors=0)
    finally:
        if proxy is not None:proxy.shutdown();proxy.server_close()
        if thread is not None:thread.join(timeout=3)
        for p in processes:
            if p.poll() is None:
                p.terminate()
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:p.kill();p.wait(timeout=3)
            if p.stderr:p.stderr.close()
        for s in sockets:s.close()
    result['cleanup']='both app processes and proxy stopped; sockets closed'
    result['not_tested']=['TLS','nginx/ALB','Docker or Kubernetes rollout','DB migrations','long-lived streams',
                          'real unhealthy backend probe; candidate rejection was simulated']
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--worker-fd',type=int)
    parser.add_argument('--version');parser.add_argument('--output',type=Path);args=parser.parse_args()
    if args.worker_fd is not None:worker(args.worker_fd,args.version)
    else:
        if args.output is None or args.output.exists():parser.error('Choose new output path')
        result=run()
        with args.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
        print(json.dumps(result,indent=2))
