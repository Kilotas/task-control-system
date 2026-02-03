# src/storage/minio_service.py
from __future__ import annotations

import asyncio
import io
import os
from datetime import timedelta
from functools import lru_cache

from minio import Minio
from src.core.config import get_settings

BUCKETS = {
    "reports": "Сгенерированные отчеты",
    "exports": "Экспортированные данные",
    "imports": "Загруженные файлы для импорта",
}


class MinIOService:
    def __init__(self):
        settings = get_settings()
        self.client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )


    def _ensure_buckets(self) -> None:
        for bucket in BUCKETS:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)

    def _upload_bytes(self, bucket: str, object_name: str, data: bytes, content_type: str) -> None:
        self._ensure_buckets()
        self.client.put_object(
            bucket_name=bucket,
            object_name=object_name,
            data=io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    def _presigned_get_url(self, bucket: str, object_name: str, expires_sec: int) -> str:
        self._ensure_buckets()
        return self.client.presigned_get_object(
            bucket_name=bucket,
            object_name=object_name,
            expires=timedelta(seconds=expires_sec),
        )

    def _download_bytes(self, bucket: str, object_name: str) -> bytes:
        self._ensure_buckets()
        resp = self.client.get_object(bucket_name=bucket, object_name=object_name)
        try:
            return resp.read()
        finally:
            resp.close()
            resp.release_conn()

    async def ensure_buckets(self) -> None:
        await asyncio.to_thread(self._ensure_buckets)

    async def upload_bytes(self, bucket: str, object_name: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(self._upload_bytes, bucket, object_name, data, content_type)

    async def presigned_get_url(self, bucket: str, object_name: str, expires_sec: int) -> str:
        return await (asyncio.to_thread(self._presigned_get_url, bucket, object_name, expires_sec))

    async def download_bytes(self, bucket: str, object_name: str) -> bytes:
        return await asyncio.to_thread(self._download_bytes, bucket, object_name)


@lru_cache(maxsize=1)
def get_minio_service() -> MinIOService:
    return MinIOService()

