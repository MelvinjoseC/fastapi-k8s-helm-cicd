"""
Thin Redis caching layer.

Design choice: caching is an optimization, not a dependency. If Redis is
unreachable (e.g. mid-rollout, network blip, or simply disabled), every
method here fails soft and the API falls straight through to Postgres
instead of throwing 500s. This is the same resilience pattern you'd want
in any service that treats a cache as best-effort.
"""
import json
import logging
from typing import Any, Optional

import redis

from config import settings

logger = logging.getLogger("taskapi.cache")

_client: Optional[redis.Redis] = None


def _get_client() -> Optional[redis.Redis]:
    global _client
    if not settings.cache_enabled:
        return None
    if _client is None:
        try:
            _client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                socket_connect_timeout=1,
                socket_timeout=1,
                decode_responses=True,
            )
            _client.ping()
        except redis.RedisError as exc:
            logger.warning("Redis unavailable, continuing without cache: %s", exc)
            _client = None
    return _client


def get(key: str) -> Optional[Any]:
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        return json.loads(raw) if raw else None
    except redis.RedisError as exc:
        logger.warning("Cache GET failed for %s: %s", key, exc)
        return None


def set(key: str, value: Any, ttl: int = None) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        client.set(key, json.dumps(value, default=str), ex=ttl or settings.redis_ttl_seconds)
    except redis.RedisError as exc:
        logger.warning("Cache SET failed for %s: %s", key, exc)


def invalidate(key: str) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        client.delete(key)
    except redis.RedisError as exc:
        logger.warning("Cache DELETE failed for %s: %s", key, exc)


def ping() -> bool:
    client = _get_client()
    if client is None:
        return False
    try:
        return bool(client.ping())
    except redis.RedisError:
        return False
