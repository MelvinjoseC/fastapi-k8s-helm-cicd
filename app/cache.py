"""Thin, resilient Redis caching layer.

Design choice: caching is an optimization, not a dependency. If Redis is
unreachable (e.g. mid-rollout, network blip, or simply disabled), every
method here fails soft and the API falls straight through to Postgres
instead of throwing 500s. This is the same resilience pattern you'd want
in any service that treats a cache as best-effort.
"""

import json
import logging
import random
from typing import Any

import redis
from config import settings

logger = logging.getLogger("taskapi.cache")

_client: redis.Redis | None = None

# In-process stats counter for local observability
_cache_stats = {"hits": 0, "misses": 0, "sets": 0, "errors": 0}


def _get_client() -> redis.Redis | None:
    global _client
    if not settings.cache_enabled:
        return None
    if _client is None:
        try:
            _client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                socket_connect_timeout=settings.redis_connect_timeout,
                socket_timeout=settings.redis_connect_timeout,
                decode_responses=True,
            )
            _client.ping()
        except redis.RedisError as exc:
            logger.warning("Redis unavailable, continuing without cache: %s", exc)
            _client = None
    return _client


def task_detail_key(task_id: int) -> str:
    """Helper to generate cache key for an individual task."""
    return f"tasks:detail:{task_id}"


def get(key: str) -> Any | None:
    """Retrieve value from cache. Fails soft and logs warning on error."""
    client = _get_client()
    if client is None:
        _cache_stats["misses"] += 1
        return None
    try:
        raw = client.get(key)
        if raw is not None:
            _cache_stats["hits"] += 1
            return json.loads(raw)
        _cache_stats["misses"] += 1
        return None
    except redis.RedisError as exc:
        _cache_stats["errors"] += 1
        logger.warning("Cache GET failed for %s: %s", key, exc)
        return None


def set(key: str, value: Any, ttl: int | None = None) -> None:
    """Store value in cache with TTL jitter to prevent cache stampedes."""
    client = _get_client()
    if client is None:
        return
    try:
        base_ttl = ttl or settings.redis_ttl_seconds
        # Apply +/- 10% jitter to avoid simultaneous key expirations
        jitter = random.randint(-max(1, int(base_ttl * 0.1)), max(1, int(base_ttl * 0.1)))
        effective_ttl = max(1, base_ttl + jitter)
        client.set(key, json.dumps(value, default=str), ex=effective_ttl)
        _cache_stats["sets"] += 1
    except redis.RedisError as exc:
        _cache_stats["errors"] += 1
        logger.warning("Cache SET failed for %s: %s", key, exc)


def invalidate(key: str) -> None:
    """Invalidate a single cache key."""
    client = _get_client()
    if client is None:
        return
    try:
        client.delete(key)
    except redis.RedisError as exc:
        _cache_stats["errors"] += 1
        logger.warning("Cache DELETE failed for %s: %s", key, exc)


def invalidate_task(task_id: int) -> None:
    """Invalidate individual task cache and general task list caches."""
    invalidate(task_detail_key(task_id))
    invalidate("tasks:all")


def ping() -> bool:
    """Check connectivity to Redis cache."""
    client = _get_client()
    if client is None:
        return False
    try:
        return bool(client.ping())
    except redis.RedisError:
        return False


def get_stats() -> dict[str, int]:
    """Return cache operational metrics."""
    return dict(_cache_stats)
