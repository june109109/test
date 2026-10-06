"""Single-worker educational exporter; bounded fault endpoints, loopback only."""

import asyncio
from contextlib import asynccontextmanager, suppress
import time
import anyio
from fastapi import FastAPI, Query, Response, Request
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    ProcessCollector,
    generate_latest,
    CONTENT_TYPE_LATEST,
)


def create_app():
    registry = CollectorRegistry()
    ProcessCollector(registry=registry)
    lag = Histogram(
        "study_loop_lag_seconds",
        "Delay beyond sampler interval",
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1),
        registry=registry,
    )
    borrowed = Gauge(
        "study_thread_tokens_borrowed", "AnyIO borrowed tokens", registry=registry
    )
    total = Gauge("study_thread_tokens_total", "AnyIO token limit", registry=registry)
    inflight = Gauge(
        "study_thread_route_inflight",
        "Thread route requests, including limiter wait",
        registry=registry,
    )
    requests = Counter(
        "study_http_requests",
        "Completed application requests",
        ["route", "status"],
        registry=registry,
    )
    duration = Histogram(
        "study_http_duration_seconds",
        "Application middleware duration",
        ["route"],
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2),
        registry=registry,
    )

    @asynccontextmanager
    async def lifespan(app):
        limiter = anyio.to_thread.current_default_thread_limiter()
        old = limiter.total_tokens
        limiter.total_tokens = 2
        total.set(2)

        async def sample():
            previous = time.perf_counter()
            while True:
                await asyncio.sleep(0.01)
                now = time.perf_counter()
                lag.observe(max(0, now - previous - 0.01))
                previous = now
                borrowed.set(limiter.borrowed_tokens)

        task = asyncio.create_task(sample())
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            limiter.total_tokens = old

    app = FastAPI(lifespan=lifespan)

    @app.middleware("http")
    async def observe(request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)
        route = (
            request.url.path
            if request.url.path in ["/block", "/thread", "/health"]
            else "other"
        )
        started = time.perf_counter()
        status = "500"
        try:
            response = await call_next(request)
            status = str(response.status_code)
            return response
        finally:
            requests.labels(route, status).inc()
            duration.labels(route).observe(time.perf_counter() - started)

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.get("/block")
    async def block(delay: float = Query(default=0.1, ge=0, le=0.5)):
        time.sleep(delay)
        return {"ok": True}

    @app.get("/thread")
    async def thread(delay: float = Query(default=0.1, ge=0, le=0.5)):
        inflight.inc()
        try:
            await anyio.to_thread.run_sync(time.sleep, delay)
        finally:
            inflight.dec()
        return {"ok": True}

    @app.get("/metrics")
    async def metrics():
        return Response(
            generate_latest(registry), headers={"Content-Type": CONTENT_TYPE_LATEST}
        )

    app.state.study_registry = registry
    return app
