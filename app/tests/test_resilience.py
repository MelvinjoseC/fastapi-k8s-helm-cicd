"""Tests for CircuitBreaker pattern and resilient cache fallbacks."""

import cache
import pytest
from resilience import CircuitBreaker, CircuitBreakerOpenError, CircuitState


def test_circuit_breaker_transitions():
    cb = CircuitBreaker("test-service", failure_threshold=2, recovery_timeout_seconds=0.1)
    assert cb.state == CircuitState.CLOSED

    # Failure 1
    with pytest.raises(ValueError):
        cb.call(int, "invalid_number")
    assert cb.state == CircuitState.CLOSED

    # Failure 2 (trips open)
    with pytest.raises(ValueError):
        cb.call(int, "invalid_number")
    assert cb.state == CircuitState.OPEN

    # Fast failure when OPEN
    with pytest.raises(CircuitBreakerOpenError):
        cb.call(int, "123")


def test_cache_fails_soft_when_circuit_open(monkeypatch):
    # Ensure cache operations fail soft and do not crash requests
    monkeypatch.setattr(cache._circuit_breaker, "_state", CircuitState.OPEN)
    assert cache.get("test-key") is None
    cache.set("test-key", {"dummy": 1})
    cache.invalidate("test-key")
    assert cache.ping() is False
