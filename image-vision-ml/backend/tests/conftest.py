"""Shared test fixtures for satellite processing tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine


REFERENCE_CRS = "EPSG:32635"
REFERENCE_TRANSFORM = Affine(10.0, 0.0, 500000.0, 0.0, -10.0, 4700000.0)


def write_geotiff(
    path: Path,
    data: np.ndarray,
    *,
    crs: str = REFERENCE_CRS,
    transform: Affine = REFERENCE_TRANSFORM,
    nodata: float | None = 0,
    scale: float | None = None,
    offset: float | None = None,
) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    profile = {
        "driver": "GTiff",
        "height": data.shape[0],
        "width": data.shape[1],
        "count": 1,
        "dtype": str(data.dtype),
        "crs": crs,
        "transform": transform,
        "nodata": nodata,
    }
    with rasterio.open(path, "w", **profile) as destination:
        destination.write(data, 1)
        if scale is not None:
            destination.scales = (float(scale),)
        if offset is not None:
            destination.offsets = (float(offset),)
    return path


def write_scene_metadata(raw_dir: Path, **overrides) -> Path:
    metadata = {
        "scene_id": "TEST_SCENE_001",
        "acquisition_date": "2025-09-16T09:18:47.628000+00:00",
        "cloud_cover": 1.25,
        "collection": "sentinel-2-l2a",
        "stac_url": "https://earth-search.aws.element84.com/v1",
    }
    metadata.update(overrides)
    path = raw_dir / "metadata.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    import json

    path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return path


def build_fixture_dataset(raw_dir: Path) -> Path:
    """Create a small calibrated Sentinel-2-like window."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    write_scene_metadata(raw_dir)

    # DN 3000 -> 0.20 reflectance, DN 6000 -> 0.50 reflectance
    # with scale=0.0001 and offset=-0.1.
    red = np.full((4, 6), 3000, dtype=np.uint16)
    nir = np.full((4, 6), 6000, dtype=np.uint16)
    green = np.full((4, 6), 2500, dtype=np.uint16)
    blue = np.full((4, 6), 2000, dtype=np.uint16)
    scl = np.full((4, 6), 4, dtype=np.uint8)

    red[0, 0] = 0
    nir[0, 0] = 0
    scl[0, 1] = 8
    scl[3, 5] = 5

    for name, array in (
        ("red_B04.tif", red),
        ("nir_B08.tif", nir),
        ("green_B03.tif", green),
        ("blue_B02.tif", blue),
    ):
        write_geotiff(
            raw_dir / name,
            array,
            scale=0.0001,
            offset=-0.1,
        )

    write_geotiff(raw_dir / "scl.tif", scl)
    return raw_dir


@pytest.fixture
def fixture_dataset(tmp_path: Path) -> Path:
    return build_fixture_dataset(tmp_path / "raw" / "fixture_scene")
