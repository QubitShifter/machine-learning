"""Leakage-safe join of satellite NDVI acquisitions with preceding weather."""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ml.analysis.weather_timeseries import _write_csv, _write_parquet
from ml.ingestion.manifest import write_json_atomic
from ml.integration.features import (
    DEFAULT_WINDOWS,
    DRY_DAY_THRESHOLD_MM,
    INTEGRATION_VERSION,
    LEAKAGE_POLICY,
    SAME_DAY_POLICY,
    WINDOW_RULE,
    feature_metadata,
)
from ml.preprocessing.raster import default_processed_root, project_root, read_json
from ml.preprocessing.weather import _maybe_float


DEFAULT_DRY_DAY_MM = DRY_DAY_THRESHOLD_MM
UNUSABLE_WEATHER_STATUSES = frozenset({"missing", "rejected", "requires_review"})
READY_STATUSES = frozenset({"ready", "suitable"})

INTEGRATION_COLUMNS = (
    "satellite_dataset_id",
    "weather_dataset_id",
    "scene_id",
    "acquisition_timestamp_utc",
    "acquisition_time_precision",
    "observation_date_utc",
    "aoi_id",
    "ndvi_mean",
    "ndvi_minimum",
    "ndvi_maximum",
    "ndvi_median",
    "valid_ndvi_pct",
    "cloud_shadow_fraction_pct",
    "source_crs",
    "pixel_resolution_m",
    "satellite_quality_status",
    "quality_status",
    "precip_prev_7d_mm",
    "precip_prev_14d_mm",
    "precip_prev_30d_mm",
    "temp_mean_prev_7d_c",
    "temp_mean_prev_30d_c",
    "dry_days_prev_30d",
    "rh_mean_prev_7d_pct",
    "wind_mean_prev_7d_ms",
    "evap_prev_7d_mm",
    "evap_prev_30d_mm",
    "window_7d_complete",
    "window_14d_complete",
    "window_30d_complete",
    "window_7d_expected_days",
    "window_14d_expected_days",
    "window_30d_expected_days",
    "window_7d_observed_days",
    "window_14d_observed_days",
    "window_30d_observed_days",
    "window_7d_available_days",
    "window_14d_available_days",
    "window_30d_available_days",
    "window_7d_missing_days",
    "window_14d_missing_days",
    "window_30d_missing_days",
    "window_7d_start_utc",
    "window_7d_end_utc",
    "window_14d_start_utc",
    "window_14d_end_utc",
    "window_30d_start_utc",
    "window_30d_end_utc",
    "source_grid_id",
    "weather_grid_longitude",
    "weather_grid_latitude",
    "weather_grid_distance_km",
    "weather_grid_method",
    "satellite_observation_valid",
    "weather_observation_valid",
    "weather_feature_window_complete",
    "integrated_observation_complete",
    "suitable_for_modeling",
    "quality_warnings",
    "integration_version",
    "satellite_processing_version",
)


def default_integration_root() -> Path:
    return project_root() / "data" / "processed" / "integration"


def prior_window_dates(observation_date: date, window: int) -> list[date]:
    """UTC dates D−window … D−1 inclusive. Acquisition date D is excluded."""
    return _previous_days(observation_date, window)


