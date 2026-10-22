"""Instantaneous ERA5-Land volumetric soil-water calculations.

These variables are modeled states (m³/m³), not accumulated fluxes.
They must not be deaccumulated with the precipitation next-day 00:00 UTC rule.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable

from ml.preprocessing.weather import _maybe_float, aoi_centroid


SOIL_PROCESSING_VERSION = "3.4.0"
EXPECTED_HOURS = 24
VOLUMETRIC_UNIT = "m3 m-3"

# ECMWF TESSEL/HTESSEL layers. Layer 4 is excluded from the 0–100 cm mean.
SOIL_LAYERS = {
    "swvl1": {
        "cds_variable": "volumetric_soil_water_layer_1",
        "depth_top_m": 0.00,
        "depth_bottom_m": 0.07,
        "thickness_m": 0.07,
        "label": "0-7 cm",
    },
    "swvl2": {
        "cds_variable": "volumetric_soil_water_layer_2",
        "depth_top_m": 0.07,
        "depth_bottom_m": 0.28,
        "thickness_m": 0.21,
        "label": "7-28 cm",
    },
    "swvl3": {
        "cds_variable": "volumetric_soil_water_layer_3",
        "depth_top_m": 0.28,
        "depth_bottom_m": 1.00,
        "thickness_m": 0.72,
        "label": "28-100 cm",
    },
    "swvl4": {
        "cds_variable": "volumetric_soil_water_layer_4",
        "depth_top_m": 1.00,
        "depth_bottom_m": 2.89,
        "thickness_m": 1.89,
        "label": "100-289 cm",
    },
}

ROOT_ZONE_LAYERS = ("swvl1", "swvl2", "swvl3")
ROOT_ZONE_WEIGHTS = {
    "swvl1": 0.07,
    "swvl2": 0.21,
    "swvl3": 0.72,
}
ROOT_ZONE_WEIGHT_SUM = sum(ROOT_ZONE_WEIGHTS.values())

OBSERVATION_KIND = "modeled_volumetric_soil_moisture"
NOT_MEASURED_KIND = "measured_soil_moisture"

# Physical review bounds for volumetric fraction. Values are retained, not clamped.
THETA_INVALID_LOW = 0.0
THETA_INVALID_HIGH = 1.0


def root_zone_theta_0_100(
    theta1: float | None,
    theta2: float | None,
    theta3: float | None,
) -> float | None:
    """Thickness-weighted 0–100 cm volumetric mean.

    θ_0-100 = 0.07 θ1 + 0.21 θ2 + 0.72 θ3

    Layer 4 is excluded. Returns None if any of layers 1–3 is missing.
    This is a profile-average volumetric moisture, not crop-specific
    effective root-zone water.
    """
    if ROOT_ZONE_WEIGHT_SUM != 1.0:
        raise RuntimeError("Root-zone weights must sum to 1.0.")
    values = (theta1, theta2, theta3)
    if any(value is None for value in values):
        return None
    return (
        ROOT_ZONE_WEIGHTS["swvl1"] * float(theta1)
        + ROOT_ZONE_WEIGHTS["swvl2"] * float(theta2)
        + ROOT_ZONE_WEIGHTS["swvl3"] * float(theta3)
    )


def daily_mean_theta(hourly: Iterable[float | None], *, expected: int = EXPECTED_HOURS) -> float | None:
    """Mean of 24 valid hourly states. Missing hours yield None, never 0."""
    values = [float(item) for item in hourly if item is not None]
    if len(values) != int(expected):
        return None
    return sum(values) / float(expected)


def physical_flags(theta: float | None) -> list[str]:
    if theta is None:
        return []
    flags = []
    if theta < THETA_INVALID_LOW:
        flags.append("negative_volumetric_soil_water")
    if theta > THETA_INVALID_HIGH:
        flags.append("volumetric_soil_water_exceeds_unity")
    return flags


def compare_spatial_selection(
    left: dict[str, Any] | None,
    right: dict[str, Any] | None,
    *,
    longitude_tol: float = 1e-4,
    latitude_tol: float = 1e-4,
) -> dict[str, Any]:
    """Compare two ERA5-Land nearest-cell selections without claiming identity."""
    if not left or not right:
        return {
            "same_grid_cell": None,
            "reason": "one_or_both_spatial_records_missing",
        }
    lon_l = _maybe_float(left.get("source_longitude"))
    lat_l = _maybe_float(left.get("source_latitude"))
    lon_r = _maybe_float(right.get("source_longitude"))
    lat_r = _maybe_float(right.get("source_latitude"))
    if None in {lon_l, lat_l, lon_r, lat_r}:
        return {"same_grid_cell": None, "reason": "missing_coordinates"}
    same = abs(lon_l - lon_r) <= longitude_tol and abs(lat_l - lat_r) <= latitude_tol
    return {
        "same_grid_cell": same,
        "left": {"source_longitude": lon_l, "source_latitude": lat_l},
        "right": {"source_longitude": lon_r, "source_latitude": lat_r},
        "method_left": left.get("method"),
        "method_right": right.get("method"),
        "distance_km_left": left.get("distance_km"),
        "distance_km_right": right.get("distance_km"),
    }


def plant_available_water_fraction(
    theta: float | None,
    field_capacity: float | None,
    wilting_point: float | None,
) -> float | None:
    """R = (θ − θ_WP) / (θ_FC − θ_WP). None unless both thresholds exist."""
    if theta is None or field_capacity is None or wilting_point is None:
        return None
    denom = float(field_capacity) - float(wilting_point)
    if denom <= 0:
        return None
    return (float(theta) - float(wilting_point)) / denom


def aggregate_daily_soil(
    hourly_records: list[dict[str, Any]],
    *,
    period_start: str,
    period_end: str,
    aoi_id: str,
    source_dataset: str,
    spatial: dict[str, Any] | None,
    require_complete_days: bool = True,
    field_capacity: float | None = None,
    wilting_point: float | None = None,
) -> list[dict[str, Any]]:
    """UTC daily soil-water statistics from instantaneous hourly states."""
    by_time: dict[datetime, dict[str, Any]] = {}
    for record in hourly_records:
        stamp = _as_utc(record.get("timestamp_utc") or record.get("time"))
        if stamp is None:
            continue
        by_time[stamp] = record

    start = date.fromisoformat(period_start[:10])
    end = date.fromisoformat(period_end[:10])
    rows = []
    cursor = start
    while cursor <= end:
        instants = []
        for hour in range(EXPECTED_HOURS):
            stamp = datetime(cursor.year, cursor.month, cursor.day, hour, tzinfo=timezone.utc)
            if stamp in by_time:
                instants.append(by_time[stamp])
        available = len(instants)
        complete = available == EXPECTED_HOURS
        layer_series = {
            key: [_maybe_float(item.get(key)) for item in instants]
            for key in SOIL_LAYERS
        }
        daily_layers: dict[str, Any] = {}
        flags: list[str] = []
        for key, series in layer_series.items():
            mean = daily_mean_theta(series) if complete else None
            finite = [value for value in series if value is not None]
            daily_layers[f"{key}_mean"] = mean
            daily_layers[f"{key}_min"] = min(finite) if finite and complete else None
            daily_layers[f"{key}_max"] = max(finite) if finite and complete else None
            daily_layers[f"{key}_end_of_day"] = series[-1] if complete else None
            daily_layers[f"{key}_start_of_day"] = series[0] if complete else None
            daily_layers[f"{key}_daily_change"] = (
                None
                if not complete or series[0] is None or series[-1] is None
                else series[-1] - series[0]
            )
            daily_layers[f"{key}_valid_hours"] = sum(1 for value in series if value is not None)
            for value in finite:
                flags.extend(physical_flags(value))
            if not complete and require_complete_days and any(value is not None for value in series):
                flags.append("incomplete_hourly_coverage")
            if any(value is None for value in series) and complete:
                flags.append(f"missing_{key}_within_complete_clock")

        root = root_zone_theta_0_100(
            daily_layers["swvl1_mean"],
            daily_layers["swvl2_mean"],
            daily_layers["swvl3_mean"],
        )
        paw = plant_available_water_fraction(root, field_capacity, wilting_point)
        status = "valid" if complete and not flags else (
            "missing" if available == 0 else "warning"
        )
        if any(item.startswith("negative_") or item.endswith("unity") for item in flags):
            status = "requires_review"
        if not complete and require_complete_days and available:
            status = "requires_review" if status != "requires_review" else status
            if "incomplete_hourly_coverage" not in flags:
                flags.append("incomplete_hourly_coverage")

        start_utc = datetime(cursor.year, cursor.month, cursor.day, tzinfo=timezone.utc)
        end_utc = start_utc + timedelta(days=1)
        rows.append({
            "date_utc": cursor.isoformat(),
            "period_start_utc": start_utc.isoformat().replace("+00:00", "Z"),
            "period_end_utc": end_utc.isoformat().replace("+00:00", "Z"),
            "timezone": "UTC",
            "aoi_id": aoi_id,
            "unit": VOLUMETRIC_UNIT,
            "observation_kind": OBSERVATION_KIND,
            "is_ground_truth": False,
            "is_measured_soil_moisture": False,
            "hourly_records_expected": EXPECTED_HOURS,
            "hourly_records_available": available,
            "complete_day": complete,
            "quality_status": status,
            "quality_flags": sorted(set(flags)),
            "theta_root_zone_0_100": root,
            "plant_available_water_fraction": paw,
            "source_dataset": source_dataset,
            "source_grid_id": None if spatial is None else (
                f"{spatial.get('source_latitude')},{spatial.get('source_longitude')}"
            ),
            "spatial": spatial,
            "aggregation": "arithmetic_mean_of_24_hourly_states",
            "boundary_rule": "not_applicable_instantaneous_state",
            **daily_layers,
        })
        cursor = cursor + timedelta(days=1)
    _attach_anomalies(rows)
    return rows


def annotate_anomalies(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    _attach_anomalies(rows)
    return rows


def _attach_anomalies(rows: list[dict[str, Any]]) -> None:
    """Period-relative anomalies, not climate normals."""
    complete = [
        item for item in rows
        if item.get("complete_day") and item.get("theta_root_zone_0_100") is not None
    ]
    if len(complete) < 30:
        for item in rows:
            item["theta_root_zone_anomaly"] = None
            item["anomaly_basis"] = "insufficient_complete_days_for_period_mean"
        return
    mean = sum(float(item["theta_root_zone_0_100"]) for item in complete) / len(complete)
    for item in rows:
        value = item.get("theta_root_zone_0_100")
        item["theta_root_zone_anomaly"] = None if value is None else float(value) - mean
        item["anomaly_basis"] = "period_mean_of_complete_days"


def _as_utc(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def soil_spatial_from_bbox(bbox: tuple[float, float, float, float], spatial: dict[str, Any] | None) -> dict[str, Any]:
    if spatial:
        return dict(spatial)
    lon, lat = aoi_centroid(bbox)
    return {
        "method": "nearest_grid_cell",
        "query_longitude": lon,
        "query_latitude": lat,
        "native_resolution_deg": 0.1,
    }
