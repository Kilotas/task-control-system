from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TypeVar, Callable, Awaitable

from src.core.circuit_breaker_types import CircuitState, CircuitBreakerOpenException

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: timedelta = timedelta(seconds=60),
        success_threshold: int = 2,
        name: str = "default",
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold
        self.name = name

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: datetime | None = None

    async def call(self, func: Callable[[], Awaitable[T]]) -> T:
        if self.state == CircuitState.OPEN:
            if self.last_failure_time:
                elapsed = datetime.now() - self.last_failure_time
                if elapsed >= self.timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    logger.info(f"CircuitBreaker[{self.name}]: OPEN -> HALF_OPEN")
                else:
                    remaining = self.timeout - elapsed
                    raise CircuitBreakerOpenException(
                        f"Circuit breaker is open (retry in {remaining.seconds}s)"
                    )

        try:
            result = await func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info(f"CircuitBreaker[{self.name}]: HALF_OPEN -> CLOSED")
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def _on_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.success_count = 0
            logger.warning(f"CircuitBreaker[{self.name}]: HALF_OPEN -> OPEN")
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(
                    f"CircuitBreaker[{self.name}]: CLOSED -> OPEN (failures: {self.failure_count})"
                )

    def get_state(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None,
        }


webhook_circuit_breaker = CircuitBreaker(
    name="webhook",
    failure_threshold=5,
    timeout=timedelta(seconds=60),
    success_threshold=2,
)
