"""Beginning-of-day historical features for one research cutoff day."""

from __future__ import annotations

from datetime import date
from typing import Any

from ml.agricultural_ml.time_semantics import (
    DATA_AVAILABILITY_MODE,
    calendar_features,
    feature_cutoff_utc,
    iso_z,
    issue_datetime_utc,
    last_observation_date,
    parse_utc_date,
    window_bounds,
)
from ml.integration.satellite_weather import prior_window_dates
from ml.preprocessing.soil import SOIL_LAYERS
from ml.preprocessing.weather import _maybe_float
from ml.preprocessing.wetness import (
    DEFAULT_API_FACTORS,
    DEFAULT_WARMUP_DAYS,
    antecedent_precipitation_index,
    consecutive_dry_days,
    days_since_rain,
)


SOIL_SERIES = (
    ("swvl1", "swvl1_mean"),
    ("swvl2", "swvl2_mean"),
    ("swvl3", "swvl3_mean"),
    ("swvl4", "swvl4_mean"),
    ("theta_root_zone_0_100", "theta_root_zone_0_100"),
)
STATIC_PROPERTIES = (
    "soil_texture",
    "bulk_density",
    "soil_organic_carbon",
    "elevation",
    "slope",
    "land_cover",
    "crop_identity",
)


def index_by_date(rows: list[dict[str, Any]]) -> dict[date, dict[str, Any]]:
    indexed: dict[date, dict[str, Any]] = {}
    for row in rows:
        parsed = parse_utc_date(row.get("date_utc"))
        if parsed is not None:
            indexed[parsed] = row
    return indexed


def weather_day_complete(row: dict[str, Any] | None) -> bool:
    if not row:
        return False
    hourly = row.get("hourly_records_available")
    return (
        str(row.get("quality_status") or "") == "valid"
        and int(hourly or 0) == 24
        and bool(row.get("boundary_00utc_available"))
        and _maybe_float(row.get("precipitation_total_mm")) is not None
    )


def soil_day_complete(row: dict[str, Any] | None) -> bool:
    if not row:
        return False
    return bool(row.get("complete_day")) and str(row.get("quality_status") or "") == "valid"


def window_values(
    by_date: dict[date, dict[str, Any]],
    issue_date: date,
    window: int,
    field: str,
    *,
    complete: Any,
) -> list[float | None]:
    values: list[float | None] = []
    for day in prior_window_dates(issue_date, window):
        row = by_date.get(day)
        if not complete(row):
            values.append(None)
            continue
        values.append(_maybe_float(row.get(field)))
    return values


def require_complete_mean(values: list[float | None]) -> float | None:
    if not values or any(item is None for item in values):
        return None
    return float(sum(values)) / float(len(values))


def require_complete_sum(values: list[float | None]) -> float | None:
    if not values or any(item is None for item in values):
        return None
    return float(sum(values))


def require_complete_minmax(values: list[float | None], fn: Any) -> float | None:
    if not values or any(item is None for item in values):
        return None
    return float(fn(values))


def slope(values: list[float | None]) -> float | None:
    """(last − first) / (N−1) over a complete N-day window D−N … D−1."""
    if len(values) < 2 or any(item is None for item in values):
        return None
    return (float(values[-1]) - float(values[0])) / float(len(values) - 1)


def api_key(k: float) -> str:
    return f"api_k{int(round(k * 100)):03d}_mm"


def build_api_lookup(
    weather_by_date: dict[date, dict[str, Any]],
    dates: list[date],
    *,
    k_factors: tuple[float, ...] = DEFAULT_API_FACTORS,
    warmup_days: int = DEFAULT_WARMUP_DAYS,
) -> dict[float, dict[date, float | None]]:
    precip = []
    for day in dates:
        row = weather_by_date.get(day)
        precip.append(
            _maybe_float(row.get("precipitation_total_mm")) if weather_day_complete(row) else None
        )
    series = {k: antecedent_precipitation_index(precip, k=k) for k in k_factors}
    lookup: dict[float, dict[date, float | None]] = {k: {} for k in k_factors}
    for index, day in enumerate(dates):
        for k in k_factors:
            lookup[k][day] = series[k][index]
    lookup["_warmup_days"] = warmup_days  # type: ignore[assignment]
    lookup["_valid_count"] = {}  # type: ignore[assignment]
    valid = 0
    counts: dict[date, int] = {}
    for day, value in zip(dates, precip):
        if value is not None:
            valid += 1
        counts[day] = valid
    lookup["_valid_count"] = counts  # type: ignore[assignment]
    return lookup


