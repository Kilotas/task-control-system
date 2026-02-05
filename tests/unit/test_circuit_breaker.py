import pytest
from datetime import timedelta

from src.core.circuit_breaker import CircuitBreaker
from src.core.circuit_breaker_types import CircuitState, CircuitBreakerOpenException


@pytest.mark.asyncio
class TestCircuitBreaker:

    async def test_initial_state_closed(self):
        cb = CircuitBreaker(failure_threshold=3)

        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    async def test_successful_call(self):
        cb = CircuitBreaker(failure_threshold=3)

        async def success_func():
            return "ok"

        result = await cb.call(success_func)

        assert result == "ok"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    async def test_failure_increments_count(self):
        cb = CircuitBreaker(failure_threshold=3)

        async def fail_func():
            raise Exception("error")

        with pytest.raises(Exception):
            await cb.call(fail_func)

        assert cb.failure_count == 1
        assert cb.state == CircuitState.CLOSED

    async def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)

        async def fail_func():
            raise Exception("error")

        for _ in range(3):
            with pytest.raises(Exception):
                await cb.call(fail_func)

        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 3

    async def test_open_state_rejects_calls(self):
        cb = CircuitBreaker(failure_threshold=1, timeout=timedelta(seconds=60))

        async def fail_func():
            raise Exception("error")

        with pytest.raises(Exception):
            await cb.call(fail_func)

        assert cb.state == CircuitState.OPEN

        async def any_func():
            return "should not reach"

        with pytest.raises(CircuitBreakerOpenException):
            await cb.call(any_func)

    async def test_success_resets_failure_count(self):
        cb = CircuitBreaker(failure_threshold=3)

        async def fail_func():
            raise Exception("error")

        async def success_func():
            return "ok"

        with pytest.raises(Exception):
            await cb.call(fail_func)

        assert cb.failure_count == 1

        await cb.call(success_func)

        assert cb.failure_count == 0

    async def test_half_open_success_closes(self):
        cb = CircuitBreaker(
            failure_threshold=1,
            timeout=timedelta(seconds=0),
            success_threshold=2,
        )

        async def fail_func():
            raise Exception("error")

        async def success_func():
            return "ok"

        with pytest.raises(Exception):
            await cb.call(fail_func)

        assert cb.state == CircuitState.OPEN

        await cb.call(success_func)
        assert cb.state == CircuitState.HALF_OPEN

        await cb.call(success_func)
        assert cb.state == CircuitState.CLOSED

    async def test_half_open_failure_reopens(self):
        cb = CircuitBreaker(
            failure_threshold=1,
            timeout=timedelta(seconds=0),
            success_threshold=2,
        )

        async def fail_func():
            raise Exception("error")

        async def success_func():
            return "ok"

        with pytest.raises(Exception):
            await cb.call(fail_func)

        assert cb.state == CircuitState.OPEN

        await cb.call(success_func)
        assert cb.state == CircuitState.HALF_OPEN

        with pytest.raises(Exception):
            await cb.call(fail_func)

        assert cb.state == CircuitState.OPEN

    async def test_get_state(self):
        cb = CircuitBreaker(name="test_breaker", failure_threshold=3)

        state = cb.get_state()

        assert state["name"] == "test_breaker"
        assert state["state"] == "closed"
        assert state["failure_count"] == 0
        assert state["success_count"] == 0
        assert state["last_failure"] is None
