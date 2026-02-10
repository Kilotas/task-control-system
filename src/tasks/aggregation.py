from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Dict, List, Tuple

from celery import states
from celery.exceptions import Ignore

from src.celery_app import celery_app
from src.application.uow.sqlalchemy import SqlAlchemyUnitOfWork
from src.core.database import async_session_maker
from src.core.exceptions import NotFoundException
from src.core.database import celery_session_maker

def _chunked(seq: list[str], size: int) -> list[list[str]]:
    """Разбивает список на части заданного размера."""
    return [seq[i:i + size] for i in range(0, len(seq), size)]


async def _validate_batch_exists(uow: SqlAlchemyUnitOfWork, batch_id: int) -> None:
    """Проверяет существование партии."""
    batch = await uow.batches.get_by_id(batch_id)
    if batch is None:
        raise NotFoundException("Batch", batch_id)


def _create_found_map(statuses: List[Tuple[str, bool]]) -> Dict[str, bool]:
    """Создает словарь найденных товаров из результатов запроса."""
    return {code: is_aggr for code, is_aggr in statuses}


def _find_missing_codes(part: List[str], found_map: Dict[str, bool]) -> List[Dict[str, str]]:
    """Находит коды, которые отсутствуют в базе данных."""
    errors = []
    for code in part:
        if code not in found_map:
            errors.append({"code": code, "reason": "not found"})
    return errors


def _filter_codes_for_aggregation(found_map: Dict[str, bool]) -> Tuple[List[str], List[Dict[str, str]]]:
    """Фильтрует коды для агрегации, отделяя уже упакованные."""
    to_aggregate = []
    errors = []

    for code, is_aggr in found_map.items():
        if is_aggr:
            errors.append({"code": code, "reason": "already aggregated"})
        else:
            to_aggregate.append(code)

    return to_aggregate, errors


async def _process_chunk(
        uow: SqlAlchemyUnitOfWork,
        batch_id: int,
        part: List[str],
        errors: List[Dict[str, str]]
) -> int:
    """Обрабатывает одну часть (чанк) товаров."""
    statuses = await uow.products.fetch_statuses_by_codes(batch_id=batch_id, codes=part)
    found_map = _create_found_map(statuses)

    missing_errors = _find_missing_codes(part, found_map)
    errors.extend(missing_errors)

    to_aggregate, already_aggregated_errors = _filter_codes_for_aggregation(found_map)
    errors.extend(already_aggregated_errors)

    if to_aggregate:
        updated = await uow.products.aggregate_by_codes(
            batch_id=batch_id,
            codes_to_aggregate=to_aggregate
        )
        return updated

    return 0


async def _run_aggregation(batch_id: int, unique_codes: List[str], task_self) -> Dict:
    """Основная логика массовой агрегации."""
    total = len(unique_codes)
    aggregated_total = 0
    errors: List[Dict[str, str]] = []

    chunks = _chunked(unique_codes, 500)
    processed = 0

    async with SqlAlchemyUnitOfWork(celery_session_maker) as uow:
        await _validate_batch_exists(uow, batch_id)

        for part in chunks:
            updated = await _process_chunk(uow, batch_id, part, errors)
            aggregated_total += updated

            await uow.flush()

            processed += len(part)
            _update_task_progress(task_self, processed, total)

    return _build_result(total, aggregated_total, errors)


def _update_task_progress(task_self, processed: int, total: int) -> None:
    """Обновляет состояние задачи с прогрессом."""
    task_self.update_state(
        state="PROGRESS",
        meta={
            "current": processed,
            "total": total,
            "progress": int((processed / max(total, 1)) * 100),
        },
    )


def _build_result(total: int, aggregated: int, errors: List[Dict[str, str]]) -> Dict:
    """Формирует итоговый результат агрегации."""
    return {
        "success": True,
        "total": total,
        "aggregated": aggregated,
        "failed": len(errors),
        "errors": errors,
    }


def _handle_task_error(task_self, exc: Exception) -> None:
    """Обрабатывает ошибки в задаче."""
    if isinstance(exc, NotFoundException):
        task_self.update_state(state=states.FAILURE, meta={"detail": str(exc)})
        raise Ignore()

    raise task_self.retry(exc=exc, countdown=5)


@celery_app.task(name="aggregate_products_batch", bind=True,
                 max_retries=3)
def aggregate_products_batch(self, batch_id: int, unique_codes: list[str], user_id: int | None = None):
    """
    Асинхронная массовая агрегация продукции.

    Возвращает:
    {
      "success": True,
      "total": N,
      "aggregated": X,
      "failed": Y,
      "errors": [{"code": "...", "reason": "..."}]
    }
    """
    try:
        result = asyncio.run(_run_aggregation(batch_id, unique_codes, self))
        if result.get("success") and result.get("aggregated", 0) > 0:
            from src.domain.services.webhook_service import dispatch_webhook_event
            dispatch_webhook_event("product_aggregated", {
                "batch_id": batch_id,
                "aggregated_count": result["aggregated"],
                "total": result["total"],
                "failed": result["failed"],
            })
        return result
    except Exception as exc:
        _handle_task_error(self, exc)