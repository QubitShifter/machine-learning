"""AOI registry and draft geometry validation."""

from __future__ import annotations

import pytest

from ml.aoi.geometry import (
    AoiGeometryError,
    geometry_payload,
    validate_bbox,
    validate_polygon,
)
from ml.aoi.registry import load_registry


def test_operational_plovdiv_bbox_is_valid():
    bbox = validate_bbox([24.65, 42.05, 24.68, 42.08])
    payload = geometry_payload(kind="bbox", bbox=bbox)
    assert payload["valid"] is True
    assert payload["download_started"] is False
    assert payload["area_km2"] > 0.01
    registry = load_registry()
    ids = [item["aoi_id"] for item in registry["areas"]]
    assert "plovdiv_test" in ids
    plovdiv = next(item for item in registry["areas"] if item["aoi_id"] == "plovdiv_test")
    assert plovdiv["status"] == "operational"
    assert plovdiv["mutable"] is False
    assert plovdiv["downloads_allowed"] is False
    assert plovdiv["satellite_dataset_id"] == "plovdiv_2023_2025"


def test_invalid_geometries_are_rejected():
    with pytest.raises(AoiGeometryError, match="west"):
        validate_bbox([24.68, 42.05, 24.65, 42.08])
    with pytest.raises(AoiGeometryError, match="2.0 degrees"):
        validate_bbox([20.0, 40.0, 25.0, 45.0])
    with pytest.raises(AoiGeometryError, match="three"):
        validate_polygon([[24.65, 42.05], [24.66, 42.06]])
    bowtie = [
        [24.65, 42.05],
        [24.68, 42.08],
        [24.65, 42.08],
        [24.68, 42.05],
        [24.65, 42.05],
    ]
    with pytest.raises(AoiGeometryError, match="self-intersect"):
        validate_polygon(bowtie)
