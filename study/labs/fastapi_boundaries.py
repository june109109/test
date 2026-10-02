"""In-process ASGI execution-boundary experiment; no Uvicorn/network benchmark.

Requires fastapi, anyio, httpx. Exact validated versions are in the result JSON.
python3 study/labs/fastapi_boundaries.py --output /tmp/fastapi-boundaries.json
"""

import argparse
import asyncio
from contextlib import contextmanager
from importlib.metadata import version
import json
from pathlib import Path
import platform
import statistics
import threading
import time

import anyio.to_thread
from fastapi import Depends, FastAPI
import httpx


def helper():
    return threading.get_ident()


def sync_dependency():
    return helper()


def create_app():
    app = FastAPI()
    lock = threading.Lock()
    app.state.active = 0
    app.state.peak = 0

    @contextmanager
    def tracking():
        with lock:
            app.state.active += 1
            app.state.peak = max(app.state.peak, app.state.active)
        try:
            yield
        finally:
            with lock:
                app.state.active -= 1

    @app.get("/async-blocking")
    async def async_blocking():
        with tracking():
            time.sleep(0.05)
            return {"ok": True, "work_thread": helper()}

    @app.get("/sync")
    def sync_route():
        with tracking():
            time.sleep(0.05)
            return {"ok": True, "work_thread": helper()}

    @app.get("/async-io")
    async def async_io():
        with tracking():
            await asyncio.sleep(0.05)
            return {"ok": True, "work_thread": helper()}

    @app.get("/async-thread")
    async def async_thread():
        def blocking_work():
            time.sleep(0.05)
            return helper()
        with tracking():
            thread_id = await anyio.to_thread.run_sync(blocking_work)
            return {"ok": True, "work_thread": thread_id}

    @app.get("/dependency")
    async def dependency_route(dependency_thread: int = Depends(sync_dependency)):
        return {"route_thread": helper(), "dependency_thread": dependency_thread,
                "direct_helper_thread": helper()}

    return app


async def measure():
    app = create_app()
    loop_thread = threading.get_ident()
    report = {
        "python": platform.python_version(),
        "versions": {name: version(name) for name in ("fastapi", "starlette", "anyio", "httpx")},
        "transport": "httpx.ASGITransport; in-process; no TCP, TLS, Uvicorn or multiworker",
        "requests_per_batch": 10, "delay_seconds": 0.05, "repeats": 3,
        "anyio_default_tokens": anyio.to_thread.current_default_thread_limiter().total_tokens,
        "results": {},
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/dependency")
        response.raise_for_status()
        dependency = response.json()
        if not (dependency["route_thread"] == loop_thread == dependency["direct_helper_thread"]
                and dependency["dependency_thread"] != loop_thread):
            raise AssertionError("dependency/direct helper execution boundary mismatch")
        report["dependency_check"] = "sync Depends runs off-loop; async route and direct helper run on-loop"
        # Warm the offload machinery; excluded from timed batches.
        await asyncio.gather(*(anyio.to_thread.run_sync(helper) for _ in range(10)))
        routes = ("async-blocking", "sync", "async-io", "async-thread")
        samples = {r: [] for r in routes}
        peaks = {r: [] for r in routes}
        for repeat in range(3):
            order = routes[repeat:] + routes[:repeat]
            for route in order:
                app.state.peak = 0
                if app.state.active != 0:
                    raise AssertionError("previous requests still active")
                started = time.perf_counter()
                responses = await asyncio.gather(*(client.get('/' + route) for _ in range(10)))
                elapsed = time.perf_counter() - started
                for response in responses:
                    response.raise_for_status()
                    body = response.json()
                    if body.get("ok") is not True:
                        raise AssertionError("incorrect result")
                    on_loop = body["work_thread"] == loop_thread
                    if on_loop != (route in ("async-blocking", "async-io")):
                        raise AssertionError("work executed on the wrong thread")
                if route == "async-blocking" and app.state.peak != 1:
                    raise AssertionError("expected sequential blocking handler bodies")
                if route != "async-blocking" and app.state.peak <= 1:
                    raise AssertionError("expected overlapping handler bodies")
                samples[route].append(elapsed)
                peaks[route].append(app.state.peak)
        report["results"] = {r: {"seconds": samples[r], "median_seconds": statistics.median(samples[r]),
                                    "peak_active_handler_bodies": peaks[r]} for r in routes}
        report["validation"] = "120 timed responses succeeded; thread boundaries and overlap verified; dependency check passed"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("choose a fresh output path")
    report = asyncio.run(measure())
    with args.output.open("x") as f:
        json.dump(report, f, indent=2)
        f.write("\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
