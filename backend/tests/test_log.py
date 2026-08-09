import pytest
from httpx import AsyncClient


class TestLog:
    async def test_list_logs(self, client: AsyncClient):
        resp = await client.get("/api/v1/logs")
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_log_stats(self, client: AsyncClient):
        resp = await client.get("/api/v1/logs/stats?days=7")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert "total" in data["data"]

    async def test_export_logs(self, client: AsyncClient):
        resp = await client.get("/api/v1/logs/export")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/csv; charset=utf-8"

    async def test_log_filters(self, client: AsyncClient):
        resp = await client.get("/api/v1/logs?level=ERROR")
        assert resp.status_code == 200

    async def test_log_pagination(self, client: AsyncClient):
        resp = await client.get("/api/v1/logs?page=1&page_size=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]["items"]) <= 5
