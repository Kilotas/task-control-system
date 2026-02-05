import pytest
from unittest.mock import patch, MagicMock

from src.core.rate_limiter import get_limiter


class TestRateLimiter:

    def test_limiter_created_with_redis(self):
        with patch("src.core.rate_limiter.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                cache_backend="redis",
                redis_url="redis://localhost:6379/0",
                rate_limit_enabled=True,
                rate_limit_requests=100,
                rate_limit_window=60,
            )

            limiter = get_limiter()

            assert limiter is not None
            assert limiter.enabled is True

    def test_limiter_created_with_memory(self):
        with patch("src.core.rate_limiter.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                cache_backend="memory",
                redis_url="redis://localhost:6379/0",
                rate_limit_enabled=True,
                rate_limit_requests=50,
                rate_limit_window=30,
            )

            limiter = get_limiter()

            assert limiter is not None

    def test_limiter_disabled(self):
        with patch("src.core.rate_limiter.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                cache_backend="memory",
                redis_url="redis://localhost:6379/0",
                rate_limit_enabled=False,
                rate_limit_requests=100,
                rate_limit_window=60,
            )

            limiter = get_limiter()

            assert limiter.enabled is False
