from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient
from rasterio.transform import Affine

from backend.app.main import app
from backend.app.services import satellite_service
from backend.tests.conftest import write_geotiff
from ml.ingestion.manifest import save_manifest, upsert_scene
from ml.preprocessing.raster import write_geotiff as write_processed_geotiff

client = TestClient(app)


def _configure(monkeypatch, tmp_path: Path) -> tuple[Path, Path]:
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    monkeypatch.setattr(satellite_service, "RAW_ROOT", raw)
    monkeypatch.setattr(satellite_service, "PROCESSED_ROOT", processed)
    return raw, processed


def test_scene_histograms_endpoint_uses_mask_and_warns_on_rejected(monkeypatch, tmp_path: Path):
    raw, processed = _configure(monkeypatch, tmp_path)
    dataset_id = "plovdiv_2025"
    scene_id = "S2B_35TLG_20250119_0_L2A"
    dataset = raw / dataset_id
    dataset.mkdir(parents=True)
    manifest = {
        "dataset_id": dataset_id,
        "bbox": [24.65, 42.05, 24.68, 42.08],
        "period": {"start": "2025-01-01", "end": "2025-12-31"},
        "source": {"collection": "sentinel-2-l2a"},
        "scenes": {},
    }
    upsert_scene(manifest, scene_id, status="processed", acquisition_date="2025-01-19")
    save_manifest(dataset / "manifest.json", manifest)

    scene = processed / dataset_id / "scenes" / scene_id
    scene.mkdir(parents=True)
    transform = Affine(10.0, 0.0, 0.0, 0.0, -10.0, 0.0)
    grid = {"crs": "EPSG:32635", "transform": transform, "width": 3, "height": 2}
    ndvi = np.array([[0.2, 0.4, np.nan], [-0.1, 0.0, 0.9]], dtype=np.float32)
    mask = np.array([[1, 1, 0], [1, 0, 1]], dtype=np.uint8)
    write_processed_geotiff(scene / "ndvi.tif", ndvi, grid, nodata=None)
    write_processed_geotiff(scene / "valid_mask.tif", mask, grid, nodata=0)
    (scene / "quality_report.json").write_text(
        '{"scene_quality_status":"rejected","scene_quality_reasons":["valid_ndvi_below_threshold"],'
        '"calibration_status":"verified","acquisition_date":"2025-01-19"}',
        encoding="utf-8",
    )
    (scene / "processing_metadata.json").write_text(
        '{"processing_version":"1.1.0","calibration":{"B04":{"scale":0.0001,"offset":0.0}}}',
        encoding="utf-8",
    )
    _ = write_geotiff

    response = client.get(
        f"/api/v1/satellite/datasets/{dataset_id}/scenes/{scene_id}/histograms?bins=20"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["scientific_use"] == "rejected_or_review"
    assert payload["calibration_status"] == "verified"
    assert payload["ndvi"]["masked_treated_as_zero"] is False
    assert payload["ndvi"]["pixel_conservation_ok"] is True
    assert payload["ndvi"]["masked_or_nodata_count"] == 2
    assert payload["ndvi"]["valid_pixel_count"] == 4
    assert "validated" in " ".join(payload["warnings"]).lower() or payload["warnings"]


def test_missing_histograms_return_404(monkeypatch, tmp_path: Path):
    raw, processed = _configure(monkeypatch, tmp_path)
    dataset = raw / "plovdiv_2025"
    dataset.mkdir(parents=True)
    save_manifest(dataset / "manifest.json", {
        "dataset_id": "plovdiv_2025",
        "scenes": {"SCENE_X": {"status": "discovered"}},
    })
    response = client.get("/api/v1/satellite/datasets/plovdiv_2025/scenes/SCENE_X/histograms")
    assert response.status_code == 404
    _ = processed
