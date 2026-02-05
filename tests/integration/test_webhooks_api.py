import pytest


@pytest.mark.asyncio
class TestWebhooksAPI:

    async def test_create_webhook(self, client):
        webhook_data = {
            "url": "https://example.com/webhook",
            "events": ["batch.created", "batch.closed"],
            "secret_key": "test-secret-key-123",
            "retry_count": 3,
            "timeout": 10,
        }

        response = await client.post("/api/v1/webhooks", json=webhook_data)

        assert response.status_code == 201
        data = response.json()

        assert data["url"] == "https://example.com/webhook"
        assert data["events"] == ["batch.created", "batch.closed"]
        assert data["is_active"] is True
        assert "id" in data

    async def test_create_webhook_invalid_url(self, client):
        webhook_data = {
            "url": "not-a-valid-url",
            "events": ["batch.created"],
            "secret_key": "secret",
        }

        response = await client.post("/api/v1/webhooks", json=webhook_data)

        assert response.status_code == 422

    async def test_list_webhooks(self, client):
        webhook_data = {
            "url": "https://example.com/hook1",
            "events": ["batch.created"],
            "secret_key": "secret1",
        }
        await client.post("/api/v1/webhooks", json=webhook_data)

        response = await client.get("/api/v1/webhooks")

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    async def test_update_webhook(self, client):
        webhook_data = {
            "url": "https://example.com/original",
            "events": ["batch.created"],
            "secret_key": "secret",
        }
        create_response = await client.post("/api/v1/webhooks", json=webhook_data)
        webhook_id = create_response.json()["id"]

        update_data = {
            "url": "https://example.com/updated",
            "is_active": False,
        }

        response = await client.patch(f"/api/v1/webhooks/{webhook_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()

        assert data["url"] == "https://example.com/updated"
        assert data["is_active"] is False

    async def test_delete_webhook(self, client):
        webhook_data = {
            "url": "https://example.com/to-delete",
            "events": ["batch.created"],
            "secret_key": "secret",
        }
        create_response = await client.post("/api/v1/webhooks", json=webhook_data)
        webhook_id = create_response.json()["id"]

        response = await client.delete(f"/api/v1/webhooks/{webhook_id}")

        assert response.status_code == 204

        get_response = await client.get("/api/v1/webhooks")
        webhooks = get_response.json()["items"]
        webhook_ids = [w["id"] for w in webhooks]
        assert webhook_id not in webhook_ids

    async def test_get_webhook_deliveries(self, client):
        webhook_data = {
            "url": "https://example.com/deliveries",
            "events": ["batch.created"],
            "secret_key": "secret",
        }
        create_response = await client.post("/api/v1/webhooks", json=webhook_data)
        webhook_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/webhooks/{webhook_id}/deliveries")

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "total" in data

    async def test_circuit_breaker_status(self, client):
        response = await client.get("/api/v1/webhooks/circuit-breaker/status")

        assert response.status_code == 200
        data = response.json()

        assert "name" in data
        assert "state" in data
        assert "failure_count" in data
        assert "success_count" in data
        assert data["state"] in ["closed", "open", "half_open"]
