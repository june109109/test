import asyncio
import httpx
import pytest
from metrics_app import create_app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_exporter_and_fault_paths():
    app = create_app()
    r = app.state.study_registry
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://study.invalid"
        ) as client:
            await asyncio.sleep(0.02)
            assert (await client.get("/block?delay=0.05")).json() == {"ok": True}
            await asyncio.sleep(0.02)
            assert r.get_sample_value("study_loop_lag_seconds_count") > 0
            # At least one observed scheduling delay exceeded 25ms after the injected block.
            count = r.get_sample_value("study_loop_lag_seconds_count")
            under = r.get_sample_value("study_loop_lag_seconds_bucket", {"le": "0.025"})
            assert count > under
            jobs = [
                asyncio.create_task(client.get("/thread?delay=0.05")) for _ in range(6)
            ]
            peaks = []
            while not all(j.done() for j in jobs):
                peaks.append(r.get_sample_value("study_thread_tokens_borrowed"))
                await asyncio.sleep(0.005)
            assert all(x.status_code == 200 for x in await asyncio.gather(*jobs))
            assert (
                max(peaks) == 2
                and r.get_sample_value("study_thread_route_inflight") == 0
            )
            assert (await client.get("/thread?delay=2")).status_code == 422
            response = await client.get("/metrics")
            assert response.status_code == 200
            for name in [
                "study_loop_lag_seconds_bucket",
                "study_http_requests_total",
                "process_resident_memory_bytes",
            ]:
                assert name in response.text
