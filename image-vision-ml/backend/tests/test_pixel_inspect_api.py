"""Isolated API tests for georeferenced pixel inspection."""

from pathlib import Path

import numpy as np
import rasterio
from fastapi.testclient import TestClient
from rasterio.transform import Affine

from backend.app.main import app
from backend.app.services import satellite_map, satellite_service
from backend.tests.conftest import write_geotiff
from ml.ingestion.manifest import save_manifest, upsert_scene


client = TestClient(app)
TRANSFORM = Affine(10.0, 0.0, 305520.0, 0.0, -10.0, 4661340.0)


def _configure(monkeypatch, tmp_path: Path) -> tuple[Path, Path]:
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    cache = tmp_path / "cache"
    monkeypatch.setattr(satellite_service, "RAW_ROOT", raw)
    monkeypatch.setattr(satellite_service, "PROCESSED_ROOT", processed)
    monkeypatch.setattr(satellite_map, "CACHE_ROOT", cache)
    return raw, processed


def _seed(raw: Path, processed: Path) -> None:
    dataset_id = "plovdiv_2023_2025"
    scene_id = "S2A_35TLG_20250718_1_L2A"
    raw_dataset = raw / dataset_id
    raw_dataset.mkdir(parents=True)
    manifest = {
        "dataset_id": dataset_id,
        "bbox": [24.65, 42.05, 24.68, 42.08],
        "period": {"start": "2023-01-01", "end": "2025-12-31"},
        "source": {"collection": "sentinel-2-l2a"},
        "scenes": {},
    }
    upsert_scene(
        manifest,
        scene_id,
        status="processed",
        acquisition_date="2025-07-18",
        platform="sentinel-2a",
        cloud_cover=5.8,
    )
    save_manifest(raw_dataset / "manifest.json", manifest)
    scene_raw = raw_dataset / "scenes" / scene_id
    scene_proc = processed / dataset_id / "scenes" / scene_id
    scene_proc.mkdir(parents=True)
    height, width = 8, 10
    ndvi = np.full((height, width), 0.5, dtype=np.float32)
    mask = np.ones((height, width), dtype=np.uint8)
    write_geotiff(scene_proc / "ndvi.tif", ndvi, transform=TRANSFORM, nodata=np.nan)
    write_geotiff(scene_proc / "valid_mask.tif", mask, transform=TRANSFORM, nodata=0)
    (scene_proc / "quality_report.json").write_text(
        '{"acquisition_date":"2025-07-18","scene_quality_status":"valid","calibration_status":"verified"}',
        encoding="utf-8",
    )
    scene_raw.mkdir(parents=True)
    for name, value in (
        ("red_B04.tif", 4000),
        ("green_B03.tif", 2000),
        ("blue_B02.tif", 1000),
        ("nir_B08.tif", 8000),
    ):
        write_geotiff(scene_raw / name, np.full((height, width), value, dtype=np.uint16), transform=TRANSFORM, nodata=0)
    write_geotiff(scene_raw / "scl.tif", np.full((height, width), 5, dtype=np.uint8), transform=TRANSFORM, nodata=0)


def test_pixel_api_and_out_of_coverage(monkeypatch, tmp_path: Path):
    raw, processed = _configure(monkeypatch, tmp_path)
    _seed(raw, processed)
    ndvi = processed / "plovdiv_2023_2025" / "scenes" / "S2A_35TLG_20250718_1_L2A" / "ndvi.tif"
    with rasterio.open(ndvi) as dataset:
        lon, lat = rasterio.warp.transform(
            dataset.crs, "EPSG:4326", [dataset.xy(3, 3)[0]], [dataset.xy(3, 3)[1]]
        )
        outside = rasterio.warp.transform(
            dataset.crs, "EPSG:4326", [dataset.bounds.left - 800], [dataset.bounds.bottom - 800]
        )
    inside = client.get(
        "/api/v1/satellite/datasets/plovdiv_2023_2025/scenes/"
        "S2A_35TLG_20250718_1_L2A/map/pixel",
        params={"longitude": lon[0], "latitude": lat[0]},
    )
    assert inside.status_code == 200
    body = inside.json()
    assert body["inside_raster"] is True
    assert body["ndvi"] == 0.5
    assert body["scl_class"] == 5
    assert body["scl_class_name"] == "Bare soil"
    assert body["estimated_from_display_rgb"] is False
    missed = client.get(
        "/api/v1/satellite/datasets/plovdiv_2023_2025/scenes/"
        "S2A_35TLG_20250718_1_L2A/map/pixel",
        params={"longitude": outside[0][0], "latitude": outside[1][0]},
    )
    assert missed.status_code == 200
    out = missed.json()
    assert out["coverage_state"] == "out_of_coverage"
    assert out["ndvi"] is None
    assert out["red_b04"] is None
