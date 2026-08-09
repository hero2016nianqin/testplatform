import pytest
from httpx import AsyncClient


class TestAuth:
    async def test_login_success(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert "session_id" in resp.cookies

    async def test_login_invalid(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "wrong",
        })
        assert resp.status_code == 401

    async def test_me_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_me_authorized(self, client: AsyncClient):
        await client.post("/api/v1/auth/login", json={
            "username": "admin", "password": "admin123",
        })
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["username"] == "admin"

    async def test_users_list_requires_developer(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/users")
        assert resp.status_code == 403

    async def test_users_list_as_developer(self, client: AsyncClient):
        await client.post("/api/v1/auth/login", json={
            "username": "admin", "password": "admin123",
        })
        resp = await client.get("/api/v1/auth/users")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0

    async def test_logout(self, client: AsyncClient):
        await client.post("/api/v1/auth/login", json={
            "username": "admin", "password": "admin123",
        })
        resp = await client.post("/api/v1/auth/logout")
        assert resp.status_code == 200
        resp2 = await client.get("/api/v1/auth/me")
        assert resp2.status_code == 401
