import os
from celery import Celery

# Просто читаем из переменных окружения
# Если не установлены - будут использованы значения по умолчанию
broker_url = os.getenv(
    "CELERY_BROKER_URL",
    "amqp://guest:guest@127.0.0.1:5672//"
)

result_backend = os.getenv(
    "CELERY_RESULT_BACKEND",
    "redis://127.0.0.1:6379/1"
)

celery_app = Celery(
    "production_control",
    broker=broker_url,
    backend=result_backend,
)

celery_app.autodiscover_tasks(["src.tasks"])

celery_app.conf.update(
    task_track_started=True,
    result_extended=True,
    broker_connection_retry_on_startup=True,
)