def soil_history_features(
    soil_by_date: dict[date, dict[str, Any]],
    issue_date: date,
    windows: tuple[int, ...],
) -> dict[str, Any]:
    features: dict[str, Any] = {}
    last = last_observation_date(issue_date)
    for name, field in SOIL_SERIES:
        prev1 = window_values(soil_by_date, issue_date, 1, field, complete=soil_day_complete)
        features[f"{name}_prev1"] = prev1[0] if prev1 else None
        prev2 = window_values(soil_by_date, issue_date, 2, field, complete=soil_day_complete)
        features[f"{name}_delta_prev1"] = (
            None if any(item is None for item in prev2) or len(prev2) != 2
            else float(prev2[-1]) - float(prev2[0])
        )
        for window in windows:
            values = window_values(
                soil_by_date, issue_date, window, field, complete=soil_day_complete,
            )
            features[f"{name}_prev{window}d_mean"] = require_complete_mean(values)
            if window in {3, 7, 14}:
                features[f"{name}_prev{window}d_slope"] = slope(values)
        layer = SOIL_LAYERS.get(name)
        if layer:
            features[f"{name}_depth_top_m"] = layer["depth_top_m"]
            features[f"{name}_depth_bottom_m"] = layer["depth_bottom_m"]
    features["last_soil_observation_date_utc"] = last.isoformat()
    return features


def weather_history_features(
    weather_by_date: dict[date, dict[str, Any]],
    issue_date: date,
    *,
    windows: tuple[int, ...],
    dry_day_mm: float,
    api_lookup: dict[float, dict[date, float | None]],
    k_factors: tuple[float, ...],
    warmup_days: int,
    ordered_dates: list[date],
) -> dict[str, Any]:
    last = last_observation_date(issue_date)
    features: dict[str, Any] = {}
    precip_by_day = []
    for day in ordered_dates:
        row = weather_by_date.get(day)
        precip_by_day.append(
            _maybe_float(row.get("precipitation_total_mm")) if weather_day_complete(row) else None
        )
    dry_runs = consecutive_dry_days(precip_by_day, dry_day_mm=dry_day_mm)
    since = days_since_rain(precip_by_day, dry_day_mm=dry_day_mm)
    by_index = {day: index for index, day in enumerate(ordered_dates)}
    last_index = by_index.get(last)
    features["consecutive_dry_days"] = None if last_index is None else dry_runs[last_index]
    features["days_since_rain"] = None if last_index is None else since[last_index]
    valid_count = api_lookup.get("_valid_count") or {}
    for k in k_factors:
        key = api_key(k)
        features[key] = (api_lookup.get(k) or {}).get(last)
        features[f"{key}_source_date_utc"] = last.isoformat()
        count = valid_count.get(last) if isinstance(valid_count, dict) else None
        features[f"{key}_warmup"] = bool(count is not None and int(count) <= warmup_days)
    for window in windows:
        start, end = window_bounds(issue_date, window)
        precip = window_values(
            weather_by_date, issue_date, window, "precipitation_total_mm",
            complete=weather_day_complete,
        )
        temp = window_values(
            weather_by_date, issue_date, window, "temperature_mean_c",
            complete=weather_day_complete,
        )
        tmin = window_values(
            weather_by_date, issue_date, window, "temperature_min_c",
            complete=weather_day_complete,
        )
        tmax = window_values(
            weather_by_date, issue_date, window, "temperature_max_c",
            complete=weather_day_complete,
        )
        rh = window_values(
            weather_by_date, issue_date, window, "relative_humidity_mean_pct",
            complete=weather_day_complete,
        )
        wind = window_values(
            weather_by_date, issue_date, window, "wind_speed_mean_ms",
            complete=weather_day_complete,
        )
        evap = window_values(
            weather_by_date, issue_date, window, "evaporation_total_mm",
            complete=weather_day_complete,
        )
        features[f"precip_prev_{window}d_mm"] = require_complete_sum(precip)
        features[f"window_{window}d_start_utc"] = start.isoformat()
        features[f"window_{window}d_end_utc"] = end.isoformat()
        features[f"window_{window}d_complete"] = all(item is not None for item in precip)
        if window in {1, 3, 7, 30}:
            features[f"temp_mean_prev_{window}d_c"] = require_complete_mean(temp)
        if window == 1:
            features["temp_prev1_c"] = require_complete_mean(temp)
            features["rh_prev1_pct"] = require_complete_mean(rh)
            features["evap_prev1_mm"] = require_complete_sum(evap)
        if window == 7:
            features["temp_min_prev_7d_c"] = require_complete_minmax(tmin, min)
            features["temp_max_prev_7d_c"] = require_complete_minmax(tmax, max)
            features["rh_mean_prev_7d_pct"] = require_complete_mean(rh)
            features["wind_mean_prev_7d_ms"] = require_complete_mean(wind)
            features["evap_prev_7d_mm"] = require_complete_sum(evap)
            rain = features["precip_prev_7d_mm"]
            ev = features["evap_prev_7d_mm"]
            features["precip_minus_evap_prev_7d_mm"] = (
                None if rain is None or ev is None else float(rain) - float(ev)
            )
        if window == 30:
            features["evap_prev_30d_mm"] = require_complete_sum(evap)
            rain = features["precip_prev_30d_mm"]
            ev = features["evap_prev_30d_mm"]
            features["precip_minus_evap_prev_30d_mm"] = (
                None if rain is None or ev is None else float(rain) - float(ev)
            )
            features["dry_days_prev_30d"] = (
                None if any(item is None for item in precip)
                else sum(1 for item in precip if item < dry_day_mm)
            )
    features["last_weather_observation_date_utc"] = last.isoformat()
    features["era5_evaporation_is_crop_et"] = False
    return features


