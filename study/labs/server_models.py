"""Compare a single-thread HTTP server with a bounded-worker thread pool.

The executor queue is NOT bounded; this is a finite educational load only.
Run with Python 3.10+: python3 study/labs/server_models.py --output /tmp/server-models.json
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import platform
import threading
import time


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        with self.server.counter_lock:
            self.server.active += 1
            self.server.max_active = max(self.server.max_active, self.server.active)
        try:
            time.sleep(0.08)
            body = json.dumps({"ok": True, "pid": os.getpid(), "thread": threading.get_ident()}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            # Closing avoids idle keep-alive occupying the single handler.
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
            self.close_connection = True
        finally:
            with self.server.counter_lock:
                self.server.active -= 1


class SingleServer(HTTPServer):
    def __init__(self):
        super().__init__(("127.0.0.1", 0), Handler)
        self.counter_lock = threading.Lock()
        self.active = 0
        self.max_active = 0


class PooledServer(SingleServer):
    def __init__(self):
        super().__init__()
        self.pool = ThreadPoolExecutor(max_workers=4)

    def process_request(self, request, client_address):
        self.pool.submit(self.handle_request_in_worker, request, client_address)

    def handle_request_in_worker(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)

    def server_close(self):
        super().server_close()
        self.pool.shutdown(wait=True)


def fetch(address):
    connection = HTTPConnection(*address, timeout=5)
    try:
        connection.request("GET", "/slow")
        response = connection.getresponse()
        body = json.loads(response.read())
        if response.status != 200 or body.get("ok") is not True:
            raise AssertionError("request failed")
        return body
    finally:
        connection.close()


def measure(server_class):
    with server_class() as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with ThreadPoolExecutor(max_workers=4) as clients:
                started = time.perf_counter()
                responses = list(clients.map(fetch, [server.server_address] * 4))
                elapsed = time.perf_counter() - started
            if len(responses) != 4:
                raise AssertionError("not all requests completed")
            if server_class is SingleServer and server.max_active != 1:
                raise AssertionError("single server unexpectedly overlapped handlers")
            if server_class is PooledServer and not 1 < server.max_active <= 4:
                raise AssertionError("pool did not demonstrate bounded overlap")
            return {"seconds": elapsed, "completed": len(responses),
                    "max_active_handlers": server.max_active,
                    "unique_pids": len({r['pid'] for r in responses}),
                    "unique_handler_threads": len({r['thread'] for r in responses})}
        finally:
            server.shutdown()
            thread.join(timeout=3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("choose a fresh output path")
    report = {"python": platform.python_version(), "requests_per_model": 4,
              "delay_seconds": 0.08, "repeats": 1,
              "single": measure(SingleServer), "pool4": measure(PooledServer),
              "validation": "all 8 responses succeeded; serial/parallel handler counts verified"}
    with args.output.open("x") as f:
        json.dump(report, f, indent=2)
        f.write("\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