def integrate_satellite_weather(
    weather_rows: list[dict[str, Any]],
    satellite_observations: list[dict[str, Any]],
    *,
    weather_dataset_id: str,
    satellite_dataset_id: str,
    aoi_id: str,
    dry_day_mm: float = DEFAULT_DRY_DAY_MM,
    windows: tuple[int, ...] = DEFAULT_WINDOWS,
    spatial: dict[str, Any] | None = None,
    weather_integration_readiness: str | None = None,
    satellite_supervised_readiness: str | None = None,
    duplicate_scene_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Attach preceding-weather features to satellite observations.

    Features use only completed UTC days before the acquisition UTC date.
    Missing weather days stay missing; they are never filled with zero.
    One output row is produced per unique ``scene_id``. Observations without
    an acquisition timestamp remain in the table with weather features null.
    """
    weather_by_date = _index_weather(weather_rows)
    observations, dropped = _deduplicate_satellite(satellite_observations)
    if duplicate_scene_ids is not None:
        duplicate_scene_ids.extend(dropped)
    rows = []
    for item in observations:
        rows.append(
            _observation_row(
                item,
                weather_by_date=weather_by_date,
                weather_dataset_id=weather_dataset_id,
                satellite_dataset_id=satellite_dataset_id,
                aoi_id=aoi_id,
                dry_day_mm=dry_day_mm,
                windows=windows,
                spatial=spatial or {},
                weather_integration_readiness=weather_integration_readiness,
                satellite_supervised_readiness=satellite_supervised_readiness,
            )
        )
    return rows


def historical_weather_features(
    weather_by_date: dict[str, dict[str, Any]],
    observation_date: date,
    *,
    dry_day_mm: float = DEFAULT_DRY_DAY_MM,
    windows: tuple[int, ...] = DEFAULT_WINDOWS,
) -> dict[str, Any]:
    features: dict[str, Any] = {}
    for window in windows:
        days = _previous_days(observation_date, window)
        records = [weather_by_date.get(day.isoformat()) for day in days]
        precip_values = [_variable_value(item, "precipitation_total_mm") for item in records]
        temp_values = [_variable_value(item, "temperature_mean_c") for item in records]
        rh_values = [_variable_value(item, "relative_humidity_mean_pct") for item in records]
        wind_values = [_variable_value(item, "wind_speed_mean_ms") for item in records]
        evap_values = [_variable_value(item, "evaporation_total_mm") for item in records]
        observed = sum(1 for value in precip_values if value is not None)
        complete = observed == window
        features[f"window_{window}d_complete"] = complete
        features[f"window_{window}d_expected_days"] = window
        features[f"window_{window}d_observed_days"] = observed
        features[f"window_{window}d_available_days"] = observed
        features[f"window_{window}d_missing_days"] = window - observed
        features[f"window_{window}d_start_utc"] = days[0].isoformat() if days else None
        features[f"window_{window}d_end_utc"] = days[-1].isoformat() if days else None
        features[f"precip_prev_{window}d_mm"] = _sum_or_missing(precip_values)
        if window in {7, 30}:
            features[f"temp_mean_prev_{window}d_c"] = _mean_or_missing(temp_values)
            features[f"evap_prev_{window}d_mm"] = _sum_or_missing(evap_values)
        if window == 7:
            features["rh_mean_prev_7d_pct"] = _mean_or_missing(rh_values)
            features["wind_mean_prev_7d_ms"] = _mean_or_missing(wind_values)
        if window == 30:
            features["dry_days_prev_30d"] = _dry_days(precip_values, dry_day_mm)
    return features


def load_validated_satellite_observations(
    satellite_dataset_id: str,
    *,
    processed_root: Path | None = None,
    include_warning: bool = False,
) -> list[dict[str, Any]]:
    root = processed_root or default_processed_root()
    quality_path = root / satellite_dataset_id / "quality" / "dataset_quality.json"
    series_path = root / satellite_dataset_id / "timeseries" / "ndvi_timeseries.json"
    allowed = {"valid"}
    if include_warning:
        allowed.add("warning")
    quality_scenes: list[dict[str, Any]] = []
    grid: dict[str, Any] = {}
    if quality_path.is_file():
        payload = read_json(quality_path)
        summary = payload.get("dataset") or {}
        grid = (summary.get("spatial_grid_consistency") or {}).get("expected") or {}
        for scene in payload.get("scenes") or []:
            scene_id = scene.get("scene_id")
            if scene_id and scene.get("quality_status") in allowed:
                quality_scenes.append(scene)
    series_by_id: dict[str, dict[str, Any]] = {}
    if series_path.is_file():
        series = read_json(series_path)
        for item in series.get("observations") or []:
            scene_id = item.get("scene_id")
            if scene_id:
                series_by_id[scene_id] = item
    if quality_scenes:
        source = quality_scenes
    else:
        source = list(series_by_id.values())
    observations = []
    for scene in source:
        scene_id = scene.get("scene_id")
        if not scene_id:
            continue
        status = scene.get("quality_status")
        if quality_scenes and status not in allowed:
            continue
        series_item = series_by_id.get(scene_id) or {}
        processing = _read_processing_metadata(root, satellite_dataset_id, scene_id)
        timestamp_source = (
            processing.get("acquisition_date")
            or scene.get("acquisition_datetime")
            or series_item.get("datetime")
            or series_item.get("acquisition_date")
        )
        date_source = (
            timestamp_source
            or scene.get("acquisition_date")
            or series_item.get("date")
        )
        target = (processing.get("processing_settings") or {}).get("target_grid") or grid
        resolution = None
        raw_resolution = (target or {}).get("resolution")
        if isinstance(raw_resolution, (list, tuple)) and raw_resolution:
            resolution = float(raw_resolution[0])
        ndvi_mean = scene.get("ndvi_mean")
        if ndvi_mean is None:
            ndvi_mean = series_item.get("mean")
        ndvi_median = scene.get("ndvi_median")
        if ndvi_median is None:
            ndvi_median = series_item.get("median")
        observations.append({
            "scene_id": scene_id,
            "date": _utc_date_text(date_source),
            "acquisition_timestamp_utc": _timestamp_text(timestamp_source),
            "acquisition_time_precision": _time_precision(timestamp_source, date_source),
            "mean": ndvi_mean,
            "median": ndvi_median,
            "ndvi_minimum": scene.get("ndvi_minimum"),
            "ndvi_maximum": scene.get("ndvi_maximum"),
            "valid_ndvi_pct": scene.get("valid_ndvi_pct"),
            "cloud_shadow_fraction_pct": scene.get("cloud_shadow_fraction_pct"),
            "quality_status": status or "valid",
            "source_crs": (target or {}).get("crs"),
            "pixel_resolution_m": resolution,
            "satellite_processing_version": processing.get("processing_version"),
            "grid_aligned": scene.get("grid_aligned"),
        })
    return observations


def write_integration_outputs(
    rows: list[dict[str, Any]],
    directory: Path,
    *,
    metadata: dict[str, Any],
    quality: dict[str, Any] | None = None,
    catalog: dict[str, Any] | None = None,
) -> dict[str, str]:
    directory.mkdir(parents=True, exist_ok=True)
    _write_csv(directory / "satellite_weather.csv", rows, INTEGRATION_COLUMNS)
    outputs = {"csv": "satellite_weather.csv"}
    if _write_parquet(rows, directory / "satellite_weather.parquet"):
        outputs["parquet"] = "satellite_weather.parquet"
    write_json_atomic(directory / "integration_metadata.json", metadata)
    outputs["metadata"] = "integration_metadata.json"
    catalog_payload = catalog or feature_metadata()
    write_json_atomic(directory / "feature_catalog.json", catalog_payload)
    outputs["feature_catalog"] = "feature_catalog.json"
    if quality is not None:
        write_json_atomic(directory / "integration_quality.json", quality)
        outputs["quality"] = "integration_quality.json"
    return outputs


def source_fingerprint(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    stats = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "sha256": digest.hexdigest(),
        "size": stats.st_size,
        "mtime_ns": stats.st_mtime_ns,
    }


def empty_weather_features(windows: tuple[int, ...] = DEFAULT_WINDOWS) -> dict[str, Any]:
    features: dict[str, Any] = {}
    for window in windows:
        features[f"window_{window}d_complete"] = False
        features[f"window_{window}d_expected_days"] = window
        features[f"window_{window}d_observed_days"] = 0
        features[f"window_{window}d_available_days"] = 0
        features[f"window_{window}d_missing_days"] = window
        features[f"window_{window}d_start_utc"] = None
        features[f"window_{window}d_end_utc"] = None
        features[f"precip_prev_{window}d_mm"] = None
        if window in {7, 30}:
            features[f"temp_mean_prev_{window}d_c"] = None
            features[f"evap_prev_{window}d_mm"] = None
        if window == 7:
            features["rh_mean_prev_7d_pct"] = None
            features["wind_mean_prev_7d_ms"] = None
        if window == 30:
            features["dry_days_prev_30d"] = None
    return features


def _observation_row(
    item: dict[str, Any],
    *,
    weather_by_date: dict[str, dict[str, Any]],
    weather_dataset_id: str,
    satellite_dataset_id: str,
    aoi_id: str,
    dry_day_mm: float,
    windows: tuple[int, ...],
    spatial: dict[str, Any],
    weather_integration_readiness: str | None,
    satellite_supervised_readiness: str | None,
) -> dict[str, Any]:
    timestamp = _as_timestamp(
        item.get("acquisition_timestamp_utc") or item.get("date") or item.get("observation_date_utc")
    )
    obs_date = _as_date(
        timestamp
        or item.get("date")
        or item.get("observation_date_utc")
        or item.get("acquisition_timestamp_utc")
    )
    if obs_date is None:
        features = empty_weather_features(windows)
    else:
        features = historical_weather_features(
            weather_by_date,
            obs_date,
            dry_day_mm=dry_day_mm,
            windows=windows,
        )
    sample = None
    if obs_date is not None:
        sample = weather_by_date.get((obs_date - timedelta(days=1)).isoformat())
    if sample is None:
        sample = next(iter(weather_by_date.values()), None)
    ndvi_mean = _maybe_float(item.get("mean") if item.get("mean") is not None else item.get("ndvi_mean"))
    ndvi_min = _maybe_float(item.get("ndvi_minimum"))
    ndvi_max = _maybe_float(item.get("ndvi_maximum"))
    satellite_status = item.get("quality_status") or item.get("satellite_quality_status") or "valid"
    warnings = _row_warnings(
        item=item,
        obs_date=obs_date,
        timestamp=timestamp,
        ndvi_mean=ndvi_mean,
        ndvi_min=ndvi_min,
        ndvi_max=ndvi_max,
        features=features,
        windows=windows,
        spatial=spatial,
        sample=sample,
        satellite_status=satellite_status,
    )
    satellite_valid = _satellite_observation_valid(
        item=item,
        obs_date=obs_date,
        ndvi_mean=ndvi_mean,
        ndvi_min=ndvi_min,
        ndvi_max=ndvi_max,
        satellite_status=satellite_status,
    )
    weather_valid = _weather_observation_valid(spatial, sample)
    window_complete = all(bool(features.get(f"window_{window}d_complete")) for window in windows)
    integrated_complete = satellite_valid and weather_valid and window_complete
    suitable = (
        integrated_complete
        and _is_ready(weather_integration_readiness)
        and _is_ready(satellite_supervised_readiness)
    )
    precision = item.get("acquisition_time_precision") or _time_precision(
        timestamp or item.get("acquisition_timestamp_utc") or item.get("date"),
        obs_date,
    )
    return {
        "satellite_dataset_id": satellite_dataset_id,
        "weather_dataset_id": weather_dataset_id,
        "scene_id": item.get("scene_id"),
        "acquisition_timestamp_utc": _timestamp_text(timestamp) or item.get("acquisition_timestamp_utc"),
        "acquisition_time_precision": precision,
        "observation_date_utc": None if obs_date is None else obs_date.isoformat(),
        "aoi_id": aoi_id,
        "ndvi_mean": ndvi_mean,
        "ndvi_minimum": ndvi_min,
        "ndvi_maximum": ndvi_max,
        "ndvi_median": _maybe_float(item.get("median") if item.get("median") is not None else item.get("ndvi_median")),
        "valid_ndvi_pct": _maybe_float(item.get("valid_ndvi_pct")),
        "cloud_shadow_fraction_pct": _maybe_float(item.get("cloud_shadow_fraction_pct")),
        "source_crs": item.get("source_crs"),
        "pixel_resolution_m": _maybe_float(item.get("pixel_resolution_m")),
        "satellite_quality_status": satellite_status,
        "quality_status": satellite_status,
        "source_grid_id": _grid_id(spatial, sample),
        "weather_grid_longitude": _maybe_float(spatial.get("source_longitude")),
        "weather_grid_latitude": _maybe_float(spatial.get("source_latitude")),
        "weather_grid_distance_km": _maybe_float(spatial.get("distance_km")),
        "weather_grid_method": spatial.get("method"),
        "satellite_observation_valid": satellite_valid,
        "weather_observation_valid": weather_valid,
        "weather_feature_window_complete": window_complete,
        "integrated_observation_complete": integrated_complete,
        "suitable_for_modeling": suitable,
        "quality_warnings": ";".join(warnings),
        "integration_version": INTEGRATION_VERSION,
        "satellite_processing_version": item.get("satellite_processing_version"),
        **features,
    }


def _satellite_observation_valid(
    *,
    item: dict[str, Any],
    obs_date: date | None,
    ndvi_mean: float | None,
    ndvi_min: float | None,
    ndvi_max: float | None,
    satellite_status: str,
) -> bool:
    if not item.get("scene_id") or obs_date is None:
        return False
    if satellite_status not in {"valid", "warning"}:
        return False
    if ndvi_mean is None or ndvi_mean < -1.0 or ndvi_mean > 1.0:
        return False
    if ndvi_min is not None and ndvi_max is not None and ndvi_min > ndvi_max:
        return False
    valid_pct = _maybe_float(item.get("valid_ndvi_pct"))
    if valid_pct is not None and (valid_pct < 0 or valid_pct > 100):
        return False
    return True


def _weather_observation_valid(
    spatial: dict[str, Any],
    sample: dict[str, Any] | None,
) -> bool:
    grid_id = _grid_id(spatial, sample)
    method = spatial.get("method")
    latitude = _maybe_float(spatial.get("source_latitude"))
    longitude = _maybe_float(spatial.get("source_longitude"))
    if method and method != "nearest_grid_cell":
        return False
    if grid_id:
        return True
    return latitude is not None and longitude is not None


def _row_warnings(
    *,
    item: dict[str, Any],
    obs_date: date | None,
    timestamp: datetime | None,
    ndvi_mean: float | None,
    ndvi_min: float | None,
    ndvi_max: float | None,
    features: dict[str, Any],
    windows: tuple[int, ...],
    spatial: dict[str, Any],
    sample: dict[str, Any] | None,
    satellite_status: str,
) -> list[str]:
    warnings: list[str] = []
    if not item.get("scene_id"):
        warnings.append("missing_scene_id")
    if obs_date is None:
        warnings.append("missing_acquisition_timestamp")
    elif timestamp is None:
        warnings.append("acquisition_time_date_only")
    if satellite_status not in {"valid", "warning"}:
        warnings.append("incompatible_satellite_quality")
    if ndvi_mean is not None and (ndvi_mean < -1.0 or ndvi_mean > 1.0):
        warnings.append("invalid_ndvi_mean")
    if ndvi_min is not None and ndvi_max is not None and ndvi_min > ndvi_max:
        warnings.append("invalid_ndvi_range")
    if not _weather_observation_valid(spatial, sample):
        warnings.append("invalid_weather_grid_provenance")
    for window in windows:
        observed = int(features.get(f"window_{window}d_observed_days") or 0)
        expected = int(features.get(f"window_{window}d_expected_days") or window)
        if observed == 0:
            warnings.append(f"missing_weather_window_{window}d")
        elif observed < expected:
            warnings.append(f"incomplete_weather_window_{window}d")
    return warnings


def _index_weather(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed = {}
    for row in rows:
        key = str(row.get("date_utc") or "")[:10]
        if key:
            indexed[key] = row
    return indexed


def _deduplicate_satellite(
    observations: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Keep one row per scene_id. Same-day distinct scenes are retained."""
    by_id: dict[str, dict[str, Any]] = {}
    without_id: list[dict[str, Any]] = []
    dropped: list[str] = []
    for item in observations:
        scene_id = item.get("scene_id")
        if not scene_id:
            without_id.append(item)
            continue
        if scene_id in by_id:
            dropped.append(str(scene_id))
            continue
        by_id[scene_id] = item

    def sort_key(item: dict[str, Any]) -> tuple[str, str]:
        day = _utc_date_text(
            item.get("date")
            or item.get("observation_date_utc")
            or item.get("acquisition_timestamp_utc")
        ) or "9999-99-99"
        return day, str(item.get("scene_id") or "")

    ordered = sorted(list(by_id.values()) + without_id, key=sort_key)
    return ordered, dropped


def _previous_days(observation_date: date, window: int) -> list[date]:
    return [observation_date - timedelta(days=offset) for offset in range(window, 0, -1)]


def _sum_or_missing(values: list[float | None]) -> float | None:
    if any(value is None for value in values):
        return None
    return float(sum(values))


def _mean_or_missing(values: list[float | None]) -> float | None:
    if any(value is None for value in values):
        return None
    if not values:
        return None
    return float(sum(values) / len(values))


def _dry_days(values: list[float | None], threshold_mm: float) -> int | None:
    if any(value is None for value in values):
        return None
    return sum(1 for value in values if value < threshold_mm)


def _usable_weather_record(item: dict[str, Any] | None) -> bool:
    if not item:
        return False
    status = item.get("quality_status")
    if status in UNUSABLE_WEATHER_STATUSES:
        return False
    hours = item.get("hourly_records_available")
    if hours not in (None, ""):
        try:
            if int(hours) < 24:
                return False
        except (TypeError, ValueError):
            return False
    if item.get("boundary_00utc_available") is False:
        return False
    return True


def _variable_value(item: dict[str, Any] | None, field: str) -> float | None:
    if not _usable_weather_record(item):
        return None
    return _maybe_float(item.get(field))


def _as_date(value: Any) -> date | None:
    text = _utc_date_text(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _as_timestamp(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        stamp = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return stamp.astimezone(timezone.utc)
    if isinstance(value, date) and not isinstance(value, datetime):
        return None
    text = str(value).replace("Z", "+00:00")
    if "T" not in text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _utc_date_text(value: Any) -> str | None:
    if value is None or value == "":
        return None
    stamp = _as_timestamp(value)
    if stamp is not None:
        return stamp.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value)
    return text[:10] if len(text) >= 10 else text


def _timestamp_text(value: Any) -> str | None:
    stamp = _as_timestamp(value)
    if stamp is None:
        return None
    return stamp.isoformat().replace("+00:00", "Z")


def _time_precision(timestamp_source: Any, date_source: Any) -> str | None:
    if _as_timestamp(timestamp_source) is not None:
        return "utc_datetime"
    if _utc_date_text(date_source):
        return "utc_date"
    return None


def _grid_id(spatial: dict[str, Any], sample: dict[str, Any] | None) -> str | None:
    if sample and sample.get("source_grid_id"):
        return str(sample["source_grid_id"])
    latitude = spatial.get("source_latitude")
    longitude = spatial.get("source_longitude")
    if latitude is None or longitude is None:
        return None
    return f"{latitude},{longitude}"


def _is_ready(value: str | None) -> bool:
    return str(value or "").lower() in READY_STATUSES


def _read_processing_metadata(
    root: Path,
    dataset_id: str,
    scene_id: str,
) -> dict[str, Any]:
    path = root / dataset_id / "scenes" / scene_id / "processing_metadata.json"
    if not path.is_file():
        return {}
    try:
        return read_json(path)
    except Exception:
        return {}


# Re-exported for callers that previously imported these names from this module.
__all__ = [
    "DEFAULT_WINDOWS",
    "DEFAULT_DRY_DAY_MM",
    "INTEGRATION_COLUMNS",
    "INTEGRATION_VERSION",
    "LEAKAGE_POLICY",
    "SAME_DAY_POLICY",
    "WINDOW_RULE",
    "default_integration_root",
    "empty_weather_features",
    "historical_weather_features",
    "integrate_satellite_weather",
    "load_validated_satellite_observations",
    "prior_window_dates",
    "source_fingerprint",
    "write_integration_outputs",
]
