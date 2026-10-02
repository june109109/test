"""Launch two local Uvicorn workers, test routing and per-worker lifecycle, stop them.

Requires Linux/POSIX, fastapi, uvicorn, Python 3.11+.
python3 study/labs/uvicorn_workers.py --output /tmp/uvicorn-workers.json
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import signal
import socket
import subprocess
import sys
import tempfile
import time


def request(port, connection=None):
    own = connection is None
    connection = connection or HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        connection.request("GET", "/pid")
        response = connection.getresponse()
        body = json.loads(response.read())
        if response.status != 200 or "worker_token" not in body:
            raise AssertionError("invalid worker response")
        return body
    finally:
        if own:
            connection.close()


def run():
    with tempfile.TemporaryDirectory(prefix="study-workers-") as temporary:
        temp = Path(temporary)
        events_path = temp / "lifecycle.jsonl"
        log_path = temp / "uvicorn.log"
        # Reserve a socket and pass it into Uvicorn, avoiding a bind-port race.
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(128)
            port = listener.getsockname()[1]
            child_env = os.environ.copy()
            child_env["STUDY_LIFECYCLE_PATH"] = str(events_path)
            command = [sys.executable, "-m", "uvicorn", "pid_app:app",
                       "--app-dir", str(Path(__file__).resolve().parent),
                       "--fd", str(listener.fileno()), "--workers", "2",
                       "--log-level", "warning", "--no-access-log"]
            with log_path.open("w") as logs:
                process = subprocess.Popen(command, pass_fds=(listener.fileno(),),
                                           env=child_env, stdout=logs, stderr=logs,
                                           start_new_session=True)
            try:
                deadline = time.monotonic() + 20
                while True:
                    if process.poll() is not None:
                        raise RuntimeError("Uvicorn exited: " + log_path.read_text()[-2000:])
                    try:
                        request(port)
                        break
                    except (OSError, ValueError):
                        if time.monotonic() >= deadline:
                            raise RuntimeError("startup timed out: " + log_path.read_text()[-2000:])
                        time.sleep(0.1)
                persistent = HTTPConnection("127.0.0.1", port, timeout=3)
                try:
                    same_connection = [request(port, persistent) for _ in range(12)]
                finally:
                    persistent.close()
                new_connections = []
                for _ in range(4):
                    with ThreadPoolExecutor(max_workers=8) as clients:
                        new_connections.extend(clients.map(request, [port] * 24))
                    if len({r["pid"] for r in new_connections}) == 2:
                        break
                if len({r["pid"] for r in same_connection}) != 1:
                    raise AssertionError("a persistent connection changed workers")
                if len({r["pid"] for r in new_connections}) != 2:
                    raise AssertionError("two worker PIDs were not observed within bounded requests")
                tokens = {}
                for row in same_connection + new_connections:
                    tokens.setdefault(row["pid"], set()).add(row["worker_token"])
                if any(len(values) != 1 for values in tokens.values()) or len(set.union(*tokens.values())) != 2:
                    raise AssertionError("worker-local token identity mismatch")
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=5)
                        raise RuntimeError("graceful shutdown timed out")
        events = [json.loads(line) for line in events_path.read_text().splitlines()]
        started = {(e["pid"], e["token"]) for e in events if e["event"] == "started"}
        stopped = {(e["pid"], e["token"]) for e in events if e["event"] == "stopped"}
        if len(started) != 2 or started != stopped:
            raise AssertionError("both worker lifespan shutdowns were not verified")
        counts = {str(pid): sum(r["pid"] == pid for r in new_connections) for pid in tokens}
        return {
            "python": platform.python_version(),
            "versions": {n: version(n) for n in ("uvicorn", "fastapi", "starlette")},
            "workers": 2, "transport": "real loopback HTTP/1.1 using a passed listening socket",
            "persistent_requests": len(same_connection), "persistent_distinct_pids": 1,
            "fresh_connection_requests": len(new_connections), "fresh_pid_counts": counts,
            "distinct_worker_tokens": 2, "lifespan_started": len(started), "lifespan_stopped": len(stopped),
            "exit_code": process.returncode,
            "validation": "persistent connection stayed on one worker; fresh connections reached two; both lifespans closed",
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("choose a fresh output path")
    report = run()
    with args.output.open("x") as destination:
        json.dump(report, destination, indent=2)
        destination.write("\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
