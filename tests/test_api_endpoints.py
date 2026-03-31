from pathlib import Path

import pytest
pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from app.main import app
from app.models.db import JobDatabase
import app.services.job_service as job_service


class DummyRunner:
    def submit(self, job_id: str, config: dict):
        return None


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db = JobDatabase(tmp_path / "api_test.sqlite")
    monkeypatch.setattr(job_service, "get_db", lambda: db)
    monkeypatch.setattr(job_service, "get_runner", lambda: DummyRunner())
    return TestClient(app)


def _minimal_config():
    return {
        "date_range": {"start": "2024-01-01T00:00:00Z", "end": "2024-01-02T00:00:00Z"},
        "aoi": {"bbox": [-5, 40, 5, 45], "method": "bbox"},
        "data_access": {"mode": "earthaccess", "short_name": "SWOT_L2_HR_Raster_100m_D"},
        "process": {"variables": ["wse", "wse_qual", "wse_uncert", "water_frac", "n_wse_pix"]},
        "publish": {"enabled": False},
        "auth": {},
        "product": {"plugin": "swot_l2_hr_raster_100m_d", "short_name": "SWOT_L2_HR_Raster_100m_D"},
    }


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_products_and_downloaders(client: TestClient):
    p = client.get("/products")
    d = client.get("/downloaders")
    assert p.status_code == 200
    assert d.status_code == 200
    assert any(item["plugin"] == "swot_l2_hr_raster_100m_d" for item in p.json())
    assert any(item["name"] == "earthaccess" for item in d.json())


def test_aoi_validate(client: TestClient):
    response = client.post(
        "/aoi/validate",
        json={
            "method": "bbox",
            "bbox": [-10, 30, 20, 55],
            "chunking_mode": "auto",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["area_km2"] > 0
    assert body["size_class"] in {"small", "medium", "large"}


def test_create_job_and_fetch(client: TestClient):
    create = client.post("/jobs", json={"config": _minimal_config()})
    assert create.status_code == 200
    job_id = create.json()["id"]

    fetched = client.get(f"/jobs/{job_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == job_id

    logs = client.get(f"/jobs/{job_id}/logs")
    assert logs.status_code == 200


def test_cancel_job_endpoint(client: TestClient):
    create = client.post("/jobs", json={"config": _minimal_config()})
    assert create.status_code == 200
    job_id = create.json()["id"]

    cancel = client.post(f"/jobs/{job_id}/cancel")
    assert cancel.status_code == 200
    assert cancel.json()["id"] == job_id
    assert cancel.json()["status"] == "canceled"

    fetched = client.get(f"/jobs/{job_id}")
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "canceled"
