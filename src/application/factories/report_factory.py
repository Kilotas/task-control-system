from src.application.services.report_service import BatchReportService
from src.application.uow.sqlalchemy import SqlAlchemyUnitOfWork
from src.core.database import celery_session_maker
from src.storage.report_storage import ReportStorage


def build_batch_report_service() -> BatchReportService:
    uow = SqlAlchemyUnitOfWork(celery_session_maker)
    storage = ReportStorage(expires_days=7)
    return BatchReportService(uow=uow, storage=storage)
