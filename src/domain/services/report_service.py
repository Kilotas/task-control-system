from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from celery import Task

from src.domain.mappers.batch_report_mapper import _to_report_dto
from src.application.uow.protocol import UnitOfWorkProtocol
from src.core.exceptions import NotFoundException
from src.storage.report_storage import ReportStorage
from src.domain.services.webhook_service import dispatch_webhook_event

logger = logging.getLogger(__name__)

ReportFormat = Literal["excel", "pdf"]


@dataclass(frozen=True)
class ReportResult:
    success: bool
    file_url: str | None = None
    file_name: str | None = None
    file_size: int | None = None
    expires_at: str | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        if self.success:
            return {
                "success": True,
                "file_url": self.file_url,
                "file_name": self.file_name,
                "file_size": self.file_size,
                "expires_at": self.expires_at,
            }
        return {"success": False, "error": self.error}

class BatchReportService:
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        storage: ReportStorage,
    ):
        self._uow = uow
        self._storage = storage

    async def generate(
        self,
        task: Task,
        *,
        batch_id: int,
        fmt: ReportFormat,
    ) -> ReportResult:
        logger.info("report.service.generate started batch_id=%s fmt=%s", batch_id, fmt)

        async with self._uow:
            batch = await self._uow.batches.get_by_id_with_products_and_wc(batch_id)
            if batch is None:
                raise NotFoundException("Batch", batch_id)


            report_dto = _to_report_dto(batch)

        task.update_state(state="PROGRESS", meta={"progress": 20})

        if fmt == "excel":
            from src.utils.excel_generator import generate_batch_report
            data = generate_batch_report(batch=report_dto)
            content_type = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            ext = "xlsx"
        else:
            from src.utils.pdf_generator import generate_batch_report
            data = generate_batch_report(batch=report_dto)
            content_type = "application/pdf"
            ext = "pdf"

        task.update_state(state="PROGRESS", meta={"progress": 70})

        file_name = f"batch_{batch_id}_report.{ext}"

        url, size, expires_at = await self._storage.save_report(
            object_name=file_name,
            data=data,
            content_type=content_type,
        )

        task.update_state(state="PROGRESS", meta={"progress": 100})

        logger.info("report.service.generate success batch_id=%s", batch_id)

        dispatch_webhook_event("report_generated", {
            "batch_id": batch_id,
            "report_type": fmt,
            "file_url": url,
            "expires_at": expires_at,
        })

        return ReportResult(
            success=True,
            file_url=url,
            file_name=file_name,
            file_size=size,
            expires_at=expires_at,
        )


