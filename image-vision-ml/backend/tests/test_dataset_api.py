from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import satellite_service
from ml.ingestion.manifest import save_manifest, upsert_scene
from ml.analysis.timeseries import write_timeseries_outputs, build_ndvi_timeseries


client = TestClient(app)


def _configure(monkeypatch, tmp_path: Path) -> tuple[Path, Path]:
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    configs = tmp_path / "configs"
    monkeypatch.setattr(satellite_service, "RAW_ROOT", raw)
    monkeypatch.setattr(satellite_service, "PROCESSED_ROOT", processed)
    monkeypatch.setattr(satellite_service, "CONFIG_ROOT", configs)
    return raw, processed


def _seed_dataset(raw: Path, processed: Path) -> None:
    dataset = raw / "plovdiv_2025"
    dataset.mkdir(parents=True)
    manifest = {
        "dataset_id": "plovdiv_2025",
        "bbox": [24.65, 42.05, 24.68, 42.08],
        "period": {"start": "2025-01-01", "end": "2025-12-31"},
        "source": {"collection": "sentinel-2-l2a"},
        "scenes": {},
    }
    upsert_scene(
        manifest,
        "S2B_35TLG_20250916_1_L2A",
        status="processed",
        acquisition_date="2025-09-16",
        cloud_cover=0.1,
        aoi_coverage=100.0,
    )
    save_manifest(dataset / "manifest.json", manifest)
    processed_manifest = dict(manifest)
    processed_manifest["processing_version"] = "1.1.0"
    processed_manifest["target_grid"] = {"crs": "EPSG:32635", "width": 10, "height": 10}
    save_manifest(processed / "plovdiv_2025" / "manifest.json", processed_manifest)
    payload = build_ndvi_timeseries([{
        "scene_id": "S2B_35TLG_20250916_1_L2A",
        "date": "2025-09-16",
        "mean": 0.58,
        "median": 0.57,
        "valid_percentage": 82.4,
        "valid_pixels": 80,
        "aoi_coverage": 100.0,
    }])
    payload["dataset_id"] = "plovdiv_2025"
    write_timeseries_outputs(payload, processed / "plovdiv_2025" / "timeseries")
    quality_dir = processed / "plovdiv_2025" / "quality"
    quality_dir.mkdir(parents=True, exist_ok=True)
    import json
    quality = {
        "dataset_id": "plovdiv_2025",
        "dataset": {
            "validated_scenes": 1,
            "rejected_scenes": 0,
            "requires_review_scenes": 0,
        },
        "training_readiness": {
            "overall": "limited",
            "supervised_soil_forecasting": "not_ready",
        },
        "scenes": [{
            "scene_id": "S2B_35TLG_20250916_1_L2A",
            "quality_status": "valid",
            "ndvi_mean": 0.58,
            "reasons": [],
        }],
    }
    (quality_dir / "dataset_quality.json").write_text(json.dumps(quality), encoding="utf-8")
    scene_quality = processed / "plovdiv_2025" / "scenes" / "S2B_35TLG_20250916_1_L2A"
    scene_quality.mkdir(parents=True, exist_ok=True)
    (scene_quality / "quality_report.json").write_text(
        json.dumps(quality["scenes"][0]),
        encoding="utf-8",
    )
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
        b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
        b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    (scene_quality / "rgb_preview.png").write_bytes(png)
    (scene_quality / "ndvi_preview.png").write_bytes(png)


def test_list_and_describe_datasets(monkeypatch, tmp_path: Path):
    raw, processed = _configure(monkeypatch, tmp_path)
    _seed_dataset(raw, processed)

    listing = client.get("/api/v1/satellite/datasets")
    assert listing.status_code == 200
    assert listing.json()["datasets"][0]["dataset_id"] == "plovdiv_2025"

    detail = client.get("/api/v1/satellite/datasets/plovdiv_2025")
    assert detail.status_code == 200
    assert detail.json()["collection"] == "sentinel-2-l2a"

    scenes = client.get("/api/v1/satellite/datasets/plovdiv_2025/scenes")
    assert scenes.status_code == 200
    assert scenes.json()["scenes"][0]["scene_id"] == "S2B_35TLG_20250916_1_L2A"


def test_timeseries_and_chart(monkeypatch, tmp_path: Path):
    raw, processed = _configure(monkeypatch, tmp_path)
    _seed_dataset(raw, processed)

    series = client.get("/api/v1/satellite/datasets/plovdiv_2025/timeseries/ndvi")
    assert series.status_code == 200
    assert series.json()["observations"][0]["mean"] == 0.58

    chart = client.get("/api/v1/satellite/datasets/plovdiv_2025/timeseries/ndvi/chart")
    assert chart.status_code == 200
    assert chart.headers["content-type"].startswith("image/png")


