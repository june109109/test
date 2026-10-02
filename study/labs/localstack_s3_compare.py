"""Compare FastAPI routes calling a real local-only S3 emulator via boto3.

Requires LocalStack already running plus boto3, fastapi, anyio, httpx.
Only http://127.0.0.1:<port> or http://localhost:<port> endpoints are accepted.
Credentials are deliberately fake emulator credentials, never real AWS keys.
The script creates and removes only its own uniquely named bucket/object.
"""

import argparse
import asyncio
from importlib.metadata import version
import json
from pathlib import Path
import platform
import statistics
import threading
import time
from urllib.parse import urlparse
import uuid

import anyio.to_thread
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from fastapi import FastAPI
import httpx


async def experiment(endpoint):
    session = boto3.session.Session(aws_access_key_id="test", aws_secret_access_key="test", region_name="us-east-1")
    client = session.client("s3", endpoint_url=endpoint, config=Config(
        connect_timeout=2, read_timeout=3, max_pool_connections=20,
        retries={"mode": "standard", "total_max_attempts": 1},
        s3={"addressing_style": "path"},
        # Only the validated loopback emulator is used. No external proxy/auth route.
        proxies={},
    ))
    bucket = "study-" + uuid.uuid4().hex
    key = "demo.txt"
    expected = b"localstack-s3-study-payload"
    created = False
    report = {
        "python": platform.python_version(),
        "versions": {n: version(n) for n in ("boto3", "botocore", "urllib3", "fastapi", "starlette", "anyio", "httpx")},
        "endpoint": endpoint,
        "transport": "FastAPI in-process ASGITransport; boto3 makes real HTTP calls to local S3 emulator",
        "requests_per_batch": 10, "repeats": 3, "results": {},
        "delay_note": "0.05s is injected time.sleep BEFORE SDK call, not measured LocalStack/AWS network latency",
        "anyio_default_tokens": anyio.to_thread.current_default_thread_limiter().total_tokens,
        "sdk_max_pool_connections": 20, "sdk_total_max_attempts": 1,
    }
    loop_thread = threading.get_ident()

    def read_object(delay):
        if delay:
            time.sleep(delay)
        response = client.get_object(Bucket=bucket, Key=key)
        body = response["Body"]
        try:
            data = body.read()
        finally:
            body.close()
        if data != expected:
            raise AssertionError("S3 object bytes differ")
        return {"ok": True, "size": len(data), "work_thread": threading.get_ident()}

    try:
        # Preparation is outside measured requests.
        client.create_bucket(Bucket=bucket)
        created = True
        client.put_object(Bucket=bucket, Key=key, Body=expected)
        read_object(0)
        app = FastAPI()

        @app.get("/async-direct")
        async def async_direct(delay: float = 0):
            return read_object(delay)

        @app.get("/sync")
        def sync_route(delay: float = 0):
            return read_object(delay)

        @app.get("/async-offload")
        async def async_offload(delay: float = 0):
            return await anyio.to_thread.run_sync(read_object, delay)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://study") as http:
            await asyncio.gather(*(anyio.to_thread.run_sync(read_object, 0) for _ in range(10)))
            modes = ("async-direct", "sync", "async-offload")
            for delay in (0.0, 0.05):
                samples = {mode: [] for mode in modes}
                for repeat in range(3):
                    for mode in modes[repeat:] + modes[:repeat]:
                        started = time.perf_counter()
                        responses = await asyncio.gather(*(http.get(f"/{mode}", params={"delay": delay}) for _ in range(10)))
                        elapsed = time.perf_counter() - started
                        for response in responses:
                            response.raise_for_status()
                            result = response.json()
                            if result.get("ok") is not True or result["size"] != len(expected):
                                raise AssertionError("invalid API response")
                            if (result["work_thread"] == loop_thread) != (mode == "async-direct"):
                                raise AssertionError("wrong SDK execution thread")
                        samples[mode].append(elapsed)
                report["results"][str(delay)] = {
                    mode: {"seconds": values, "median_seconds": statistics.median(values)}
                    for mode, values in samples.items()
                }
        report["validation"] = "180 timed S3 reads matched expected bytes; API responses and execution threads verified"
    finally:
        try:
            if created:
                client.delete_object(Bucket=bucket, Key=key)
                client.delete_bucket(Bucket=bucket)
                try:
                    client.head_bucket(Bucket=bucket)
                except ClientError as error:
                    if error.response["ResponseMetadata"]["HTTPStatusCode"] != 404:
                        raise
                else:
                    raise AssertionError("study bucket still exists")
                report["cleanup"] = "own object and bucket deleted; head_bucket returned 404"
        finally:
            client.close()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    parsed = urlparse(args.endpoint)
    if not (parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost")
            and parsed.port and not parsed.username and not parsed.password
            and parsed.path in ("", "/") and not parsed.query and not parsed.fragment):
        parser.error("only explicit HTTP loopback emulator endpoints are permitted")
    if args.output.exists():
        parser.error("choose a fresh output path")
    report = asyncio.run(experiment(args.endpoint))
    with args.output.open("x") as destination:
        json.dump(report, destination, indent=2)
        destination.write("\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
