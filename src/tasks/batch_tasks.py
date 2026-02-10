import asyncio
import logging

from src.celery_app import celery_app
from src.application.uow.sqlalchemy import SqlAlchemyUnitOfWork
from src.core.database import celery_session_maker
from src.core.exceptions import AppException
from src.domain.services.batch_export_service import BatchExportService
from src.storage.report_storage import ReportStorage

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=1, name="export_batches_to_file")
def export_batches_to_file(self, filters: dict, format: str = "excel"):
    fmt = (format or "excel").lower().strip()
    if fmt not in ("excel", "csv"):
        return {"success": False, "error": "format must be 'excel' or 'csv'"}

    uow = SqlAlchemyUnitOfWork(celery_session_maker)
    storage = ReportStorage(expires_days=7)
    service = BatchExportService(uow=uow, storage=storage)

    async def _run():
        res = await service.export(self, filters=filters, fmt=fmt)
        return res.to_dict()

    try:
        return asyncio.run(_run())
    except AppException as exc:
        logger.warning("export.task.app_error %s", exc.message)
        return {"success": False, "error": exc.message}
    except Exception as exc:
        logger.exception("export.task.failed")
        raise self.retry(exc=exc, countdown=5)
