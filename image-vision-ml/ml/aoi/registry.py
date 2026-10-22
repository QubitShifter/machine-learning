"""Load the operational AOI registry without mutating satellite datasets."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ml.aoi.geometry import geometry_payload
from ml.preprocessing.raster import project_root


REGISTRY_VERSION = "3.5.0"
DEFAULT_REGISTRY = "configs/aoi_registry.yaml"


def default_registry_path() -> Path:
    return project_root() / DEFAULT_REGISTRY


def load_registry(path: Path | None = None) -> dict[str, Any]:
    registry_path = path or default_registry_path()
    if not registry_path.is_file():
        return {
            "version": REGISTRY_VERSION,
            "areas": [],
            "note": "AOI registry file is missing.",
        }
    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    areas = []
    for item in payload.get("areas") or []:
        bbox = [float(value) for value in item["bbox"]]
        geometry = geometry_payload(kind="bbox", bbox=bbox)
        areas.append({
            "aoi_id": item["aoi_id"],
            "name": item.get("name") or item["aoi_id"],
            "status": item.get("status") or "operational",
            "crs": item.get("crs") or "EPSG:4326",
            "bbox": bbox,
            "satellite_dataset_id": item.get("satellite_dataset_id"),
            "weather_dataset_id": item.get("weather_dataset_id"),
            "soil_dataset_id": item.get("soil_dataset_id"),
            "notes": item.get("notes"),
            "mutable": False,
            "downloads_allowed": False,
            "geometry": geometry,
        })
    return {
        "version": payload.get("version") or REGISTRY_VERSION,
        "areas": areas,
        "operational_count": sum(1 for item in areas if item["status"] == "operational"),
        "note": (
            "Operational areas are read-only in this phase. Draft geometries are "
            "proposals only and do not download satellite, weather, or soil data."
        ),
    }
