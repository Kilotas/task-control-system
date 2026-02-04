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

    def _upload_bytes(
        self,
        bucket: str,
        object_name: str,
        data: bytes,
        content_type: str,
    ) -> None:
        self._ensure_buckets()
        self.client.put_object(
            bucket_name=bucket,
            object_name=object_name,
            data=io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    def _download_bytes(self, bucket: str, object_name: str) -> bytes:
        self._ensure_buckets()
        response = self.client.get_object(bucket, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def _presigned_get_url(
        self,
        bucket: str,
        object_name: str,
        expires_sec: int,
    ) -> str:
        self._ensure_buckets()
        return self.client.presigned_get_object(
            bucket_name=bucket,
            object_name=object_name,
            expires=timedelta(seconds=expires_sec),
        )

    def _upload_file(
        self,
        bucket: str,
        file_path: str,
        object_name: str,
        content_type: str,
    ) -> None:
        self._ensure_buckets()
        self.client.fput_object(
            bucket_name=bucket,
            object_name=object_name,
            file_path=file_path,
            content_type=content_type,
        )

    def _delete_file(self, bucket: str, object_name: str) -> None:
        self._ensure_buckets()
        self.client.remove_object(bucket, object_name)

    def _list_files(
        self,
        bucket: str,
        prefix: str | None = None,
    ) -> list[dict]:
        self._ensure_buckets()
        objects = self.client.list_objects(bucket, prefix=prefix, recursive=True)
        return [
            {
                "name": obj.object_name,
                "size": obj.size,
                "last_modified": obj.last_modified.isoformat()
                if obj.last_modified
                else None,
            }
            for obj in objects
        ]

    async def ensure_buckets(self) -> None:
        await asyncio.to_thread(self._ensure_buckets)

    async def upload_bytes(
        self,
        bucket: str,
        object_name: str,
        data: bytes,
        content_type: str,
    ) -> None:
        await asyncio.to_thread(
            self._upload_bytes,
            bucket,
            object_name,
            data,
            content_type,
        )

    async def download_bytes(self, bucket: str, object_name: str) -> bytes:
        return await asyncio.to_thread(
            self._download_bytes,
            bucket,
            object_name,
        )

    async def presigned_get_url(
        self,
        bucket: str,
        object_name: str,
        expires_sec: int,
    ) -> str:
        return await asyncio.to_thread(
            self._presigned_get_url,
            bucket,
            object_name,
            expires_sec,
        )

    async def upload_file(
        self,
        bucket: str,
        file_path: str,
        object_name: str | None = None,
        expires_days: int = 7,
    ) -> str:
        """
        Загрузить файл в MinIO.

        Args:
            bucket: Название бакета (reports, exports, imports)
            file_path: Путь к локальному файлу
            object_name: Имя объекта в MinIO (по умолчанию = имя файла)
            expires_days: Срок действия URL в днях

        Returns:
            Pre-signed URL для скачивания файла
        """
        if object_name is None:
            object_name = os.path.basename(file_path)

        content_type = self._get_content_type(file_path)

        await asyncio.to_thread(
            self._upload_file,
            bucket,
            file_path,
            object_name,
            content_type,
        )

        return await self.presigned_get_url(
            bucket,
            object_name,
            expires_days * 86400,
        )

    async def delete_file(self, bucket: str, object_name: str) -> None:
        """
        Удалить файл из MinIO.

        Args:
            bucket: Название бакета (reports, exports, imports)
            object_name: Имя объекта в MinIO
        """
        await asyncio.to_thread(
            self._delete_file,
            bucket,
            object_name,
        )

    async def list_files(
        self,
        bucket: str,
        prefix: str | None = None,
    ) -> list[dict]:
        """
        Получить список файлов в бакете.

        Args:
            bucket: Название бакета (reports, exports, imports)
            prefix: Префикс для фильтрации (например, "2024/01/")

        Returns:
            Список словарей с информацией о файлах:
            - name: Имя файла
            - size: Размер в байтах
            - last_modified: Дата последнего изменения (ISO формат)
        """
        return await asyncio.to_thread(
            self._list_files,
            bucket,
            prefix,
        )

    def _get_content_type(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        return {
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
            ".csv": "text/csv",
            ".pdf": "application/pdf",
            ".json": "application/json",
        }.get(ext, "application/octet-stream")


@lru_cache(maxsize=1)
def get_minio_service() -> MinIOService:
    return MinIOService()

