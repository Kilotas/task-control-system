from __future__ import annotations

import logging

from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core.config import get_settings

logger = logging.getLogger(__name__)


def get_limiter() -> Limiter:
    settings = get_settings()

    if settings.cache_backend == "redis":
        storage_uri = settings.redis_url
    else:
        storage_uri = "memory://"

    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[f"{settings.rate_limit_requests}/{settings.rate_limit_window}second"],
        storage_uri=storage_uri,
        enabled=settings.rate_limit_enabled,
    )

    logger.info(f"Rate limiter initialized (storage: {storage_uri})")
    return limiter


limiter = get_limiter()
