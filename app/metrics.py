"""Custom Prometheus operational and domain metrics for observability.
"""
from prometheus_client import Counter, Gauge, Histogram

# Business metrics
tasks_created_total = Counter(
    "taskapi_tasks_created_total",
    "Total number of tasks created",
    ["priority"],
)

tasks_completed_total = Counter(
    "taskapi_tasks_completed_total",
    "Total number of tasks marked as completed",
)

tasks_deleted_total = Counter(
    "taskapi_tasks_deleted_total",
    "Total number of tasks deleted",
    ["permanent"],
)

active_tasks_gauge = Gauge(
    "taskapi_active_tasks_count",
    "Current number of non-deleted, uncompleted tasks",
)

# Operational & infrastructure metrics
cache_operations_total = Counter(
    "taskapi_cache_operations_total",
    "Total Redis cache operations",
    ["operation", "status"],
)

db_query_duration_seconds = Histogram(
    "taskapi_db_query_duration_seconds",
    "Database execution duration in seconds",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)