from __future__ import annotations

import logging
from datetime import date
from typing import Literal, Any

from celery import Task

from src.application.uow.protocol import UnitOfWorkProtocol
from src.domain.dto.export_dto import BatchExportRowDTO, ExportResult
from src.storage.report_storage import ReportStorage
from src.utils.excel_report import export_batches_to_excel, export_batches_to_csv

logger = logging.getLogger(__name__)

ExportFormat = Literal["excel", "csv"]


class BatchExportService:
    def __init__(self, uow: UnitOfWorkProtocol, storage: ReportStorage):
        self._uow = uow
        self._storage = storage

    async def export(self, task: Task, *, filters: dict[str, Any], fmt: ExportFormat) -> ExportResult:
        logger.info("export.started fmt=%s filters=%s", fmt, filters)

        parsed_filters = self._parse_filters(filters)

        self._update_progress(task, 10, "Получение данных из БД")

        batches = await self._fetch_batches(parsed_filters)

        rows = self._convert_to_dto(batches)

        self._update_progress(task, 50, "Генерация отчета")

        file_data, content_type, extension = self._generate_report_file(rows, fmt)

        self._update_progress(task, 80, "Сохранение файла")

        file_name = f"batches_export.{extension}"
        url, size, _ = await self._save_report_file(file_name, file_data, content_type)


        self._update_progress(task, 100, "Экспорт завершен")

        return self._create_result(url, file_name, len(rows))


    def _parse_filters(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Парсит и валидирует фильтры."""
        parsed = {
            "is_closed": filters.get("is_closed"),
            "date_from": self._parse_date(filters.get("date_from")),
            "date_to": self._parse_date(filters.get("date_to")),
            "work_center_identifier": filters.get("work_center_identifier"),
            "shift": filters.get("shift"),
        }
        return parsed

    def _parse_date(self, value: Any) -> date | None:
        """Преобразует строку в date."""
        if value is None:
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            return date.fromisoformat(value)
        raise ValueError(f"Cannot parse date from {type(value)}")

    async def _fetch_batches(self, filters: dict) -> list:
        """Получает батчи из БД по фильтрам."""
        async with self._uow as uow:
            return await uow.batches.export_list(
                is_closed=filters["is_closed"],
                date_from=filters["date_from"],
                date_to=filters["date_to"],
                work_center_identifier=filters["work_center_identifier"],
                shift=filters["shift"],
            )

    def _convert_to_dto(self, batches: list) -> list[BatchExportRowDTO]:
        """Конвертирует Batch в DTO."""
        return [
            BatchExportRowDTO(
                id=b.id,
                batch_number=b.batch_number,
                batch_date=b.batch_date,
                is_closed=b.is_closed,
                closed_at=b.closed_at,
                work_center_identifier=b.work_center.identifier if b.work_center else None,
                work_center_name=b.work_center.name if b.work_center else None,
                shift=b.shift,
                team=b.team,
                nomenclature=b.nomenclature,
                ekn_code=b.ekn_code,
                shift_start=b.shift_start,
                shift_end=b.shift_end,
            )
            for b in batches
        ]

    def _generate_report_file(self, rows: list, fmt: ExportFormat) -> tuple[bytes, str, str]:
        """Генерирует файл отчета."""
        if fmt == "excel":
            data = export_batches_to_excel(rows)
            return data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"
        else:
            data = export_batches_to_csv(rows)
            return data, "text/csv", "csv"

    async def _save_report_file(self, file_name: str, data: bytes, content_type: str):
        """Сохраняет файл в хранилище."""
        return await self._storage.save_report(
            object_name=file_name,
            data=data,
            content_type=content_type,
        )

    def _update_progress(self, task: Task, progress: int, message: str = ""):
        """Обновляет прогресс задачи."""
        task.update_state(
            state="PROGRESS",
            meta={"progress": progress, "message": message}
        )

    def _create_result(self, url: str, file_name: str, total: int) -> ExportResult:
        """Создает объект результата."""
        logger.info("export.success total=%s file=%s", total, file_name)
        return ExportResult(
            success=True,
            file_url=url,
            file_name=file_name,
            total_batches=total
        )