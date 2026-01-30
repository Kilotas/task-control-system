import os
from celery import Celery

broker_url = os.getenv("CELERY_BROKER_URL")
result_backend = os.getenv("CELERY_RESULT_BACKEND")

if not broker_url:
    raise RuntimeError("CELERY_BROKER_URL is not set")
if not result_backend:
    raise RuntimeError("CELERY_RESULT_BACKEND is not set")

celery_app = Celery("production_control", broker=broker_url, backend=result_backend)

celery_app.autodiscover_tasks(["src.tasks"])

celery_app.conf.update(
    task_track_started=True,
    result_extended=True,
    broker_connection_retry_on_startup=True,
)
