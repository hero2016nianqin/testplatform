import pytest
from httpx import AsyncClient


class TestItems:
    async def test_list_items(self, client: AsyncClient):
        resp = await client.get("/api/v1/tests/items")
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_create_item(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/tests/items", json={
            "name": "Test Item 1",
            "expected_value": 100,
            "min_value": 90,
            "max_value": 110,
            "unit": "V",
            "category": "voltage",
        })
        assert resp.status_code == 200
        assert resp.json()["code"] == 0


class TestSequences:
    async def test_create_sequence(self, auth_client: AsyncClient):
        # First create a template
        tpl = await auth_client.post("/api/v1/tests/templates", json={
            "name": "Tpl 1",
            "service_address": "http://test:8080",
            "is_critical": False,
            "timeout_seconds": 30,
        })
        tpl_id = tpl.json()["data"]["id"]
        resp = await auth_client.post("/api/v1/tests/sequences", json={
            "name": "Seq 1",
            "version": "1.0",
            "steps": [{"template_id": tpl_id, "step_order": 1, "timeout_seconds": 30}],
        })
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_get_sequence_detail(self, auth_client: AsyncClient):
        tpl = await auth_client.post("/api/v1/tests/templates", json={
            "name": "Tpl 2", "service_address": "http://test:8080",
        })
        seq = await auth_client.post("/api/v1/tests/sequences", json={
            "name": "Seq 2", "steps": [{"template_id": tpl.json()["data"]["id"], "step_order": 1}],
        })
        seq_id = seq.json()["data"]["id"]
        resp = await auth_client.get(f"/api/v1/tests/sequences/{seq_id}")
        assert resp.status_code == 200


class TestRuns:
    async def test_create_run(self, auth_client: AsyncClient):
        fac = await auth_client.post("/api/v1/stations/factories", json={"name": "Run Factory"})
        line = await auth_client.post("/api/v1/stations/lines", json={
            "factory_id": fac.json()["data"]["id"], "name": "Run Line",
        })
        def_resp = await auth_client.get("/api/v1/stations/definitions")
        def_id = def_resp.json()["data"][0]["id"] if def_resp.json()["data"] else None
        st = await auth_client.post("/api/v1/stations", json={
            "line_id": line.json()["data"]["id"],
            "definition_id": def_id,
            "name": "Run Station",
        })
        st_id = st.json()["data"]["id"]
        resp = await auth_client.post("/api/v1/tests/runs", json={
            "serial_number": "SN001",
            "station_id": st_id,
            "slot_id": 1,
            "operator": "tester",
        })
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_list_runs(self, client: AsyncClient):
        resp = await client.get("/api/v1/tests/runs?page=1&page_size=10")
        assert resp.status_code == 200

    async def test_records(self, client: AsyncClient):
        for level in ("R1", "R2", "R3"):
            resp = await client.get(f"/api/v1/tests/records?level={level}")
            assert resp.status_code == 200
