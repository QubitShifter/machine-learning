"""Load and validate satellite time-series dataset configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ml.preprocessing.errors import DatasetConfigError


SAFE_ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")

DEFAULT_QUALITY = {
    "min_aoi_coverage_pct": 95.0,
    "min_valid_ndvi_pct": 70.0,
    "calibration_policy": "verified_only",
    "warning_valid_ndvi_pct": 85.0,
    "include_partial_coverage_in_full_series": False,
}

DEFAULT_DOWNLOADS = {
    "max_scenes_per_run": 5,
    "concurrency": 2,
    "retries": 3,
    "timeout_seconds": 60,
    "selection_strategy": "stratified_seasonal",
    "scenes_per_year": 3,
}


def load_dataset_config(path: Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.is_file():
        raise DatasetConfigError(f"Configuration file {config_path.name} is missing.")
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise DatasetConfigError("Configuration file is not valid YAML.") from exc
    if not isinstance(payload, dict):
        raise DatasetConfigError("Configuration must be a mapping.")
    return validate_dataset_config(payload)


def validate_dataset_config(payload: dict[str, Any]) -> dict[str, Any]:
    dataset_id = str(payload.get("dataset_id") or "").strip()
    if not dataset_id or any(char not in SAFE_ID_CHARS for char in dataset_id):
        raise DatasetConfigError(
            "dataset_id must be a safe identifier without path separators."
        )

    source = payload.get("source") or {}
    collection = source.get("collection")
    if not collection:
        raise DatasetConfigError("source.collection is required.")

    area = payload.get("area") or {}
    bbox = area.get("bbox")
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        raise DatasetConfigError("area.bbox must contain four numbers.")
    bbox_tuple = tuple(float(value) for value in bbox)
    if bbox_tuple[0] >= bbox_tuple[2] or bbox_tuple[1] >= bbox_tuple[3]:
        raise DatasetConfigError("area.bbox must be west, south, east, north.")

    period = payload.get("period") or {}
    start = str(period.get("start") or "")
    end = str(period.get("end") or "")
    if not start or not end:
        raise DatasetConfigError("period.start and period.end are required.")

    filters = payload.get("filters") or {}
    discovery = payload.get("discovery") or {}
    processing = payload.get("processing") or {}
    quality = payload.get("quality") or {}
    downloads = payload.get("downloads") or {}
    bands = processing.get("bands") or ["blue", "green", "red", "nir", "scl"]

    max_cloud = discovery.get(
        "max_scene_cloud_cover",
        filters.get("max_scene_cloud_cover", 20.0),
    )
    min_footprint = discovery.get(
        "min_footprint_overlap_pct",
        filters.get("min_footprint_overlap_pct", 0.0),
    )

    return {
        "dataset_id": dataset_id,
        "source": {
            "provider": source.get("provider", "earth_search"),
            "stac_url": source.get(
                "stac_url",
                "https://earth-search.aws.element84.com/v1",
            ),
            "collection": collection,
        },
        "area": {
            "name": area.get("name", dataset_id),
            "bbox": bbox_tuple,
            "crs": area.get("crs", "EPSG:4326"),
        },
        "period": {"start": start, "end": end},
        "filters": {
            "max_scene_cloud_cover": float(max_cloud),
            "min_footprint_overlap_pct": float(min_footprint),
        },
        "discovery": {
            "max_scene_cloud_cover": float(max_cloud),
            "min_footprint_overlap_pct": float(min_footprint),
        },
        "processing": {
            "bands": list(bands),
            "calculate_ndvi": bool(processing.get("calculate_ndvi", True)),
            "apply_scl_mask": bool(processing.get("apply_scl_mask", True)),
            "valid_scl_classes": [
                int(value) for value in processing.get("valid_scl_classes", [4, 5])
            ],
            "target_resolution_m": float(
                processing.get("target_resolution_m", 10)
            ),
            "target_crs": processing.get("target_crs", "EPSG:32635"),
        },
        "quality": {
            "min_aoi_coverage_pct": float(
                quality.get(
                    "min_aoi_coverage_pct",
                    DEFAULT_QUALITY["min_aoi_coverage_pct"],
                )
            ),
            "min_valid_ndvi_pct": float(
                quality.get(
                    "min_valid_ndvi_pct",
                    DEFAULT_QUALITY["min_valid_ndvi_pct"],
                )
            ),
            "warning_valid_ndvi_pct": float(
                quality.get(
                    "warning_valid_ndvi_pct",
                    DEFAULT_QUALITY["warning_valid_ndvi_pct"],
                )
            ),
            "calibration_policy": str(
                quality.get(
                    "calibration_policy",
                    DEFAULT_QUALITY["calibration_policy"],
                )
            ),
            "include_partial_coverage_in_full_series": bool(
                quality.get(
                    "include_partial_coverage_in_full_series",
                    DEFAULT_QUALITY["include_partial_coverage_in_full_series"],
                )
            ),
        },
        "downloads": {
            "max_scenes_per_run": int(
                downloads.get(
                    "max_scenes_per_run",
                    DEFAULT_DOWNLOADS["max_scenes_per_run"],
                )
            ),
            "concurrency": int(
                downloads.get("concurrency", DEFAULT_DOWNLOADS["concurrency"])
            ),
            "retries": int(downloads.get("retries", DEFAULT_DOWNLOADS["retries"])),
            "timeout_seconds": int(
                downloads.get(
                    "timeout_seconds",
                    DEFAULT_DOWNLOADS["timeout_seconds"],
                )
            ),
            "selection_strategy": str(
                downloads.get(
                    "selection_strategy",
                    DEFAULT_DOWNLOADS["selection_strategy"],
                )
            ),
            "scenes_per_year": int(
                downloads.get(
                    "scenes_per_year",
                    DEFAULT_DOWNLOADS["scenes_per_year"],
                )
            ),
        },
    }
