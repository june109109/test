"""Test-only hypothetical quote API, not a checkout accepting customer prices."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query
from pricing import Line, quote

@asynccontextmanager
async def lifespan(app):
    app.state.ready=True
    try:yield
    finally:app.state.ready=False

app=FastAPI(lifespan=lifespan)

@app.get('/quote')
async def get_quote(subtotal: int=Query(ge=0), discount_bps: int=Query(default=0,ge=0,le=10000)):
    if not app.state.ready:raise RuntimeError('lifespan not started')
    return quote([Line('hypothetical',1,subtotal)],discount_bps)
