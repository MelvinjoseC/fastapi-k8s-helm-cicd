"""Seed database with realistic task data for local development, demos, and load testing.
Supports seeding via direct DB session or REST API HTTP endpoint.
"""
import argparse
import json
import os
import random
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

SAMPLE_TASKS = [
    {
        "title": "Harden Kubernetes network policies",
        "description": "Enforce strict egress rules and allow-list only kube-dns, postgres, and redis.",
        "priority": "high",
        "tags": ["k8s", "security", "devops"],
    },
    {
        "title": "Configure Prometheus alerting rules for p95 latency",
        "description": "Implement multi-window burn rate alerts targeting 99.9% availability SLO.",
        "priority": "urgent",
        "tags": ["monitoring", "prometheus", "sre"],
    },
    {
        "title": "Automate database migrations in Helm pre-upgrade hook",
        "description": "Deploy Alembic migration runner job before pod rolling updates.",
        "priority": "high",
        "tags": ["helm", "database", "ci-cd"],
    },
    {
        "title": "Implement sliding window rate limiter",
        "description": "Add Redis-backed token bucket rate limiting to prevent API burst traffic.",
        "priority": "medium",
        "tags": ["fastapi", "redis", "security"],
    },
    {
        "title": "Set up Grafana dashboard for HTTP error rates",
        "description": "Track 4xx and 5xx status codes, request throughput, and active pods.",
        "priority": "medium",
        "tags": ["grafana", "observability"],
    },
    {
        "title": "Tune HPA scale-down stabilization window",
        "description": "Prevent pod flapping during spiky morning load patterns.",
        "priority": "low",
        "tags": ["k8s", "hpa", "autoscaling"],
    },
    {
        "title": "Rotate database secrets with External Secrets Operator",
        "description": "Integrate Vault/AWS Secrets Manager with Kubernetes secrets store.",
        "priority": "urgent",
        "tags": ["security", "secrets", "vault"],
    },
    {
        "title": "Run Trivy container vulnerability scan in CI",
        "description": "Gate merge requests when CRITICAL or HIGH CVEs are detected.",
        "priority": "high",
        "tags": ["security", "docker", "ci-cd"],
    },
]


def seed_via_http(base_url: str, count: int = 15) -> None:
    print(f"Seeding {count} tasks via HTTP at {base_url}...")
    headers = {"Content-Type": "application/json"}
    success = 0

    for i in range(count):
        sample = random.choice(SAMPLE_TASKS)
        payload = {
            "title": f"{sample['title']} (Sample #{i+1})",
            "description": sample["description"],
            "priority": sample["priority"],
            "tags": sample["tags"],
            "due_date": (datetime.now(timezone.utc) + timedelta(days=random.randint(1, 30))).isoformat(),
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/tasks", data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req) as resp:
                if resp.status == 201:
                    success += 1
        except Exception as exc:
            print(f"Error inserting task #{i+1}: {exc}")

    print(f"Successfully created {success}/{count} tasks via HTTP.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Task API with sample data")
    parser.add_argument("--url", default="http://localhost:8000", help="Target API URL")
    parser.add_argument("--count", type=int, default=12, help="Number of tasks to generate")
    args = parser.parse_args()

    seed_via_http(args.url, args.count)