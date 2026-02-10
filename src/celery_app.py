import os
from celery import Celery
from celery.schedules import crontab

broker_url = os.getenv("CELERY_BROKER_URL")
result_backend = os.getenv("CELERY_RESULT_BACKEND")

if not broker_url:
    raise RuntimeError("CELERY_BROKER_URL is not set")
if not result_backend:
    raise RuntimeError("CELERY_RESULT_BACKEND is not set")

celery_app = Celery("production_control", broker=broker_url, backend=result_backend)

import src.tasks.batch_tasks

celery_app.autodiscover_tasks(["src.tasks"])

celery_app.conf.update(
    task_track_started=True,
    result_extended=True,
    broker_connection_retry_on_startup=True,
    timezone="UTC",
    beat_schedule={
        "auto-close-expired-batches": {
            "task": "auto_close_expired_batches",
            "schedule": crontab(hour=1, minute=0),
        },
        "cleanup-old-files": {
            "task": "cleanup_old_files",
            "schedule": crontab(hour=2, minute=0),
        },
        "update-statistics": {
            "task": "update_cached_statistics",
            "schedule": crontab(minute="*/5"),
        },
        "retry-failed-webhooks": {
            "task": "retry_failed_webhooks",
            "schedule": crontab(minute="*/15"),
        },
    },
)
