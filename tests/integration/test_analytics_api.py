import pytest


@pytest.mark.asyncio
class TestAnalyticsAPI:

    async def test_get_dashboard(self, client, sample_batch, sample_products):
        response = await client.get("/api/v1/analytics/dashboard")

        assert response.status_code == 200
        data = response.json()

        assert "summary" in data
        assert "today" in data
        assert "by_shift" in data
        assert "top_work_centers" in data
        assert "cached_at" in data

    async def test_get_dashboard_summary_fields(self, client, sample_batch):
        response = await client.get("/api/v1/analytics/dashboard")

        assert response.status_code == 200
        data = response.json()

        summary = data["summary"]
        assert "total_batches" in summary
        assert "active_batches" in summary
        assert "closed_batches" in summary
        assert "total_products" in summary
        assert "aggregated_products" in summary
        assert "aggregation_rate" in summary

    async def test_get_batch_statistics(self, client, sample_batch, sample_products):
        response = await client.get(f"/api/v1/analytics/batches/{sample_batch.id}/statistics")

        assert response.status_code == 200
        data = response.json()

        assert "batch_info" in data
        assert "production_stats" in data
        assert "timeline" in data
        assert "team_performance" in data

        assert data["batch_info"]["id"] == sample_batch.id
        assert data["production_stats"]["total_products"] == 10
        assert data["production_stats"]["aggregated"] == 5
        assert data["production_stats"]["remaining"] == 5

    async def test_get_batch_statistics_not_found(self, client):
        response = await client.get("/api/v1/analytics/batches/99999/statistics")

        assert response.status_code == 404

    async def test_compare_batches(self, client, sample_batch, sample_products):
        response = await client.post(
            "/api/v1/analytics/compare-batches",
            json={"batch_ids": [sample_batch.id]},
        )

        assert response.status_code == 200
        data = response.json()

        assert "comparison" in data
        assert "average" in data
        assert len(data["comparison"]) == 1

    async def test_compare_batches_empty(self, client):
        response = await client.post(
            "/api/v1/analytics/compare-batches",
            json={"batch_ids": []},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["comparison"] == []

    async def test_compare_batches_invalid_ids(self, client):
        response = await client.post(
            "/api/v1/analytics/compare-batches",
            json={"batch_ids": [99999, 99998]},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["comparison"] == []

    async def test_compare_batches_max_limit(self, client):
        batch_ids = list(range(1, 20))

        response = await client.post(
            "/api/v1/analytics/compare-batches",
            json={"batch_ids": batch_ids},
        )

        assert response.status_code == 200
