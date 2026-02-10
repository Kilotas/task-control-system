from __future__ import annotations

import logging
from datetime import date, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError

from src.api.v1.schemas.batch import BatchUpdateIn, BatchListQuery
from src.application.uow.protocol import UnitOfWorkProtocol
from src.core.exceptions import ConflictException, ValidationException, NotFoundException
from src.domain.services.webhook_service import dispatch_webhook_event
from src.domain.services.redis_service import CacheInvalidator

from datetime import datetime

logger = logging.getLogger(__name__)


class BatchService:
    def __init__(self, uow: UnitOfWorkProtocol):
        self.uow = uow
        self._cache = CacheInvalidator()

    async def create_batches(self, items: list[dict[str, Any]]) -> list:
        logger.info("Creating batches: count=%d", len(items))
        self._validate_items(items)

        async with self.uow as uow:
            prepared = await self._prepare(uow, items)
            created = await self._persist(uow, prepared)

            logger.info(
                "Batches successfully created: count=%d ids=%s",
                len(created),
                [b.id for b in created],
            )

            for batch, item in zip(created, items):
                dispatch_webhook_event("batch_created", {
                    "id": batch.id,
                    "batch_number": batch.batch_number,
                    "batch_date": str(batch.batch_date),
                    "nomenclature": batch.nomenclature,
                    "work_center": item.get("work_center_identifier", ""),
                })

            await self._cache.on_batch_created()

            return created


    async def get_batch_by_id(self, batch_id: int):
        async with self.uow as uow:
            batch = await uow.batches.get_by_id_with_products(batch_id)
            if batch is None:
                raise NotFoundException("Batch", batch_id)
            return batch


    async def update_batch(self, batch_id: int, data: BatchUpdateIn):
        async with self.uow as uow:
            batch = await uow.batches.get_by_id_with_wc(batch_id)
            if batch is None:
                raise NotFoundException("Batch", batch_id)

            changes = {}

            if data.is_closed and not batch.is_closed:
                batch.is_closed = True
                batch.closed_at = datetime.now(timezone.utc)
                changes["is_closed"] = True
            elif not data.is_closed and batch.is_closed:
                batch.is_closed = False
                batch.closed_at = None
                changes["is_closed"] = False

            await uow.batches.update(batch)
            await uow.flush()

            if batch.is_closed and changes.get("is_closed"):
                total = await uow.products.count_by_batch(batch_id)
                aggregated = await uow.products.count_aggregated_by_batch(batch_id)
                rate = round(aggregated / total * 100, 2) if total else 0.0
                dispatch_webhook_event("batch_closed", {
                    "id": batch.id,
                    "batch_number": batch.batch_number,
                    "closed_at": batch.closed_at.isoformat() if batch.closed_at else None,
                    "statistics": {
                        "total_products": total,
                        "aggregated": aggregated,
                        "aggregation_rate": rate,
                    },
                })
            elif changes:
                dispatch_webhook_event("batch_updated", {
                    "id": batch.id,
                    "batch_number": batch.batch_number,
                    "changes": changes,
                })

            if changes:
                await self._cache.on_batch_updated(batch_id)

            return batch

    async def list_batches(self, query: BatchListQuery) -> list[dict]:
        async with self.uow as uow:
            return await uow.batches.list(
                is_closed=query.is_closed,
                batch_number=query.batch_number,
                batch_date=query.batch_date,
                work_center_id=query.work_center_id,
                shift=query.shift,
                offset=query.offset,
                limit=query.limit,
            )


    async def aggregate_batch_products(self, batch_id: int) -> dict:
        async with self.uow as uow:
            batch = await uow.batches.get_by_id(batch_id)
            if batch is None:
                raise NotFoundException("Batch", batch_id)


            if batch.is_closed:
                raise ValidationException("Нельзя агрегировать продукцию в закрытой партии")

            total = await uow.products.count_by_batch(batch_id)
            already = await uow.products.count_aggregated_by_batch(batch_id)

            updated = await uow.products.aggregate_by_batch(batch_id)

            await uow.flush()

            if updated > 0:
                await self._cache.on_product_aggregated(batch_id)

            return {
                "batch_id": batch_id,
                "updated_count": updated,
                "already_aggregated": already,
                "total_products": total,
            }

    def _validate_items(self, items: list[dict[str, Any]]) -> None:
        if not items:
            logger.warning("Batch creation failed: empty payload")
            raise ValidationException("Пустой список заданий")

        seen: set[tuple[int, date]] = set()
        for batch in items:
            key = (batch["batch_number"], batch["batch_date"])
            if key in seen:
                logger.warning(
                    "Duplicate batch in request: batch_number=%s batch_date=%s",
                    batch["batch_number"],
                    batch["batch_date"],
                )
                raise ConflictException(
                    f"Дубликат в запросе: НомерПартии={batch['batch_number']} "
                    f"ДатаПартии={batch['batch_date']}"
                )
            seen.add(key)

    async def _prepare(
        self,
        uow: UnitOfWorkProtocol,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        prepared: list[dict[str, Any]] = []

        for batch in items:
            exists = await uow.batches.exists_by_number_and_date(
                batch["batch_number"],
                batch["batch_date"],
            )
            if exists:
                logger.warning(
                    "Batch already exists: batch_number=%s batch_date=%s",
                    batch["batch_number"],
                    batch["batch_date"],
                )
                raise ConflictException(
                    f"Batch уже существует: НомерПартии={batch['batch_number']} "
                    f"ДатаПартии={batch['batch_date']}"
                )

            wc = await self._get_or_create_wc(
                uow=uow,
                identifier=batch["work_center_identifier"],
                name=batch["work_center_name"],
            )

            prepared.append(
                {
                    "is_closed": batch["is_closed"],
                    "closed_at": batch["shift_end"] if batch["is_closed"] else None,
                    "task_description": batch["task_description"],
                    "work_center_id": wc.id,
                    "shift": batch["shift"],
                    "team": batch["team"],
                    "batch_number": batch["batch_number"],
                    "batch_date": batch["batch_date"],
                    "nomenclature": batch["nomenclature"],
                    "ekn_code": batch["ekn_code"],
                    "shift_start": batch["shift_start"],
                    "shift_end": batch["shift_end"],
                }
            )

        return prepared


    async def _get_or_create_wc(
        self,
        uow: UnitOfWorkProtocol,
        identifier: str,
        name: str,
    ):
        wc = await uow.work_centers.get_by_identifier(identifier)
        if wc is not None:
            return wc

        logger.info(
            "WorkCenter not found -> creating: identifier=%s name=%s",
            identifier,
            name,
        )

        try:
            wc = await uow.work_centers.create(identifier=identifier, name=name)
            return wc
        except IntegrityError:
            await uow.rollback()
            logger.warning(
                "WorkCenter create race detected, reloading: identifier=%s",
                identifier,
            )
            wc = await uow.work_centers.get_by_identifier(identifier)
            if wc is None:
                raise ConflictException(f"WorkCenter create failed: {identifier}")
            return wc


    async def _persist(self, uow: UnitOfWorkProtocol, prepared: list[dict[str, Any]]):
        try:
            created = await uow.batches.bulk_create(prepared)
            await uow.commit()
            return created
        except IntegrityError:
            await uow.rollback()
            logger.warning(
                "IntegrityError while creating batches (possible duplicates by uq_batch_number_date)"
            )
            raise ConflictException("Конфликт при создании batches (возможен дубль)")


