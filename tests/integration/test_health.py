import pytest


@pytest.mark.asyncio
class TestHealthEndpoint:

    async def test_health_check(self, client):
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
