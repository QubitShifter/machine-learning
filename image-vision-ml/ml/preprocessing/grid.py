"""Canonical target grids for multi-temporal satellite datasets."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from rasterio.crs import CRS
from rasterio.transform import Affine
from rasterio.warp import transform_bounds

GRID_VERSION = "1"


def build_target_grid(
    bbox: tuple[float, float, float, float],
    *,
    source_crs: str = "EPSG:4326",
    target_crs: str = "EPSG:32635",
    resolution_m: float = 10.0,
) -> dict[str, Any]:
    """Build a snapped projected grid covering ``bbox``.

    Bounds are expanded outward to whole pixels so every scene in a
    time series shares one CRS, transform, width and height.
    """
    if bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
        raise ValueError("Bounding box must be west, south, east, north.")
    if resolution_m <= 0:
        raise ValueError("Resolution must be positive.")

    crs = CRS.from_string(target_crs)
    west, south, east, north = transform_bounds(
        source_crs,
        crs,
        *bbox,
        densify_pts=21,
    )
    left = math.floor(west / resolution_m) * resolution_m
    bottom = math.floor(south / resolution_m) * resolution_m
    right = math.ceil(east / resolution_m) * resolution_m
    top = math.ceil(north / resolution_m) * resolution_m
    width = int(round((right - left) / resolution_m))
    height = int(round((top - bottom) / resolution_m))
    transform = Affine(resolution_m, 0.0, left, 0.0, -resolution_m, top)
    return {
        "crs": crs,
        "transform": transform,
        "width": width,
        "height": height,
        "bounds": (left, bottom, right, top),
        "resolution": (resolution_m, resolution_m),
        "nodata": 0,
        "grid_version": GRID_VERSION,
    }


def serialize_grid(grid: dict[str, Any]) -> dict[str, Any]:
    crs = grid["crs"]
    transform = grid["transform"]
    return {
        "crs": crs.to_string() if hasattr(crs, "to_string") else str(crs),
        "transform": list(transform)[:6],
        "width": int(grid["width"]),
        "height": int(grid["height"]),
        "bounds": [float(value) for value in grid["bounds"]],
        "resolution": [float(value) for value in grid["resolution"]],
        "grid_version": grid.get("grid_version", GRID_VERSION),
    }


def deserialize_grid(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "crs": CRS.from_string(payload["crs"]),
        "transform": Affine(*payload["transform"]),
        "width": int(payload["width"]),
        "height": int(payload["height"]),
        "bounds": tuple(payload["bounds"]),
        "resolution": tuple(payload["resolution"]),
        "nodata": payload.get("nodata", 0),
        "grid_version": payload.get("grid_version", GRID_VERSION),
    }


def grids_equivalent(left: dict[str, Any], right: dict[str, Any]) -> bool:
    """Compare serialized or live grids for CRS, shape, and transform."""
    left_s = _as_serialized(left)
    right_s = _as_serialized(right)
    if (
        left_s["crs"] != right_s["crs"]
        or int(left_s["width"]) != int(right_s["width"])
        or int(left_s["height"]) != int(right_s["height"])
    ):
        return False
    left_t = [round(float(value), 6) for value in left_s["transform"][:6]]
    right_t = [round(float(value), 6) for value in right_s["transform"][:6]]
    return left_t == right_t


def validate_dataset_grid(
    dataset_id: str,
    *,
    processed_root: Path | None = None,
    expected: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Inspect processed scenes and report canonical-grid mismatches."""
    from ml.ingestion.manifest import read_manifest, scene_records, validate_safe_id
    from ml.preprocessing.raster import default_processed_root, read_json

    dataset_id = validate_safe_id(dataset_id, "dataset_id")
    root = (processed_root or default_processed_root()) / dataset_id
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        return {
            "dataset_id": dataset_id,
            "consistent": True,
            "expected": expected,
            "inspected_scenes": [],
            "mismatches": [],
            "notes": "No processed manifest is available yet.",
        }

    manifest = read_manifest(manifest_path)
    target = expected or manifest.get("target_grid")
    inspected: list[str] = []
    mismatches: list[dict[str, Any]] = []
    for record in scene_records(manifest):
        if record.get("status") != "processed":
            continue
        scene_id = record["scene_id"]
        meta_path = root / "scenes" / scene_id / "processing_metadata.json"
        if not meta_path.is_file():
            continue
        try:
            metadata = read_json(meta_path)
        except Exception:
            mismatches.append({
                "scene_id": scene_id,
                "reason": "unreadable_processing_metadata",
            })
            continue
        raster = metadata.get("raster") or {}
        inspected.append(scene_id)
        if not target:
            target = raster
            continue
        candidate = {
            "crs": raster.get("crs"),
            "transform": raster.get("transform"),
            "width": raster.get("width"),
            "height": raster.get("height"),
        }
        if not grids_equivalent(target, candidate):
            mismatches.append({
                "scene_id": scene_id,
                "reason": "grid_mismatch",
                "observed": candidate,
            })

    return {
        "dataset_id": dataset_id,
        "consistent": not mismatches,
        "expected": target,
        "inspected_scenes": inspected,
        "mismatches": mismatches,
        "grid_version": (target or {}).get("grid_version", GRID_VERSION),
    }


def _as_serialized(grid: dict[str, Any]) -> dict[str, Any]:
    if "transform" in grid and not isinstance(grid.get("crs"), str):
        return serialize_grid(grid)
    transform = grid.get("transform") or []
    return {
        "crs": str(grid.get("crs")),
        "transform": list(transform)[:6],
        "width": grid.get("width"),
        "height": grid.get("height"),
    }
