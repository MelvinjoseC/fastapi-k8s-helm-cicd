"""High-performance benchmarking and SLA verification tool for Task API.
Generates comprehensive performance reports including latency percentiles, error rates, and RPS.
"""
import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def execute_request(url: str, method: str = "GET", data: bytes | None = None) -> tuple[int, float]:
    start = time.perf_counter()
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            elapsed_ms = (time.perf_counter() - start) * 1000
            resp.read()
            return resp.status, elapsed_ms
    except urllib.error.HTTPError as err:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return err.code, elapsed_ms
    except Exception:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return 500, elapsed_ms


def run_benchmark(
    base_url: str,
    total_requests: int = 200,
    concurrency: int = 15,
    export_json: Path | None = None,
) -> dict:
    target_url = f"{base_url.rstrip('/')}/tasks"
    print(f"Executing benchmark: {total_requests} requests, concurrency {concurrency} -> {target_url}")

    latencies: list[float] = []
    status_counts: dict[int, int] = {}

    start_time = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(execute_request, target_url, "GET") for _ in range(total_requests)]
        for fut in as_completed(futures):
            code, lat = fut.result()
            latencies.append(lat)
            status_counts[code] = status_counts.get(code, 0) + 1

    total_duration = time.perf_counter() - start_time
    rps = total_requests / total_duration if total_duration > 0 else 0

    sorted_latencies = sorted(latencies)
    mean_lat = statistics.mean(latencies) if latencies else 0
    p50 = sorted_latencies[int(len(sorted_latencies) * 0.50)] if sorted_latencies else 0
    p90 = sorted_latencies[int(len(sorted_latencies) * 0.90)] if sorted_latencies else 0
    p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)] if sorted_latencies else 0
    p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)] if sorted_latencies else 0

    report = {
        "target": target_url,
        "concurrency": concurrency,
        "total_requests": total_requests,
        "duration_seconds": round(total_duration, 3),
        "requests_per_second": round(rps, 2),
        "latency_ms": {
            "mean": round(mean_lat, 2),
            "p50": round(p50, 2),
            "p90": round(p90, 2),
            "p95": round(p95, 2),
            "p99": round(p99, 2),
            "min": round(sorted_latencies[0], 2) if sorted_latencies else 0,
            "max": round(sorted_latencies[-1], 2) if sorted_latencies else 0,
        },
        "status_distribution": status_counts,
        "success_rate_percent": round(
            (status_counts.get(200, 0) / total_requests) * 100, 2
        ) if total_requests else 0,
    }

    print("\n" + "=" * 45)
    print("        BENCHMARK REPORT RESULTS")
    print("=" * 45)
    print(f"Throughput:          {report['requests_per_second']} requests/sec")
    print(f"Total Time:          {report['duration_seconds']}s")
    print(f"Success Rate:        {report['success_rate_percent']}%")
    print(f"Latency Mean:        {report['latency_ms']['mean']} ms")
    print(f"Latency p50:         {report['latency_ms']['p50']} ms")
    print(f"Latency p90:         {report['latency_ms']['p90']} ms")
    print(f"Latency p95:         {report['latency_ms']['p95']} ms")
    print(f"Latency p99:         {report['latency_ms']['p99']} ms")
    print("=" * 45)

    if export_json:
        export_json.parent.mkdir(parents=True, exist_ok=True)
        with open(export_json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"Benchmark summary saved to {export_json}")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Task API Performance Benchmarker")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of Task API")
    parser.add_argument("-n", "--requests", type=int, default=150, help="Total requests to fire")
    parser.add_argument("-c", "--concurrency", type=int, default=10, help="Concurrency level")
    parser.add_argument("--export", type=Path, default=None, help="JSON export filepath")
    args = parser.parse_args()

    run_benchmark(args.url, args.requests, args.concurrency, args.export)
