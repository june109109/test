import itertools
import pytest
import pytest_asyncio
import httpx
from pricing import Line
from quote_api import app

@pytest.fixture
def line_factory():
    ids=itertools.count(1)
    def make(**overrides):
        fields={'sku':f'SKU-{next(ids)}','quantity':1,'unit_cents':10000}
        fields.update(overrides)
        return Line(**fields)
    return make

@pytest_asyncio.fixture
async def client():
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://study.invalid') as c:
            yield c
