"""Isolated AOI registry API tests. Drafts write only to a temp cache file."""

from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import aoi_service


client = TestClient(app)


def test_list_operational_areas_and_create_draft(monkeypatch, tmp_path: Path):
    drafts = tmp_path / "aoi_drafts.json"
    monkeypatch.setattr(aoi_service, "default_drafts_path", lambda: drafts)
    listing = client.get("/api/v1/aoi/areas")
    assert listing.status_code == 200
    body = listing.json()
    assert body["areas"][0]["aoi_id"] == "plovdiv_test"
    assert body["areas"][0]["status"] == "operational"
    created = client.post(
        "/api/v1/aoi/drafts",
        json={
            "name": "North field proposal",
            "geometry_type": "bbox",
            "bbox": [24.66, 42.06, 24.67, 42.07],
        },
    )
    assert created.status_code == 200
    draft = created.json()
    assert draft["status"] == "draft"
    assert draft["downloads_started"] is False
    assert draft["operational"] is False
    assert "Plovdiv" in (draft["note"] or "")
    rejected = client.post(
        "/api/v1/aoi/drafts",
        json={"geometry_type": "bbox", "bbox": [24.68, 42.05, 24.65, 42.08]},
    )
    assert rejected.status_code == 422
    assert drafts.is_file()
    assert drafts.resolve().is_relative_to(tmp_path.resolve())
    assert "data/raw/soil" not in str(drafts)
    assert "data/processed/soil" not in str(drafts)
