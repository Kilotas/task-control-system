import asyncio
import logging

from src.celery_app import celery_app
from src.application.uow.sqlalchemy import SqlAlchemyUnitOfWork
from src.core.database import celery_session_maker
from src.core.exceptions import AppException
from src.domain.services.import_service import BatchImportService

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=1, name="import_batches_from_file")
def import_batches_from_file(self, file_object_name: str, user_id: int):
    uow = SqlAlchemyUnitOfWork(celery_session_maker)
    service = BatchImportService(uow=uow)

    async def _run():
        res = await service.import_from_minio(self, object_name=file_object_name, user_id=user_id)
        return res.to_dict()

    try:
        result = asyncio.run(_run())
        if result.get("success"):
            from src.domain.services.webhook_service import dispatch_webhook_event
            dispatch_webhook_event("import_completed", {
                "total_rows": result.get("total_rows", 0),
                "created": result.get("created", 0),
                "skipped": result.get("skipped", 0),
                "errors": result.get("errors", []),
            })
        return result
    except AppException as exc:
        logger.warning("import.task.app_error %s", exc.message)
        return {"success": False, "error": exc.message}
    except Exception as exc:
        logger.exception("import.task.failed")
        raise self.retry(exc=exc, countdown=5)
