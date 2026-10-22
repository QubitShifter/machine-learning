"""Load and validate ERA5-Land soil-moisture dataset configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ml.ingestion.config import SAFE_ID_CHARS
from ml.ingestion.weather_config import _retrieval_area
from ml.preprocessing.errors import SoilConfigError, WeatherConfigError
from ml.preprocessing.soil import SOIL_LAYERS
from ml.preprocessing.weather import NATIVE_RESOLUTION_DEG


CDS_SOIL_VARIABLES = {
    "volumetric_soil_water_layer_1": "volumetric_soil_water_layer_1",
    "volumetric_soil_water_layer_2": "volumetric_soil_water_layer_2",
    "volumetric_soil_water_layer_3": "volumetric_soil_water_layer_3",
    "volumetric_soil_water_layer_4": "volumetric_soil_water_layer_4",
    "soil_temperature_level_1": "soil_temperature_level_1",
    "soil_temperature_level_2": "soil_temperature_level_2",
    "soil_temperature_level_3": "soil_temperature_level_3",
    "soil_temperature_level_4": "soil_temperature_level_4",
}

REQUIRED_SOIL_WATER = (
    "volumetric_soil_water_layer_1",
    "volumetric_soil_water_layer_2",
    "volumetric_soil_water_layer_3",
    "volumetric_soil_water_layer_4",
)


def load_soil_config(path: Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.is_file():
        raise SoilConfigError(f"Configuration file {config_path.name} is missing.")
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise SoilConfigError("Configuration file is not valid YAML.") from exc
    if not isinstance(payload, dict):
        raise SoilConfigError("Configuration must be a mapping.")
    return validate_soil_config(payload)


def validate_soil_config(payload: dict[str, Any]) -> dict[str, Any]:
    dataset_id = str(payload.get("dataset_id") or "").strip()
    if not dataset_id or any(char not in SAFE_ID_CHARS for char in dataset_id):
        raise SoilConfigError(
            "dataset_id must be a safe identifier without path separators."
        )
    source = payload.get("source") or {}
    dataset = source.get("dataset") or "reanalysis-era5-land"
    area = payload.get("area") or {}
    bbox = area.get("bbox")
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        raise SoilConfigError("area.bbox must contain four numbers.")
    bbox_tuple = tuple(float(value) for value in bbox)
    if bbox_tuple[0] >= bbox_tuple[2] or bbox_tuple[1] >= bbox_tuple[3]:
        raise SoilConfigError("area.bbox must be west, south, east, north.")

    period = payload.get("period") or {}
    start = str(period.get("start") or "")
    end = str(period.get("end") or "")
    if not start or not end:
        raise SoilConfigError("period.start and period.end are required.")

    variables = list(payload.get("variables") or REQUIRED_SOIL_WATER)
    unknown = [name for name in variables if name not in CDS_SOIL_VARIABLES]
    if unknown:
        raise SoilConfigError(f"Unknown soil variables: {unknown}")
    missing = [name for name in REQUIRED_SOIL_WATER if name not in variables]
    if missing:
        raise SoilConfigError(f"Required soil-water layers are missing: {missing}")

    spatial = payload.get("spatial") or {}
    downloads = payload.get("downloads") or {}
    quality = payload.get("quality") or {}
    layers = payload.get("layers") or {}
    resolution = float(spatial.get("native_resolution_deg", NATIVE_RESOLUTION_DEG))
    try:
        retrieval_area = _retrieval_area(spatial, bbox_tuple, resolution)
    except WeatherConfigError as exc:
        raise SoilConfigError(str(exc)) from exc
    include_boundary = bool(downloads.get("include_next_day_boundary", False))
    if include_boundary:
        raise SoilConfigError(
            "Soil-water variables are instantaneous. "
            "downloads.include_next_day_boundary must be false."
        )

    return {
        "dataset_id": dataset_id,
        "source": {
            "provider": source.get("provider", "cds"),
            "dataset": dataset,
            "product_kind": source.get("product_kind", "reanalysis_soil_water"),
            "data_format": source.get("data_format", "netcdf"),
            "download_format": source.get("download_format", "unarchived"),
            "units": source.get("units", "m3 m-3"),
            "observation_kind": source.get(
                "observation_kind", "modeled_volumetric_soil_moisture"
            ),
        },
        "area": {
            "name": area.get("name", dataset_id),
            "bbox": bbox_tuple,
            "crs": area.get("crs", "EPSG:4326"),
        },
        "period": {"start": start[:10], "end": end[:10]},
        "time": {
            "timezone": (payload.get("time") or {}).get("timezone", "UTC"),
            "daily_aggregation": True,
            "aggregation": "hourly_instantaneous_mean",
        },
        "variables": variables,
        "layers": {key: dict(SOIL_LAYERS[key], **(layers.get(key) or {})) for key in SOIL_LAYERS},
        "spatial": {
            "method": spatial.get("method", "nearest_grid_cell"),
            "native_resolution_deg": resolution,
            "retrieval_area": retrieval_area,
            "reference_weather_dataset_id": spatial.get(
                "reference_weather_dataset_id", "plovdiv_weather_2023_2025"
            ),
        },
        "downloads": {
            "partition": downloads.get("partition", "monthly"),
            "retries": int(downloads.get("retries", 3)),
            "timeout_seconds": int(downloads.get("timeout_seconds", 120)),
            "include_next_day_boundary": False,
        },
        "quality": {
            "require_complete_days": bool(quality.get("require_complete_days", True)),
            "preserve_missing_values": bool(quality.get("preserve_missing_values", True)),
            "theta_min": float(quality.get("theta_min", 0.0)),
            "theta_max": float(quality.get("theta_max", 1.0)),
            "field_capacity": quality.get("field_capacity"),
            "wilting_point": quality.get("wilting_point"),
        },
    }
