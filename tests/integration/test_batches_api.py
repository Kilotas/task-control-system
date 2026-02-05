import pytest
from datetime import date, datetime, timedelta


@pytest.mark.asyncio
class TestBatchesAPI:

    async def test_create_batch_success(self, client):
        batch_data = [
            {
                "НомерПартии": 5001,
                "ДатаПартии": str(date.today()),
                "ИдентификаторРЦ": "WC-TEST",
                "Смена": "1",
                "Бригада": "A",
                "ПредставлениеЗаданияНаСмену": "Test task",
                "Номенклатура": "Test nomenclature",
                "КодЕКН": "EKN001",
                "РабочийЦентр": "Test WC",
                "СтатусЗакрытия": False,
                "ДатаВремяНачалаСмены": datetime.now().isoformat(),
                "ДатаВремяОкончанияСмены": (datetime.now() + timedelta(hours=8)).isoformat(),
            }
        ]

        response = await client.post("/api/v1/batches", json=batch_data)

        assert response.status_code == 201
        data = response.json()
        assert len(data) == 1
        assert data[0]["НомерПартии"] == 5001

    async def test_create_batch_invalid_data(self, client):
        batch_data = [
            {
                "batch_number": "invalid",
            }
        ]

        response = await client.post("/api/v1/batches", json=batch_data)

        assert response.status_code == 422

    async def test_get_batch_success(self, client, sample_batch):
        response = await client.get(f"/api/v1/batches/{sample_batch.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_batch.id

    async def test_get_batch_not_found(self, client):
        response = await client.get("/api/v1/batches/99999")

        assert response.status_code == 404

    async def test_list_batches(self, client, sample_batch):
        response = await client.get("/api/v1/batches")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_list_batches_with_filters(self, client, sample_batch):
        response = await client.get(
            "/api/v1/batches",
            params={"shift": "1", "is_closed": False},
        )

        assert response.status_code == 200

    async def test_update_batch(self, client, sample_batch):
        update_data = {"СтатусЗакрытия": True}

        response = await client.patch(
            f"/api/v1/batches/{sample_batch.id}",
            json=update_data,
        )

        assert response.status_code == 200

    async def test_aggregate_batch(self, client, sample_batch, sample_products):
        response = await client.post(f"/api/v1/batches/{sample_batch.id}/aggregate")

        assert response.status_code == 200
        data = response.json()
        assert "updated_count" in data


@pytest.mark.asyncio
class TestBatchesRateLimiting:

    @pytest.mark.skip(reason="Rate limiter state persists between tests")
    async def test_create_batch_rate_limit(self, client):
        responses = []
        for i in range(35):
            batch_data = [
                {
                    "НомерПартии": 6000 + i,
                    "ДатаПартии": str(date.today()),
                    "ИдентификаторРЦ": "WC-RATE",
                    "Смена": "1",
                    "Бригада": "A",
                    "ПредставлениеЗаданияНаСмену": "Rate limit test",
                    "Номенклатура": "Test",
                    "КодЕКН": f"EKN{i:03d}",
                    "РабочийЦентр": "Rate WC",
                    "СтатусЗакрытия": False,
                    "ДатаВремяНачалаСмены": datetime.now().isoformat(),
                    "ДатаВремяОкончанияСмены": (datetime.now() + timedelta(hours=8)).isoformat(),
                }
            ]
            response = await client.post("/api/v1/batches", json=batch_data)
            responses.append(response.status_code)

        success_count = responses.count(201)
        rate_limited_count = responses.count(429)

        assert success_count <= 30
        assert rate_limited_count > 0
