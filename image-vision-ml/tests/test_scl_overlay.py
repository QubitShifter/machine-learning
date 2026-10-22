"""SCL overlay colorization and source inspection."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from rasterio.enums import Resampling
from rasterio.transform import Affine

from backend.tests.conftest import write_geotiff
from ml.visualization.map_overlay import (
    SCL_DISPLAY_COLORS,
    _source_display_arrays,
    colorize_scl,
    inspect_overlay_sources,
)


TRANSFORM = Affine(10.0, 0.0, 305520.0, 0.0, -10.0, 4661340.0)


def test_colorize_scl_is_categorical_and_keeps_nodata_transparent():
    classes = np.array([[0, 4], [5, 11], [9, 6]], dtype=np.uint8)
    rgb, alpha = colorize_scl(classes)
    assert list(rgb[0, 0]) == list(SCL_DISPLAY_COLORS[0])
    assert alpha[0, 0] == 0
    assert list(rgb[0, 1]) == list(SCL_DISPLAY_COLORS[4])
    assert list(rgb[1, 0]) == list(SCL_DISPLAY_COLORS[5])
    assert list(rgb[1, 1]) == list(SCL_DISPLAY_COLORS[11])
    assert list(rgb[2, 0]) == list(SCL_DISPLAY_COLORS[9])
    assert list(rgb[2, 1]) == list(SCL_DISPLAY_COLORS[6])
    assert int(alpha[0, 1]) == 255


def test_inspect_overlay_sources_adds_scl_without_dropping_rgb(tmp_path: Path):
    processed = tmp_path / "processed"
    raw = tmp_path / "raw"
    processed.mkdir()
    raw.mkdir()
    ndvi = np.full((4, 4), 0.4, dtype=np.float32)
    mask = np.ones((4, 4), dtype=np.uint8)
    write_geotiff(processed / "ndvi.tif", ndvi, transform=TRANSFORM, nodata=np.nan)
    write_geotiff(processed / "valid_mask.tif", mask, transform=TRANSFORM, nodata=0)
    for name in ("red_B04.tif", "green_B03.tif", "blue_B02.tif"):
        write_geotiff(raw / name, np.full((4, 4), 1000, dtype=np.uint16), transform=TRANSFORM, nodata=0)
    write_geotiff(raw / "scl.tif", np.full((4, 4), 4, dtype=np.uint8), transform=TRANSFORM, nodata=0)
    sources = inspect_overlay_sources(processed, raw)
    assert sources["supported_modes"] == ["ndvi", "rgb", "scl"]
    payload = _source_display_arrays(processed, "scl", raw)
    assert payload["resampling"] == Resampling.nearest
