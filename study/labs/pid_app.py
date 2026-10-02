"""Small FastAPI app for observing worker-local lifespan and keep-alive routing."""

import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import uuid

from fastapi import FastAPI


def record(event, token):
    path = os.environ.get("STUDY_LIFECYCLE_PATH")
    if not path:
        return
    line = json.dumps({"event": event, "pid": os.getpid(), "token": token}) + "\n"
    descriptor = os.open(Path(path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(descriptor, line.encode())
    finally:
        os.close(descriptor)


@asynccontextmanager
async def lifespan(app):
    token = uuid.uuid4().hex  # A non-secret identifier for this worker's state.
    app.state.worker_token = token
    app.state.requests = 0
    record("started", token)
    try:
        yield
    finally:
        record("stopped", token)


app = FastAPI(lifespan=lifespan)


@app.get("/pid")
async def pid():
    app.state.requests += 1
    current = app.state.requests
    await asyncio.sleep(0.02)
    return {"pid": os.getpid(), "worker_token": app.state.worker_token,
            "local_request_count": current}
