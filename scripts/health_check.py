"""Automated health and readiness verification script for CI/CD post-deployment validation.
Inspects /health, /ready, and /metrics with exponential backoff retries.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def check_endpoint(url: str, timeout: float = 3.0) -> tuple[bool, int, float, str]:
    start = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TaskAPI-HealthVerifier/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed_ms = (time.perf_counter() - start) * 1000
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status == 200, resp.status, elapsed_ms, body
    except urllib.error.HTTPError as err:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return False, err.code, elapsed_ms, str(err)
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return False, 0, elapsed_ms, str(exc)


def verify_deployment(base_url: str, retries: int = 10, backoff: float = 2.0) -> bool:
    print(f"Starting post-deployment verification for {base_url}...")
    endpoints = [
        ("/health", "Liveness probe"),
        ("/ready", "Readiness & DB connectivity probe"),
        ("/metrics", "Prometheus telemetry scrape endpoint"),
    ]

    for attempt in range(1, retries + 1):
        all_passed = True
        print(f"\n[Attempt {attempt}/{retries}] Checking endpoints...")

        for path, description in endpoints:
            target = f"{base_url.rstrip('/')}{path}"
            ok, status, latency_ms, body = check_endpoint(target)
            status_indicator = "OK" if ok else "FAIL"
            print(f"  [{status_indicator}] {path:12} - HTTP {status} ({latency_ms:.1f}ms) - {description}")

            if ok and path == "/ready":
                try:
                    payload = json.loads(body)
                    print(f"        Readiness details: status={payload.get('status')} cache={payload.get('cache')}")
                except Exception:
                    pass

            if not ok:
                all_passed = False

        if all_passed:
            print("\nVerification succeeded: All services and probes are healthy!")
            return True

        if attempt < retries:
            sleep_time = backoff * attempt
            print(f"Probes pending. Retrying in {sleep_time:.1f}s...")
            time.sleep(sleep_time)

    print("\nVerification failed: One or more critical probes failed within retry limit.")
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Task API Deployment Health Verifier")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of application")
    parser.add_argument("--retries", type=int, default=5, help="Maximum retry attempts")
    parser.add_argument("--backoff", type=float, default=2.0, help="Backoff multiplier in seconds")
    args = parser.parse_args()

    success = verify_deployment(args.url, args.retries, args.backoff)
    sys.exit(0 if success else 1)
