"""Circuit breaker and fault-tolerance primitives for distributed resilience."""

import logging
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from enum import Enum
from typing import Any, TypeVar

logger = logging.getLogger("taskapi.resilience")
T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(Exception):
    def __init__(self, name: str, retry_after: float):
        super().__init__(f"Circuit breaker '{name}' is OPEN. Retry after {retry_after:.1f}s")
        self.name = name
        self.retry_after = retry_after


class CircuitBreaker:
    """Thread-safe circuit breaker protecting external calls from cascading failure."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 30.0,
        expected_exceptions: tuple[type[Exception], ...] = (Exception,),
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.expected_exceptions = expected_exceptions

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if (time.time() - self._last_failure_time) >= self.recovery_timeout_seconds:
                    self._state = CircuitState.HALF_OPEN
                    logger.info("Circuit breaker '%s' transition to HALF-OPEN", self.name)
            return self._state

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        current_state = self.state
        if current_state == CircuitState.OPEN:
            retry_after = max(0.0, self.recovery_timeout_seconds - (time.time() - self._last_failure_time))
            raise CircuitBreakerOpenError(self.name, retry_after)

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exceptions as exc:
            self._on_failure()
            raise exc

    def _on_success(self) -> None:
        with self._lock:
            if self._state in (CircuitState.HALF_OPEN, CircuitState.OPEN):
                logger.info("Circuit breaker '%s' recovered. State reset to CLOSED", self.name)
            self._state = CircuitState.CLOSED
            self._failure_count = 0

    def _on_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    "Circuit breaker '%s' tripped OPEN after %d failures",
                    self.name,
                    self._failure_count,
                )

    def get_status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure": (
                datetime.fromtimestamp(self._last_failure_time, UTC).isoformat()
                if self._last_failure_time > 0
                else None
            ),
        }
