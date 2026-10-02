"""Local-only HTTP/1.1 learning lab; not a production server or full cache.

Run from the repository root: python3 study/labs/http_semantics.py
No dependencies. The process creates and closes its own loopback server.
"""

from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread


class DemoServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self):
        super().__init__(("127.0.0.1", 0), DemoHandler)
        self.accepted_connections = 0
        self.item_exists = True

    def get_request(self):
        connection, address = super().get_request()
        # accept occurs in the serve_forever thread; assign before handler launch.
        self.accepted_connections += 1
        return connection, address


class DemoHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def setup(self):
        # Each client is created sequentially by this lab, so the counter is stable
        # during setup. This identifier is for this demonstration only.
        super().setup()
        self.connection_number = self.server.accepted_connections

    def log_message(self, format, *args):
        pass

    def respond(self, status, payload=None, *, etag=None):
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("X-Demo-Connection", str(self.connection_number))
        self.send_header("Cache-Control", "no-cache")
        if etag is not None:
            self.send_header("ETag", etag)
        # 204 has no content and must not include Content-Length.
        # 304 omits it here; any supplied value would describe the selected 200.
        if status not in (204, 304):
            self.send_header("Content-Length", str(len(body)))
        if body:
            self.send_header("Content-Type", "application/json")
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self):
        if self.path != "/item" or not self.server.item_exists:
            self.respond(404, {"error": "not found"})
        elif self.headers.get("If-None-Match") == '"demo-v1"':
            self.respond(304, etag='"demo-v1"')
        else:
            self.respond(200, {"id": 7, "name": "demo"}, etag='"demo-v1"')

    def do_DELETE(self):
        if self.path != "/item" or not self.server.item_exists:
            self.respond(404, {"error": "not found"})
        else:
            self.server.item_exists = False
            self.respond(204)


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def request(client, method, headers=None):
    client.request(method, "/item", headers=headers or {})
    response = client.getresponse()
    body = response.read()  # Fully consume the body before connection reuse.
    return response.status, dict(response.getheaders()), body


def main():
    server = DemoServer()
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = HTTPConnection(*server.server_address, timeout=3)
    other = HTTPConnection(*server.server_address, timeout=3)
    try:
        status, headers, body = request(client, "GET")
        check(status == 200 and json.loads(body)["id"] == 7, "GET returns the item")
        connection = headers["X-Demo-Connection"]
        status, second_headers, body = request(
            client, "GET", {"If-None-Match": headers["ETag"]}
        )
        check(status == 304 and body == b"", "matching ETag returns 304 without a body")
        check(second_headers["X-Demo-Connection"] == connection, "same TCP connection reused")
        status, other_headers, _ = request(other, "GET")
        check(status == 200 and other_headers["X-Demo-Connection"] != connection,
              "a new client uses a different connection")
        status, _, body = request(client, "DELETE")
        check(status == 204 and body == b"", "first DELETE returns 204 without a body")
        status, _, _ = request(client, "DELETE")
        check(status == 404, "second DELETE returns 404")
        status, _, _ = request(client, "GET")
        check(status == 404, "final state remains absent")
    finally:
        client.close()
        other.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


if __name__ == "__main__":
    main()
