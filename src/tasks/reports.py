import asyncio
import logging

from src.celery_app import celery_app
from src.domain.services.report_service import BatchReportService
from src.application.uow.sqlalchemy import SqlAlchemyUnitOfWork
from src.core.database import celery_session_maker
from src.core.exceptions import AppException
from src.storage.report_storage import ReportStorage

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, name="generate_batch_report")
def generate_batch_report(
    self,
    batch_id: int,
    format: str = "excel",
    user_email: str | None = None,
):
    fmt = format.lower().strip()
    if fmt not in ("excel", "pdf"):
        return {"success": False, "error": "format must be 'excel' or 'pdf'"}

    uow = SqlAlchemyUnitOfWork(celery_session_maker)
    storage = ReportStorage(expires_days=7)
    service = BatchReportService(uow=uow, storage=storage)

    async def _run():
        result = await service.generate(self, batch_id=batch_id, fmt=fmt)
        return result.to_dict()

    try:
        return asyncio.run(_run())
    except AppException as exc:
        logger.warning("report.task.app_error %s", exc)
        return {"success": False, "error": exc.message}
    except Exception as exc:
        logger.exception("report.task.failed batch_id=%s", batch_id)
        raise self.retry(exc=exc, countdown=5)
