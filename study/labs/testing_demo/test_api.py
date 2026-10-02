import pytest

@pytest.mark.asyncio
async def test_quote_contract(client):
    r=await client.get('/quote',params={'subtotal':10000})
    assert r.status_code==200
    assert r.json()=={'subtotal_cents':10000,'shipping_cents':0,'total_cents':10000}

@pytest.mark.asyncio
@pytest.mark.parametrize('params',[{'subtotal':-1},{'subtotal':100,'discount_bps':10001},{}])
async def test_invalid_query_returns_validation_error(client,params):
    r=await client.get('/quote',params=params)
    assert r.status_code==422
    assert isinstance(r.json()['detail'],list) and r.json()['detail']
