"""Finite fault traffic to a separately started loopback-only study exporter."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import http.client
import json
import time

p = argparse.ArgumentParser()
p.add_argument("--mode", choices=["block", "thread"], required=True)
p.add_argument("--seconds", type=int, default=30)
a = p.parse_args()
if not 1 <= a.seconds <= 60:
    p.error("seconds must be 1..60")
end = time.monotonic() + a.seconds


def run():
    ok = errors = 0
    while time.monotonic() < end:
        c = http.client.HTTPConnection("127.0.0.1", 8008, timeout=2)
        try:
            c.request("GET", "/" + a.mode + "?delay=0.1")
            r = c.getresponse()
            body = r.read()
            if r.status == 200 and json.loads(body).get("ok"):
                ok += 1
            else:
                errors += 1
        except (OSError, http.client.HTTPException, ValueError):
            errors += 1
        finally:
            c.close()
    return ok, errors


with ThreadPoolExecutor(max_workers=1 if a.mode == "block" else 8) as pool:
    results = list(pool.map(lambda _: run(), range(1 if a.mode == "block" else 8)))
print(
    json.dumps(
        {
            "mode": a.mode,
            "successes": sum(x[0] for x in results),
            "errors": sum(x[1] for x in results),
        }
    )
)
