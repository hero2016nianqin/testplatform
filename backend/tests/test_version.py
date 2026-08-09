import pytest
from httpx import AsyncClient


class TestVersion:
    async def test_create_version(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/versions", json={
            "version": "2.0.0",
            "project_name": "P201",
            "type": "standard",
            "description": "test version",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["status"] == "draft"

    async def test_list_versions(self, auth_client: AsyncClient):
        await auth_client.post("/api/v1/versions", json={
            "version": "2.0.1", "project_name": "P201",
        })
        resp = await auth_client.get("/api/v1/versions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert len(data["data"]["items"]) > 0

    async def test_get_version(self, auth_client: AsyncClient):
        ver = await auth_client.post("/api/v1/versions", json={
            "version": "2.0.2", "project_name": "P201",
        })
        ver_id = ver.json()["data"]["id"]
        resp = await auth_client.get(f"/api/v1/versions/{ver_id}")
        assert resp.status_code == 200

    async def test_update_version_draft(self, auth_client: AsyncClient):
        ver = await auth_client.post("/api/v1/versions", json={
            "version": "2.0.3", "project_name": "P201",
        })
        ver_id = ver.json()["data"]["id"]
        resp = await auth_client.put(f"/api/v1/versions/{ver_id}", json={
            "description": "updated description",
        })
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_add_sub_scenario(self, auth_client: AsyncClient):
        ver = await auth_client.post("/api/v1/versions", json={
            "version": "2.0.4", "project_name": "P201",
        })
        ver_id = ver.json()["data"]["id"]
        resp = await auth_client.post(f"/api/v1/versions/{ver_id}/sub-scenarios", json={
            "name": "Sub Scenario 1",
            "sort_order": 1,
        })
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_pending_approvals(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/versions/pending-approvals")
        assert resp.status_code == 200

    async def test_delist_and_restore(self, auth_client: AsyncClient):
        ver = await auth_client.post("/api/v1/versions", json={
            "version": "2.0.99", "project_name": "P201",
        })
        ver_id = ver.json()["data"]["id"]
        delist_resp = await auth_client.post(f"/api/v1/versions/{ver_id}/delist")
        assert delist_resp.status_code == 200
        restore_resp = await auth_client.post(f"/api/v1/versions/{ver_id}/restore")
        assert restore_resp.status_code == 200

    async def test_next_version(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/versions/next-version?project_name=P201")
        assert resp.status_code == 200
