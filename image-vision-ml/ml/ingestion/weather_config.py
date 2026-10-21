"""Load and validate ERA5-Land weather dataset configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ml.ingestion.config import SAFE_ID_CHARS
from ml.preprocessing.errors import WeatherConfigError
from ml.preprocessing.weather import (
    NATIVE_RESOLUTION_DEG,
    expand_bbox_to_retrieval_area,
    retrieval_area_has_grid_points,
)


CDS_VARIABLES = {
    "2m_temperature": "2m_temperature",
    "2m_dewpoint_temperature": "2m_dewpoint_temperature",
    "total_precipitation": "total_precipitation",
    "10m_u_component_of_wind": "10m_u_component_of_wind",
    "10m_v_component_of_wind": "10m_v_component_of_wind",
    "total_evaporation": "total_evaporation",
    "surface_solar_radiation_downwards": "surface_solar_radiation_downwards",
    "skin_temperature": "skin_temperature",
    "potential_evaporation": "potential_evaporation",
}

REQUIRED_VARIABLES = (
    "2m_temperature",
    "2m_dewpoint_temperature",
    "total_precipitation",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "total_evaporation",
)


def load_weather_config(path: Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.is_file():
        raise WeatherConfigError(f"Configuration file {config_path.name} is missing.")
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise WeatherConfigError("Configuration file is not valid YAML.") from exc
    if not isinstance(payload, dict):
        raise WeatherConfigError("Configuration must be a mapping.")
    return validate_weather_config(payload)


def validate_weather_config(payload: dict[str, Any]) -> dict[str, Any]:
    dataset_id = str(payload.get("dataset_id") or "").strip()
    if not dataset_id or any(char not in SAFE_ID_CHARS for char in dataset_id):
        raise WeatherConfigError(
            "dataset_id must be a safe identifier without path separators."
        )

    source = payload.get("source") or {}
    dataset = source.get("dataset") or "reanalysis-era5-land"
    area = payload.get("area") or {}
    bbox = area.get("bbox")
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        raise WeatherConfigError("area.bbox must contain four numbers.")
    bbox_tuple = tuple(float(value) for value in bbox)
    if bbox_tuple[0] >= bbox_tuple[2] or bbox_tuple[1] >= bbox_tuple[3]:
        raise WeatherConfigError("area.bbox must be west, south, east, north.")

    period = payload.get("period") or {}
    start = str(period.get("start") or "")
    end = str(period.get("end") or "")
    if not start or not end:
        raise WeatherConfigError("period.start and period.end are required.")

    variables = list(payload.get("variables") or REQUIRED_VARIABLES)
    unknown = [name for name in variables if name not in CDS_VARIABLES]
    if unknown:
        raise WeatherConfigError(f"Unknown weather variables: {unknown}")
    missing_required = [name for name in REQUIRED_VARIABLES if name not in variables]
    if missing_required:
        raise WeatherConfigError(
            f"Required ERA5-Land variables are missing: {missing_required}"
        )

    time_cfg = payload.get("time") or {}
    spatial = payload.get("spatial") or {}
    downloads = payload.get("downloads") or {}
    quality = payload.get("quality") or {}
    features = payload.get("features") or {}
    resolution = float(spatial.get("native_resolution_deg", NATIVE_RESOLUTION_DEG))
    retrieval_area = _retrieval_area(spatial, bbox_tuple, resolution)

    return {
        "dataset_id": dataset_id,
        "source": {
            "provider": source.get("provider", "cds"),
            "dataset": dataset,
            "data_format": source.get("data_format", "netcdf"),
            "download_format": source.get("download_format", "unarchived"),
        },
        "area": {
            "name": area.get("name", dataset_id),
            "bbox": bbox_tuple,
            "crs": area.get("crs", "EPSG:4326"),
        },
        "period": {"start": start[:10], "end": end[:10]},
        "time": {
            "timezone": time_cfg.get("timezone", "UTC"),
            "daily_aggregation": bool(time_cfg.get("daily_aggregation", True)),
        },
        "variables": variables,
        "spatial": {
            "method": spatial.get("method", "nearest_grid_cell"),
            "native_resolution_deg": resolution,
            "retrieval_area": retrieval_area,
        },
        "downloads": {
            "partition": downloads.get("partition", "monthly"),
            "retries": int(downloads.get("retries", 3)),
            "timeout_seconds": int(downloads.get("timeout_seconds", 120)),
            "include_next_day_boundary": bool(
                downloads.get("include_next_day_boundary", True)
            ),
        },
        "quality": {
            "require_complete_days": bool(quality.get("require_complete_days", True)),
            "reject_invalid_units": bool(quality.get("reject_invalid_units", True)),
            "preserve_missing_values": bool(
                quality.get("preserve_missing_values", True)
            ),
        },
        "features": {
            "dry_day_precipitation_mm": float(
                features.get("dry_day_precipitation_mm", 1.0)
            ),
            "windows_days": [
                int(value) for value in features.get("windows_days", [7, 14, 30])
            ],
        },
    }


def _retrieval_area(
    spatial: dict[str, Any],
    bbox: tuple[float, float, float, float],
    resolution: float,
) -> tuple[float, float, float, float]:
    raw = spatial.get("retrieval_area")
    if raw is None:
        area = expand_bbox_to_retrieval_area(bbox, resolution_deg=resolution)
    else:
        if not isinstance(raw, (list, tuple)) or len(raw) != 4:
            raise WeatherConfigError(
                "spatial.retrieval_area must be [north, west, south, east]."
            )
        north, west, south, east = (float(value) for value in raw)
        if north <= south or east <= west:
            raise WeatherConfigError(
                "spatial.retrieval_area must be north > south and east > west."
            )
        area = (north, west, south, east)
    if not retrieval_area_has_grid_points(area, resolution_deg=resolution):
        raise WeatherConfigError(
            "ERA5-Land retrieval_area must contain at least one native "
            f"{resolution}° grid point. The study AOI is often smaller than "
            "the ERA5-Land grid and cannot be sent to CDS as the crop."
        )
    return area
