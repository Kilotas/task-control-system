import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone

import httpx

from src.celery_app import celery_app
from src.application.uow.sqlalchemy import SqlAlchemyUnitOfWork
from src.core.database import celery_session_maker
from src.storage.minio_service import BUCKETS, get_minio_service

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="auto_close_expired_batches")
def auto_close_expired_batches(self):
    uow = SqlAlchemyUnitOfWork(celery_session_maker)

    async def _run():
        async with uow:
            now = datetime.now(timezone.utc)
            count = await uow.batches.close_expired(now)
            logger.info("auto_close_expired_batches: closed %d batches", count)
            return {"closed": count}

    return asyncio.run(_run())


@celery_app.task(bind=True, name="cleanup_old_files")
def cleanup_old_files(self):
    minio = get_minio_service()
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    removed = 0

    for bucket in BUCKETS:
        objects = minio.client.list_objects(bucket, recursive=True)
        for obj in objects:
            if obj.last_modified and obj.last_modified < cutoff:
                minio.client.remove_object(bucket, obj.object_name)
                removed += 1

    logger.info("cleanup_old_files: removed %d objects", removed)
    return {"removed": removed}


@celery_app.task(bind=True, name="update_cached_statistics")
def update_cached_statistics(self):
    uow = SqlAlchemyUnitOfWork(celery_session_maker)

    async def _run():
        import redis.asyncio as aioredis
        from src.core.config import get_settings

        settings = get_settings()
        r = aioredis.from_url(settings.redis_url, decode_responses=True)

        try:
            async with uow:
                stats = await uow.batches.count_statistics()
            await r.set(
                "prod_control:statistics",
                json.dumps(stats, default=str),
                ex=360,
            )
            logger.info("update_cached_statistics: %s", stats)
            return stats
        finally:
            await r.aclose()

    return asyncio.run(_run())


@celery_app.task(bind=True, name="retry_failed_webhooks")
def retry_failed_webhooks(self):
    uow = SqlAlchemyUnitOfWork(celery_session_maker)

    async def _run():
        retried = 0
        async with uow:
            deliveries = await uow.webhooks.get_failed_deliveries(limit=50)
            async with httpx.AsyncClient(timeout=10) as client:
                for delivery in deliveries:
                    sub = delivery.subscription
                    body = json.dumps(delivery.payload, default=str)
                    signature = hmac.new(
                        sub.secret_key.encode(), body.encode(), hashlib.sha256
                    ).hexdigest()

                    delivery.attempts += 1
                    try:
                        resp = await client.post(
                            sub.url,
                            content=body,
                            headers={
                                "Content-Type": "application/json",
                                "X-Webhook-Signature": signature,
                            },
                        )
                        delivery.response_status = resp.status_code
                        delivery.response_body = resp.text[:1024]
                        if 200 <= resp.status_code < 300:
                            delivery.status = "success"
                            delivery.delivered_at = datetime.now(timezone.utc)
                        else:
                            delivery.status = "failed"
                    except Exception as exc:
                        delivery.status = "failed"
                        delivery.error_message = str(exc)[:512]

                    await uow.webhooks.update_delivery(delivery)
                    retried += 1

        logger.info("retry_failed_webhooks: processed %d deliveries", retried)
        return {"retried": retried}

    return asyncio.run(_run())
