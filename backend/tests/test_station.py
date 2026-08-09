import pytest
from httpx import AsyncClient


class TestFactory:
    async def test_list_factories(self, client: AsyncClient):
        resp = await client.get("/api/v1/stations/factories")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0

    async def test_create_factory_needs_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/stations/factories", json={"name": "Test Factory"})
        assert resp.status_code == 403

    async def test_create_factory(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/stations/factories", json={
            "name": "Test Factory",
            "code": "TF",
            "description": "Created by test",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0


class TestLine:
    async def test_create_line(self, auth_client: AsyncClient):
        fac_resp = await auth_client.post("/api/v1/stations/factories", json={"name": "Line Factory"})
        fac_id = fac_resp.json()["data"]["id"]
        resp = await auth_client.post("/api/v1/stations/lines", json={
            "factory_id": fac_id,
            "name": "Line A",
            "code": "LA",
        })
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_list_lines(self, client: AsyncClient):
        resp = await client.get("/api/v1/stations/lines")
        assert resp.status_code == 200


class TestStation:
    async def test_create_station(self, auth_client: AsyncClient):
        fac = await auth_client.post("/api/v1/stations/factories", json={"name": "Station Factory"})
        fac_id = fac.json()["data"]["id"]
        line = await auth_client.post("/api/v1/stations/lines", json={
            "factory_id": fac_id, "name": "Station Line",
        })
        line_id = line.json()["data"]["id"]
        def_resp = await auth_client.get("/api/v1/stations/definitions")
        def_id = def_resp.json()["data"][0]["id"] if def_resp.json()["data"] else None

        resp = await auth_client.post("/api/v1/stations", json={
            "line_id": line_id,
            "definition_id": def_id,
            "name": "Test Station",
        })
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_station_detail(self, auth_client: AsyncClient):
        fac = await auth_client.post("/api/v1/stations/factories", json={"name": "Detail Factory"})
        line = await auth_client.post("/api/v1/stations/lines", json={
            "factory_id": fac.json()["data"]["id"], "name": "Detail Line",
        })
        def_resp = await auth_client.get("/api/v1/stations/definitions")
        def_id = def_resp.json()["data"][0]["id"] if def_resp.json()["data"] else None
        st = await auth_client.post("/api/v1/stations", json={
            "line_id": line.json()["data"]["id"],
            "definition_id": def_id,
            "name": "Detail Station",
        })
        st_id = st.json()["data"]["id"]
        resp = await auth_client.get(f"/api/v1/stations/{st_id}")
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_equipment_config(self, auth_client: AsyncClient):
        fac = await auth_client.post("/api/v1/stations/factories", json={"name": "Eq Factory"})
        line = await auth_client.post("/api/v1/stations/lines", json={
            "factory_id": fac.json()["data"]["id"], "name": "Eq Line",
        })
        def_resp = await auth_client.get("/api/v1/stations/definitions")
        def_id = def_resp.json()["data"][0]["id"] if def_resp.json()["data"] else None
        st = await auth_client.post("/api/v1/stations", json={
            "line_id": line.json()["data"]["id"],
            "definition_id": def_id,
            "name": "Eq Station",
        })
        st_id = st.json()["data"]["id"]
        resp = await auth_client.put(f"/api/v1/stations/{st_id}/equipment", json={
            "equipment_ip": "10.0.0.1",
            "test_mode_normal": True,
        })
        assert resp.status_code == 200