def static_property_features() -> dict[str, Any]:
    payload = {"static_properties_status": "unavailable"}
    for name in STATIC_PROPERTIES:
        payload[f"static_{name}"] = None
        payload[f"static_{name}_status"] = "unavailable"
    return payload


def build_daily_features(
    *,
    issue_dates: list[date],
    weather_rows: list[dict[str, Any]],
    soil_rows: list[dict[str, Any]],
    config: dict[str, Any],
    spatial: dict[str, Any] | None = None,
    satellite_by_issue: dict[date, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    windows = tuple(int(item) for item in config["feature_windows_days"])
    weather_by_date = index_by_date(weather_rows)
    soil_by_date = index_by_date(soil_rows)
    weather_dates = sorted(weather_by_date)
    api_cfg = config.get("api") or {}
    k_factors = tuple(float(item) for item in (api_cfg.get("k_factors") or DEFAULT_API_FACTORS))
    warmup_days = int(api_cfg.get("warmup_days") or DEFAULT_WARMUP_DAYS)
    dry_day_mm = float(config.get("dry_day_precipitation_mm") or 1.0)
    api_lookup = build_api_lookup(
        weather_by_date, weather_dates, k_factors=k_factors, warmup_days=warmup_days,
    )
    min_history = int(config.get("minimum_history_days") or 30)
    sources = config.get("sources") or {}
    issue_cfg = config.get("issue_time") or {}
    rows = []
    for issue_date in issue_dates:
        last = last_observation_date(issue_date)
        issue_dt = issue_datetime_utc(issue_date)
        history_ok = all(
            soil_day_complete(soil_by_date.get(day)) and weather_day_complete(weather_by_date.get(day))
            for day in prior_window_dates(issue_date, min_history)
        )
        row = {
            "dataset_id": config["dataset_id"],
            "aoi_id": config.get("aoi_id"),
            "weather_dataset_id": sources.get("weather_dataset_id"),
            "soil_dataset_id": sources.get("soil_dataset_id"),
            "satellite_dataset_id": sources.get("satellite_dataset_id"),
            "issue_row_key": f"{config['dataset_id']}:{issue_date.isoformat()}",
            "issue_date_utc": issue_date.isoformat(),
            "issue_time_utc": iso_z(issue_dt),
            "last_observation_date_utc": last.isoformat(),
            "feature_cutoff_time_utc": iso_z(feature_cutoff_utc(issue_date)),
            "data_availability_mode": issue_cfg.get("research_mode") or DATA_AVAILABILITY_MODE,
            "operational_availability_verified": False,
            "publication_timestamps_known": False,
            "feature_version": config.get("dataset_version"),
            "pipeline_version": config.get("pipeline_version"),
            "prediction_target_kind": "daily_mean_state",
            "history_window_complete": history_ok,
            "source_grid_id": (spatial or {}).get("source_grid_id"),
            "source_latitude": (spatial or {}).get("source_latitude"),
            "source_longitude": (spatial or {}).get("source_longitude"),
            "source_grid_distance_km": (spatial or {}).get("distance_km"),
            **calendar_features(issue_date),
            **soil_history_features(soil_by_date, issue_date, windows),
            **weather_history_features(
                weather_by_date,
                issue_date,
                windows=windows,
                dry_day_mm=dry_day_mm,
                api_lookup=api_lookup,
                k_factors=k_factors,
                warmup_days=warmup_days,
                ordered_dates=weather_dates,
            ),
            **static_property_features(),
        }
        satellite = (satellite_by_issue or {}).get(issue_date) or empty_satellite_features()
        row.update(satellite)
        rows.append(row)
    return rows


def empty_satellite_features() -> dict[str, Any]:
    return {
        "satellite_available": False,
        "satellite_stale": False,
        "satellite_missing": True,
        "satellite_scene_id": None,
        "satellite_acquisition_date_utc": None,
        "satellite_acquisition_timestamp_utc": None,
        "satellite_age_days": None,
        "ndvi_last_valid_mean": None,
        "ndvi_last_valid_median": None,
        "ndvi_last_valid_std": None,
        "ndvi_last_valid_p10": None,
        "ndvi_last_valid_p90": None,
        "satellite_valid_pixel_fraction": None,
        "satellite_calibration_status": None,
        "satellite_scene_quality_status": None,
        "satellite_availability_assumption": "acquisition_time_only_research",
        "satellite_operational_availability_verified": False,
    }