def test_unknown_and_invalid_dataset(monkeypatch, tmp_path: Path):
    _configure(monkeypatch, tmp_path)
    assert client.get("/api/v1/satellite/datasets/missing").status_code == 404
    response = client.get("/api/v1/satellite/datasets/../secret")
    assert response.status_code in {400, 404, 422}


def test_missing_timeseries(monkeypatch, tmp_path: Path):
    raw, processed = _configure(monkeypatch, tmp_path)
    dataset = raw / "plovdiv_2025"
    dataset.mkdir(parents=True)
    save_manifest(dataset / "manifest.json", {
        "dataset_id": "plovdiv_2025",
        "period": {"start": "2025-01-01", "end": "2025-12-31"},
        "source": {"collection": "sentinel-2-l2a"},
        "scenes": {},
    })
    assert client.get("/api/v1/satellite/datasets/plovdiv_2025/timeseries/ndvi").status_code == 404


def test_quality_and_extended_timeseries_endpoints(monkeypatch, tmp_path: Path):
    raw, processed = _configure(monkeypatch, tmp_path)
    _seed_dataset(raw, processed)

    quality = client.get("/api/v1/satellite/datasets/plovdiv_2025/quality")
    assert quality.status_code == 200
    assert quality.json()["dataset"]["validated_scenes"] == 1

    scene = client.get(
        "/api/v1/satellite/datasets/plovdiv_2025/scenes/S2B_35TLG_20250916_1_L2A/quality"
    )
    assert scene.status_code == 200
    assert scene.json()["quality_status"] == "valid"

    monthly = client.get("/api/v1/satellite/datasets/plovdiv_2025/timeseries/ndvi/monthly")
    assert monthly.status_code == 200
    assert monthly.json()["monthly"][0]["month"] == "2025-09"

    yearly = client.get("/api/v1/satellite/datasets/plovdiv_2025/timeseries/ndvi/yearly")
    assert yearly.status_code == 200
    assert yearly.json()["yearly"][0]["year"] == "2025"

    comparison = client.get(
        "/api/v1/satellite/datasets/plovdiv_2025/timeseries/ndvi/comparison"
    )
    assert comparison.status_code == 200
    assert "2025" in comparison.json()["comparison"]["years"]

    report = client.get("/api/v1/satellite/datasets/plovdiv_2025/quality/report")
    assert report.status_code == 200
    assert report.headers["content-type"].startswith("application/json")

    rgb = client.get(
        "/api/v1/satellite/datasets/plovdiv_2025/scenes/S2B_35TLG_20250916_1_L2A/rgb"
    )
    assert rgb.status_code == 200
    assert rgb.headers["content-type"].startswith("image/png")
    assert rgb.content[:8] == b"\x89PNG\r\n\x1a\n"

    preview = client.get(
        "/api/v1/satellite/datasets/plovdiv_2025/scenes/S2B_35TLG_20250916_1_L2A/ndvi/preview"
    )
    assert preview.status_code == 200
    assert preview.headers["content-type"].startswith("image/png")

    assert client.get(
        "/api/v1/satellite/datasets/plovdiv_2025/scenes/missing/rgb"
    ).status_code in {400, 404}

    assert client.get("/api/v1/satellite/datasets/missing/quality").status_code == 404
    assert client.get(
        "/api/v1/satellite/datasets/plovdiv_2025/scenes/missing/quality"
    ).status_code == 404


def test_existing_endpoints_and_swagger_include_datasets():
    assert client.get("/health").status_code == 200
    assert client.get("/api").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/satellite/images" in paths
    assert "/api/v1/satellite/datasets" in paths
    assert "/api/v1/satellite/datasets/{dataset_id}/timeseries/ndvi" in paths
    assert "/api/v1/satellite/datasets/{dataset_id}/quality" in paths
    assert "/api/v1/satellite/datasets/{dataset_id}/timeseries/ndvi/monthly" in paths
    assert "/api/v1/satellite/datasets/{dataset_id}/timeseries/ndvi/yearly" in paths
    assert "/api/v1/satellite/datasets/{dataset_id}/timeseries/ndvi/comparison" in paths
    assert "/api/v1/satellite/datasets/{dataset_id}/scenes/{scene_id}/map/metadata" in paths
    assert "/api/v1/satellite/datasets/{dataset_id}/scenes/{scene_id}/map/rgb" in paths
    assert "/api/v1/satellite/datasets/{dataset_id}/scenes/{scene_id}/map/ndvi" in paths
