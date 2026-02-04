from __future__ import annotations

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.config import get_settings
from src.core.rate_limiter import get_rate_limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()

        if not settings.rate_limit_enabled:
            return await call_next(request)

        if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        rate_key = f"rate_limit:global:{client_ip}"

        try:
            limiter = get_rate_limiter()
            allowed, headers = await limiter.is_allowed(rate_key)

            if not allowed:
                return Response(
                    content='{"detail":"Too many requests"}',
                    status_code=429,
                    media_type="application/json",
                    headers=headers,
                )

            response = await call_next(request)

            for key, value in headers.items():
                response.headers[key] = value

            return response

        except RuntimeError:
            return await call_next(request)
