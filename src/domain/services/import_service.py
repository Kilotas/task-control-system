from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from celery import Task

from src.application.uow.protocol import UnitOfWorkProtocol
from src.core.exceptions import ValidationException
from src.domain.dto.import_dto import ImportResult, ImportErrorItem
from src.storage.minio_service import get_minio_service
from src.utils.excel_parser import parse_batches_excel

logger = logging.getLogger(__name__)


@dataclass
class ImportCounters:
    total: int = 0
    created: int = 0
    skipped: int = 0


class BatchImportService:
    def __init__(self, uow: UnitOfWorkProtocol):
        self._uow = uow
        self._minio = get_minio_service()


    async def import_from_minio(self, task: Task, *, object_name: str, user_id: int) -> ImportResult:
        logger.info("import.started object=%s user_id=%s", object_name, user_id)

        task.update_state(state="PROGRESS", meta={"current": 0, "total": 0, "created": 0, "skipped": 0, "progress": 0})

        data = await self._download_file(object_name)
        rows = self._parse_file(data)

        counters = ImportCounters(total=len(rows))
        errors: list[ImportErrorItem] = []

        await self._import_rows(task, rows, counters, errors)

        result = ImportResult(
            success=True,
            total_rows=counters.total,
            created=counters.created,
            skipped=counters.skipped,
            errors=errors,
        )

        logger.info(
            "import.finished object=%s total=%s created=%s skipped=%s errors=%s",
            object_name,
            counters.total,
            counters.created,
            counters.skipped,
            len(errors),
        )
        return result


    async def _download_file(self, object_name: str) -> bytes:
        logger.debug("import.download.started object=%s bucket=imports", object_name)
        data = await self._minio.download_bytes(bucket="imports", object_name=object_name)
        logger.debug("import.download.success object=%s size=%s", object_name, len(data))
        return data


    def _parse_file(self, data: bytes) -> list[dict[str, Any]]:
        logger.debug("import.parse.started size=%s", len(data))
        try:
            rows = parse_batches_excel(data)
        except Exception as exc:
            logger.exception("import.parse.failed")
            raise ValidationException(f"Invalid file format: {exc}")

        logger.info("import.parse.success rows=%s", len(rows))
        return rows

    async def _import_rows(
            self,
            task: Task,
            rows: list[dict[str, Any]],
            counters: ImportCounters,
            errors: list[ImportErrorItem],
    ) -> None:
        logger.info("import.db.started total_rows=%s", counters.total)

        if counters.total == 0:
            logger.warning("import.db.empty_file")
            return

        processed = 0
        prepared_batches: list[dict[str, Any]] = []
        seen_in_file: set[tuple[int, Any]] = set()

        async with self._uow as uow:
            for excel_row_num, item in enumerate(rows, start=2):
                try:
                    bn = int(item["batch_number"])
                    bd = item["batch_date"]
                    key = (bn, bd)

                    if key in seen_in_file:
                        counters.skipped += 1
                        errors.append(
                            ImportErrorItem(row=excel_row_num, error="Duplicate batch number and date (in file)"))
                        continue
                    seen_in_file.add(key)

                    exists = await uow.batches.exists_by_number_and_date(bn, bd)
                    if exists:
                        counters.skipped += 1
                        errors.append(ImportErrorItem(row=excel_row_num, error="Duplicate batch number and date"))
                        continue

                    wc = await self._get_or_create_work_center(uow, item)

                    prepared_batches.append({
                        "is_closed": bool(item["is_closed"]),
                        "closed_at": item["shift_end"] if item["is_closed"] else None,
                        "task_description": item["task_description"],
                        "work_center_id": wc.id,
                        "shift": item["shift"],
                        "team": item["team"],
                        "batch_number": bn,
                        "batch_date": bd,
                        "nomenclature": item["nomenclature"],
                        "ekn_code": item["ekn_code"],
                        "shift_start": item["shift_start"],
                        "shift_end": item["shift_end"],
                    })

                    counters.created += 1

                except Exception as exc:
                    counters.skipped += 1
                    errors.append(ImportErrorItem(row=excel_row_num, error=str(exc)))
                    logger.warning("import.row.failed row=%s error=%s", excel_row_num, exc)

                processed += 1
                if processed % 20 == 0 or processed == counters.total:
                    self._update_progress(task, processed, counters)

            if prepared_batches:
                try:
                    logger.info("import.db.bulk_create started count=%s", len(prepared_batches))
                    await uow.batches.bulk_create(prepared_batches)
                    logger.info("import.db.bulk_create success")
                except Exception as exc:
                    logger.exception("import.db.bulk_create.failed")
                    raise

            logger.info("import.db.commit started created=%s skipped=%s", counters.created, counters.skipped)
            await uow.commit()
            logger.info("import.db.commit success")

    async def _import_one_row(self, uow: UnitOfWorkProtocol, item: dict[str, Any]) -> dict[str, Any] | None:
        """
        Возвращает:
          - dict с данными для bulk_create → если запись нужно создать
          - None → если дубликат (пропускаем)
        """
        exists = await uow.batches.exists_by_number_and_date(item["batch_number"], item["batch_date"])
        if exists:
            logger.debug(
                "import.row.duplicate batch_number=%s batch_date=%s",
                item["batch_number"],
                item["batch_date"],
            )
            return None

        wc = await self._get_or_create_work_center(uow, item)


        batch_data: dict[str, Any] = {
            "is_closed": bool(item["is_closed"]),
            "closed_at": item["shift_end"] if item["is_closed"] else None,
            "task_description": item["task_description"],
            "work_center_id": wc.id,
            "shift": item["shift"],
            "team": item["team"],
            "batch_number": int(item["batch_number"]),
            "batch_date": item["batch_date"],
            "nomenclature": item["nomenclature"],
            "ekn_code": item["ekn_code"],
            "shift_start": item["shift_start"],
            "shift_end": item["shift_end"],
        }

        logger.debug(
            "import.row.prepared batch_number=%s batch_date=%s wc_id=%s",
            batch_data["batch_number"],
            batch_data["batch_date"],
            wc.id,
        )
        return batch_data


    async def _get_or_create_work_center(self, uow: UnitOfWorkProtocol, item: dict[str, Any]):
        identifier = item["work_center_identifier"]
        name = item["work_center_name"]

        wc = await uow.work_centers.get_by_identifier(identifier)
        if wc is not None:
            return wc

        logger.debug("import.wc.create identifier=%s name=%s", identifier, name)
        wc = await uow.work_centers.create(identifier=identifier, name=name)
        return wc


    def _update_progress(self, task: Task, processed: int, counters: ImportCounters) -> None:
        progress = int((processed / max(counters.total, 1)) * 100)
        task.update_state(
            state="PROGRESS",
            meta={
                "current": processed,
                "total": counters.total,
                "created": counters.created,
                "skipped": counters.skipped,
                "progress": progress,
            },
        )
