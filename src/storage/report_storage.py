from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from src.storage.minio_service import get_minio_service

logger = logging.getLogger(__name__)


class ReportStorage:
    def __init__(self, expires_days: int = 7):
        self._minio = get_minio_service()
        self._expires_days = expires_days

    async def save_report(
        self,
        *,
        object_name: str,
        data: bytes,
        content_type: str,
    ) -> tuple[str, int, str]:
        """
        Сохраняет отчёт в MinIO и возвращает:
        (url, size, expires_at)
        """
        logger.info("report.storage.upload started object=%s size=%s", object_name, len(data))

        await self._minio.upload_bytes(
            bucket="reports",
            object_name=object_name,
            data=data,
            content_type=content_type,
        )

        expires_sec = self._expires_days * 24 * 3600
        url = await self._minio.presigned_get_url(
            bucket="reports",
            object_name=object_name,
            expires_sec=expires_sec,
        )

        expires_at = (
            datetime.now(timezone.utc)
            + timedelta(seconds=expires_sec)
        ).isoformat()

        logger.info("report.storage.upload success object=%s", object_name)
        return url, len(data), expires_at

