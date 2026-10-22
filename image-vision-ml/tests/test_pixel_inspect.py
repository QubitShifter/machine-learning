"""Georeferenced pixel inspection from processed rasters."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

from backend.tests.conftest import write_geotiff
from ml.visualization.map_overlay import sample_ndvi, sample_pixel


TRANSFORM = Affine(10.0, 0.0, 305520.0, 0.0, -10.0, 4661340.0)


def _seed(tmp_path: Path) -> tuple[Path, Path]:
    processed = tmp_path / "processed"
    raw = tmp_path / "raw"
    processed.mkdir(parents=True)
    raw.mkdir(parents=True)
    height, width = 8, 10
    ndvi = np.full((height, width), 0.5, dtype=np.float32)
    mask = np.ones((height, width), dtype=np.uint8)
    ndvi[0, 0] = np.nan
    mask[0, 0] = 0
    ndvi[1, 1] = 0.8
    write_geotiff(processed / "ndvi.tif", ndvi, transform=TRANSFORM, nodata=np.nan)
    write_geotiff(processed / "valid_mask.tif", mask, transform=TRANSFORM, nodata=0)
    (processed / "quality_report.json").write_text(
        '{"acquisition_date":"2025-07-18","scene_quality_status":"valid","calibration_status":"verified"}',
        encoding="utf-8",
    )
    (processed / "processing_metadata.json").write_text(
        '{"calibration":{"B02":{"scale":0.0001,"offset":0.0,"nodata":0.0},'
        '"B03":{"scale":0.0001,"offset":0.0,"nodata":0.0},'
        '"B04":{"scale":0.0001,"offset":0.0,"nodata":0.0},'
        '"B08":{"scale":0.0001,"offset":0.0,"nodata":0.0}}}',
        encoding="utf-8",
    )
    red = np.full((height, width), 4000, dtype=np.uint16)
    green = np.full((height, width), 2000, dtype=np.uint16)
    blue = np.full((height, width), 1000, dtype=np.uint16)
    nir = np.full((height, width), 8000, dtype=np.uint16)
    scl = np.full((height, width), 4, dtype=np.uint8)
    scl[0, 0] = 9
    red[0, 0] = 0
    for name, array in (
        ("red_B04.tif", red),
        ("green_B03.tif", green),
        ("blue_B02.tif", blue),
        ("nir_B08.tif", nir),
        ("scl.tif", scl),
    ):
        write_geotiff(raw / name, array, transform=TRANSFORM, nodata=0)
    return processed, raw


def _lonlat(processed: Path, row: int, col: int) -> tuple[float, float]:
    with rasterio.open(processed / "ndvi.tif") as dataset:
        x, y = dataset.xy(row, col)
        lon, lat = rasterio.warp.transform(dataset.crs, "EPSG:4326", [x], [y])
    return float(lon[0]), float(lat[0])


def test_pixel_inspect_reads_rasters_not_display_rgb(tmp_path: Path):
    processed, raw = _seed(tmp_path)
    lon, lat = _lonlat(processed, 4, 4)
    result = sample_pixel(processed, lon, lat, raw)
    assert result["inside_raster"] is True
    assert result["coverage_state"] == "inside"
    assert result["row"] == 4
    assert result["col"] == 4
    assert result["ndvi"] == 0.5
    assert result["red_b04"] == pytest.approx(0.4)
    assert result["green_b03"] == pytest.approx(0.2)
    assert result["blue_b02"] == pytest.approx(0.1)
    assert result["nir_b08"] == pytest.approx(0.8)
    assert result["scl_class"] == 4
    assert result["scl_class_name"] == "Vegetation"
    assert result["valid_mask"] is True
    assert result["exclusion_reason"] is None
    assert result["estimated_from_display_rgb"] is False
    assert result["scene_quality_status"] == "valid"
    assert result["calibration_status"] == "verified"


def test_pixel_inspect_outside_footprint_is_explicit(tmp_path: Path):
    processed, raw = _seed(tmp_path)
    with rasterio.open(processed / "ndvi.tif") as dataset:
        lon, lat = rasterio.warp.transform(
            dataset.crs,
            "EPSG:4326",
            [dataset.bounds.left - 500],
            [dataset.bounds.bottom - 500],
        )
    result = sample_pixel(processed, lon[0], lat[0], raw)
    assert result["coverage_state"] == "out_of_coverage"
    assert result["inside_raster"] is False
    assert result["ndvi"] is None
    assert result["red_b04"] is None
    assert result["scl_class"] is None
    assert result["row"] is None
    assert "outside" in (result["message"] or "").lower()


def test_masked_pixel_returns_null_ndvi_not_zero(tmp_path: Path):
    processed, raw = _seed(tmp_path)
    lon, lat = _lonlat(processed, 0, 0)
    result = sample_pixel(processed, lon, lat, raw)
    assert result["inside_raster"] is True
    assert result["valid"] is False
    assert result["ndvi"] is None
    assert result["ndvi"] != 0
    assert result["valid_mask"] is False
    assert result["scl_class"] == 9
    assert result["red_b04"] is None
    assert result["missing_reasons"]["red_b04"] == "nodata"
    ndvi = sample_ndvi(processed, lon, lat, raw)
    assert ndvi["ndvi"] is None
    assert ndvi["valid"] is False
