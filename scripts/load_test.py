"""Concurrent load test generator to stress-test Task API, exercise HPA, and verify metrics.
"""
import argparse
import json
import random
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List


def make_request(base_url: str) -> Dict[str, float]:
    endpoints = [
        ("GET", "/health"),
        ("GET", "/ready"),
        ("GET", "/tasks"),
        ("GET", "/tasks/paginated?page=1&page_size=10"),
        ("GET", "/metrics"),
    ]
    method, path = random.choice(endpoints)
    url = f"{base_url}{path}"

    start = time.perf_counter()
    status_code = 0
    try:
        req = urllib.request.Request(url, method=method)
        with urllib.request.urlopen(req, timeout=5) as resp:
            status_code = resp.status
            resp.read()
    except urllib.error.HTTPError as exc:
        status_code = exc.code
    except Exception:
        status_code = 500

    duration_ms = (time.perf_counter() - start) * 1000
    return {"status": status_code, "latency_ms": duration_ms}


def run_load_test(base_url: str, requests: int, concurrency: int) -> None:
    print(f"Starting load test against {base_url} ({requests} requests, concurrency {concurrency})...")
    latencies: List[float] = []
    status_counts: Dict[int, int] = {}

    start_total = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(make_request, base_url) for _ in range(requests)]
        for f in as_completed(futures):
            res = f.result()
            latencies.append(res["latency_ms"])
            status = res["status"]
            status_counts[status] = status_counts.get(status, 0) + 1

    total_time = time.perf_counter() - start_total
    rps = requests / total_time if total_time > 0 else 0

    latencies.sort()
    p50 = latencies[int(len(latencies) * 0.50)] if latencies else 0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0
    p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0

    print("\n--- Load Test Results ---")
    print(f"Total Requests:      {requests}")
    print(f"Total Duration:      {total_time:.2f}s")
    print(f"Throughput:          {rps:.2f} req/s")
    print(f"p50 Latency:         {p50:.2f}ms")
    print(f"p95 Latency:         {p95:.2f}ms")
    print(f"p99 Latency:         {p99:.2f}ms")
    print("Status Code Breakdown:")
    for code, count in sorted(status_counts.items()):
        print(f"  HTTP {code}: {count} ({count/requests*100:.1f}%)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Task API Load Generator")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of Task API")
    parser.add_argument("-n", "--requests", type=int, default=100, help="Total requests to send")
    parser.add_argument("-c", "--concurrency", type=int, default=10, help="Concurrent client threads")
    args = parser.parse_args()

    run_load_test(args.url, args.requests, args.concurrency)