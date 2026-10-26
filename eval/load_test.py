"""Baseline load test against the local REST API (start it first: python -m helperinlaw.api).

uv run python eval/load_test.py [--requests 200] [--concurrency 8] [--url http://127.0.0.1:8000]

Sends a mix of scenario questions to POST /ask from several threads and reports throughput,
latency percentiles and errors. Local only; never point this at someone else's server.
"""

import argparse
import json
import statistics
import threading
import time
import urllib.request
from pathlib import Path

DATA = Path(__file__).parent / "datasets"


def questions() -> list[str]:
    qs = [json.loads(x)["scenario"] for x in (DATA / "scenarios.jsonl").read_text("utf-8").splitlines() if x.strip()]
    qs += [json.loads(x)["question"] for x in (DATA / "out_of_scope.jsonl").read_text("utf-8").splitlines() if x.strip()]
    return qs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--requests", type=int, default=200)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    args = ap.parse_args()
    if not args.url.startswith(("http://127.0.0.1", "http://localhost")):
        raise SystemExit("load tests run against the local server only")
    qs = questions()
    latencies: list[float] = []
    errors: list[str] = []
    lock = threading.Lock()
    counter = iter(range(args.requests))

    def worker() -> None:
        for i in counter:
            body = json.dumps({"question": qs[i % len(qs)]}).encode()
            req = urllib.request.Request(f"{args.url}/ask", data=body, headers={"Content-Type": "application/json"})
            t = time.perf_counter()
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    json.loads(r.read())
                ok = True
            except Exception as e:  # count, don't stop: we want the error rate
                ok, err = False, str(e)[:80]
            dt = time.perf_counter() - t
            with lock:
                (latencies.append(dt) if ok else errors.append(err))

    start = time.perf_counter()
    threads = [threading.Thread(target=worker) for _ in range(args.concurrency)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    wall = time.perf_counter() - start
    q = statistics.quantiles(latencies, n=100) if len(latencies) > 1 else [0.0] * 99
    result = {
        "requests": args.requests, "concurrency": args.concurrency, "ok": len(latencies), "errors": len(errors),
        "throughput_rps": round(len(latencies) / wall, 2), "p50_s": round(q[49], 2), "p95_s": round(q[94], 2),
        "p99_s": round(q[98], 2), "max_s": round(max(latencies, default=0), 2), "wall_s": round(wall, 1),
    }
    print(json.dumps(result, indent=1))
    if errors:
        print("first errors:", errors[:3])


if __name__ == "__main__":
    main()
