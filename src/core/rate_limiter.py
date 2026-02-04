from __future__ import annotations

import time
from functools import wraps
from typing import Callable

from fastapi import Request, HTTPException, status
from redis.asyncio import Redis

from src.core.config import get_settings


class RateLimiter:
    def __init__(self, redis: Redis):
        self._redis = redis
        self._settings = get_settings()

    async def is_allowed(
        self,
        key: str,
        max_requests: int | None = None,
        window_seconds: int | None = None,
    ) -> tuple[bool, dict]:
        if not self._settings.rate_limit_enabled:
            return True, {}

        max_requests = max_requests or self._settings.rate_limit_requests
        window_seconds = window_seconds or self._settings.rate_limit_window

        now = time.time()
        window_start = now - window_seconds

        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, window_seconds)
        results = await pipe.execute()

        request_count = results[2]
        allowed = request_count <= max_requests

        remaining = max(0, max_requests - request_count)
        reset_time = int(now + window_seconds)

        headers = {
            "X-RateLimit-Limit": str(max_requests),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_time),
        }

        if not allowed:
            retry_after = int(window_seconds - (now - window_start))
            headers["Retry-After"] = str(max(1, retry_after))

        return allowed, headers


_rate_limiter: RateLimiter | None = None


async def init_rate_limiter() -> RateLimiter:
    global _rate_limiter
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    _rate_limiter = RateLimiter(redis)
    return _rate_limiter


def get_rate_limiter() -> RateLimiter:
    if _rate_limiter is None:
        raise RuntimeError("Rate limiter not initialized")
    return _rate_limiter


async def close_rate_limiter() -> None:
    global _rate_limiter
    if _rate_limiter and _rate_limiter._redis:
        await _rate_limiter._redis.close()
    _rate_limiter = None


def rate_limit(
    max_requests: int | None = None,
    window_seconds: int | None = None,
    key_func: Callable[[Request], str] | None = None,
):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request: Request | None = kwargs.get("request")
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if not request:
                return await func(*args, **kwargs)

            if key_func:
                rate_key = key_func(request)
            else:
                client_ip = request.client.host if request.client else "unknown"
                rate_key = f"rate_limit:{client_ip}:{request.url.path}"

            try:
                limiter = get_rate_limiter()
                allowed, headers = await limiter.is_allowed(
                    rate_key, max_requests, window_seconds
                )

                if not allowed:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many requests",
                        headers=headers,
                    )

                response = await func(*args, **kwargs)
                return response

            except RuntimeError:
                return await func(*args, **kwargs)

        return wrapper
    return decorator
