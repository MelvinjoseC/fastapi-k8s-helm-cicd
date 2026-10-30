"""Thin, resilient Redis caching layer with Circuit Breaker and stampede mitigation.

Design choice: caching is an optimization, not a dependency. If Redis is
unreachable (e.g. mid-rollout, network blip, or simply disabled), every
method here fails soft and the API falls straight through to Postgres
instead of throwing 500s.
"""

import json
import logging
import random
from typing import Any

import redis
from config import settings
from resilience import CircuitBreaker, CircuitBreakerOpenError

logger = logging.getLogger("taskapi.cache")

_client: redis.Redis | None = None
_cache_stats = {"hits": 0, "misses": 0, "sets": 0, "errors": 0}
_circuit_breaker = CircuitBreaker("redis-cache", failure_threshold=3, recovery_timeout_seconds=15.0)
KEY_PREFIX = "taskapi:"


def _get_client() -> redis.Redis | None:
    global _client
    if not settings.cache_enabled:
        return None
    if _circuit_breaker.state.value == "open":
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
            _circuit_breaker.call(_client.ping)
        except (redis.RedisError, CircuitBreakerOpenError) as exc:
            logger.warning("Redis unavailable, continuing without cache: %s", exc)
            _client = None
    return _client


def _prefixed_key(key: str) -> str:
    return key if key.startswith(KEY_PREFIX) else f"{KEY_PREFIX}{key}"


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
        raw = _circuit_breaker.call(client.get, _prefixed_key(key))
        if raw is not None:
            _cache_stats["hits"] += 1
            return json.loads(raw)
        _cache_stats["misses"] += 1
        return None
    except (redis.RedisError, CircuitBreakerOpenError) as exc:
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
        jitter = random.randint(-max(1, int(base_ttl * 0.1)), max(1, int(base_ttl * 0.1)))
        effective_ttl = max(1, base_ttl + jitter)
        _circuit_breaker.call(
            client.set,
            _prefixed_key(key),
            json.dumps(value, default=str),
            ex=effective_ttl,
        )
        _cache_stats["sets"] += 1
    except (redis.RedisError, CircuitBreakerOpenError) as exc:
        _cache_stats["errors"] += 1
        logger.warning("Cache SET failed for %s: %s", key, exc)


def invalidate(key: str) -> None:
    """Invalidate a single cache key."""
    client = _get_client()
    if client is None:
        return
    try:
        _circuit_breaker.call(client.delete, _prefixed_key(key))
    except (redis.RedisError, CircuitBreakerOpenError) as exc:
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
        return bool(_circuit_breaker.call(client.ping))
    except (redis.RedisError, CircuitBreakerOpenError):
        return False


def get_stats() -> dict[str, Any]:
    """Return cache operational metrics with hit ratio."""
    total_reqs = _cache_stats["hits"] + _cache_stats["misses"]
    hit_ratio = round(_cache_stats["hits"] / total_reqs, 3) if total_reqs > 0 else 0.0
    return {
        **_cache_stats,
        "hit_ratio": hit_ratio,
        "circuit_breaker": _circuit_breaker.get_status(),
    }
