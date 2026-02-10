import pytest
from unittest.mock import AsyncMock, patch

from src.domain.services.webhook_service import WebhookService
from src.core.exceptions import NotFoundException


@pytest.mark.asyncio
class TestWebhookService:

    async def test_create_subscription(self, test_uow):
        service = WebhookService(test_uow)

        data = {
            "url": "https://example.com/webhook",
            "events": ["batch.created"],
            "secret_key": "test-secret",
            "retry_count": 3,
            "timeout": 10,
        }

        result = await service.create_subscription(data)

        assert result.url == "https://example.com/webhook"
        assert result.events == ["batch.created"]
        assert result.is_active is True

    async def test_list_subscriptions(self, test_uow):
        service = WebhookService(test_uow)

        await service.create_subscription({
            "url": "https://example1.com/webhook",
            "events": ["batch.created"],
            "secret_key": "secret1",
        })
        await service.create_subscription({
            "url": "https://example2.com/webhook",
            "events": ["batch.closed"],
            "secret_key": "secret2",
        })

        result = await service.list_subscriptions()

        assert len(result) >= 2

    async def test_update_subscription(self, test_uow):
        service = WebhookService(test_uow)

        sub = await service.create_subscription({
            "url": "https://example.com/webhook",
            "events": ["batch.created"],
            "secret_key": "secret",
        })

        result = await service.update_subscription(sub.id, {"is_active": False})

        assert result.is_active is False

    async def test_update_subscription_not_found(self, test_uow):
        service = WebhookService(test_uow)

        with pytest.raises(NotFoundException):
            await service.update_subscription(99999, {"is_active": False})

    async def test_delete_subscription(self, test_uow):
        service = WebhookService(test_uow)

        sub = await service.create_subscription({
            "url": "https://example.com/webhook",
            "events": ["batch.created"],
            "secret_key": "secret",
        })

        await service.delete_subscription(sub.id)

        subscriptions = await service.list_subscriptions()
        sub_ids = [s.id for s in subscriptions]
        assert sub.id not in sub_ids

    async def test_delete_subscription_not_found(self, test_uow):
        service = WebhookService(test_uow)

        with pytest.raises(NotFoundException):
            await service.delete_subscription(99999)

    async def test_list_deliveries(self, test_uow):
        service = WebhookService(test_uow)

        sub = await service.create_subscription({
            "url": "https://example.com/webhook",
            "events": ["batch.created"],
            "secret_key": "secret",
        })

        result = await service.list_deliveries(sub.id)

        assert isinstance(result, list)


@pytest.mark.asyncio
class TestDispatchWebhookEvent:

    async def test_dispatch_webhook_event(self):
        with patch("src.tasks.webhooks.deliver_webhook_event") as mock_task:
            mock_task.delay = AsyncMock()

            from src.domain.services.webhook_service import dispatch_webhook_event

            dispatch_webhook_event("batch.created", {"batch_id": 1})

            mock_task.delay.assert_called_once_with(
                event_type="batch.created",
                data={"batch_id": 1},
            )
