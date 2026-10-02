"""Bounded CPU and real loopback-I/O comparison, using only the stdlib.

Run: python3 study/labs/concurrency_bench.py --output /tmp/concurrency-results.json
Pool creation/warmup is recorded separately; measured pools are reused.
The loopback server delays replies to create a controlled I/O wait.
"""

import argparse
import asyncio
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import json
import multiprocessing
import os
from pathlib import Path
import platform
import socket
import socketserver
import statistics
import sys
import threading
import time


def cpu_job(args):
    iterations, seed = args
    total = 0
    for i in range(iterations):
        total += (i + seed) % 97
    return total


def io_job(args):
    host, port = args
    with socket.create_connection((host, port), timeout=5) as connection:
        connection.sendall(b"?")
        result = connection.recv(1)
        if result != b"!":
            raise RuntimeError(f"unexpected server response: {result!r}")
        return result.hex()


def warm_worker(_):
    time.sleep(0.1)
    return os.getpid()


class DelayedReply(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(5)
        if self.request.recv(1) != b"?":
            return
        time.sleep(self.server.delay)
        self.request.sendall(b"!")


class DelayServer(socketserver.ThreadingTCPServer):
    daemon_threads = True


async def async_jobs(kind, arguments, concurrency):
    limit = asyncio.Semaphore(concurrency)

    async def run_one(arg):
        async with limit:
            if kind == "cpu":
                # Deliberately no yield during the pure Python calculation.
                return cpu_job(arg)
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(*arg), timeout=5
            )
            try:
                writer.write(b"?")
                await writer.drain()
                result = await asyncio.wait_for(reader.readexactly(1), timeout=5)
                if result != b"!":
                    raise RuntimeError("unexpected asynchronous server response")
                return result.hex()
            finally:
                writer.close()
                await writer.wait_closed()

    return await asyncio.gather(*(run_one(arg) for arg in arguments))


def metadata(args):
    quota_file = Path("/sys/fs/cgroup/cpu.max")
    gil_check = getattr(sys, "_is_gil_enabled", None)
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "visible_cpu_count": os.cpu_count(),
        "affinity_cpu_count": len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
        "cgroup_v2_cpu_max": quota_file.read_text().strip() if quota_file.exists() else None,
        "gil_runtime_probe": gil_check() if gil_check else "unavailable; inspect build/version",
        "process_start_method": "spawn",
        "tasks": args.tasks,
        "workers_or_async_limit": args.workers,
        "cpu_iterations_per_task": args.iterations,
        "server_delay_seconds": args.delay,
        "repeats": args.repeats,
        "clock": "time.perf_counter",
        "timed_region": "submit/run, transport or computation, and collect results; warmed pools",
        "io_model": "real loopback TCP, server sleeps before one-byte response; not production network",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--tasks", type=int, default=8)
    parser.add_argument("--iterations", type=int, default=800_000)
    parser.add_argument("--delay", type=float, default=0.05)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not (1 <= args.workers <= 8 and 1 <= args.tasks <= 64 and 1 <= args.repeats <= 10):
        parser.error("use workers 1..8, tasks 1..64, repeats 1..10")
    if not (1 <= args.iterations <= 10_000_000 and 0.001 <= args.delay <= 1):
        parser.error("use iterations 1..10000000 and delay 0.001..1")
    if args.output.exists():
        parser.error("output already exists; choose a fresh path to preserve previous runs")

    report = {"environment": metadata(args), "warmup_seconds": {}, "results": {}}
    with DelayServer(("127.0.0.1", 0), DelayedReply) as server:
        server.delay = args.delay
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        try:
            # Explicit spawn avoids inheriting the running server thread/sockets.
            with ThreadPoolExecutor(max_workers=args.workers) as threads, ProcessPoolExecutor(
                max_workers=args.workers, mp_context=multiprocessing.get_context("spawn")
            ) as processes, asyncio.Runner() as runner:
                for name, pool in (("threads", threads), ("processes", processes)):
                    started = time.perf_counter()
                    pids = list(pool.map(warm_worker, range(args.workers)))
                    report["warmup_seconds"][name] = time.perf_counter() - started
                    report.setdefault("warmup_unique_worker_pids", {})[name] = len(set(pids))
                runner.run(asyncio.sleep(0))
                for kind, function, arguments in (
                    ("cpu", cpu_job, [(args.iterations, n) for n in range(args.tasks)]),
                    ("io", io_job, [server.server_address] * args.tasks),
                ):
                    samples = {name: [] for name in ("sequential", "threads", "processes", "asyncio")}
                    expected = None
                    names = list(samples)
                    for repeat in range(args.repeats):
                        order = names[repeat % len(names):] + names[:repeat % len(names)]
                        for name in order:
                            started = time.perf_counter()
                            if name == "sequential":
                                results = list(map(function, arguments))
                            elif name == "threads":
                                results = list(threads.map(function, arguments))
                            elif name == "processes":
                                results = list(processes.map(function, arguments))
                            else:
                                results = runner.run(async_jobs(kind, arguments, args.workers))
                            elapsed = time.perf_counter() - started
                            if expected is None:
                                expected = results
                            if len(results) != args.tasks or results != expected:
                                raise AssertionError(f"result mismatch: {kind}/{name}")
                            samples[name].append(elapsed)
                    report["results"][kind] = {
                        name: {"seconds": times, "median_seconds": statistics.median(times)}
                        for name, times in samples.items()
                    }
                    report["results"][kind]["verified_results_per_run"] = len(expected)
        finally:
            server.shutdown()
            server_thread.join(timeout=3)

    report["validation"] = "all task results matched; all measured runs completed"
    with args.output.open("x", encoding="utf-8") as destination:
        json.dump(report, destination, ensure_ascii=False, indent=2)
        destination.write("\n")
    for kind, rows in report["results"].items():
        print(kind.upper())
        for name in ("sequential", "threads", "processes", "asyncio"):
            print(f"  {name:10s} median={rows[name]['median_seconds']:.6f}s")
    print(report["validation"])
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
