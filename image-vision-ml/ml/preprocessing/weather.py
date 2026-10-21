"""Numerical weather conversions and UTC daily aggregation.

This module is HTTP-free. ERA5-Land accumulation rules follow
https://confluence.ecmwf.int/display/CKB/Conversion+table+for+accumulated+variables
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable

import numpy as np


KELVIN_OFFSET = 273.15
METERS_TO_MM = 1000.0
ROUNDING_MM = 1e-6
ROUNDING_RH = 0.05

# Alduchov and Eskridge (1996) Magnus coefficients, valid near
# meteorological surface temperatures. e_sat in hPa, T in °C.
MAGNUS_A = 17.625
MAGNUS_B = 243.04
MAGNUS_C = 6.1094

# ECMWF accumulated fluxes are positive downward. Surface evaporation
# is therefore typically negative. We reverse the sign so processed
# evaporation_total_mm is water leaving the surface (positive upward).
ECMWF_FLUX_POSITIVE_DOWNWARD = True
EVAPORATION_SIGN = -1.0 if ECMWF_FLUX_POSITIVE_DOWNWARD else 1.0

NATIVE_RESOLUTION_DEG = 0.1
EARTH_RADIUS_KM = 6371.0

ROLE_OBSERVATION = "observation"
ROLE_BOUNDARY = "boundary"
ROLE_BOUNDARY_ONLY = "boundary_only"

# Float32 ERA5-Land fields: ~1 ULP at 270 K is ~3e-5 K; 1e-10 m is
# well below a micrometre of precipitation.
BOUNDARY_OVERLAP_FIELDS = (
    "t2m",
    "d2m",
    "tp",
    "u10",
    "v10",
    "e",
    "t2m_c",
    "d2m_c",
    "source_longitude",
    "source_latitude",
)
BOUNDARY_OVERLAP_TOLERANCE = {
    "t2m": 1e-4,
    "d2m": 1e-4,
    "t2m_c": 1e-4,
    "d2m_c": 1e-4,
    "tp": 1e-10,
    "e": 1e-10,
    "u10": 1e-5,
    "v10": 1e-5,
    "source_longitude": 1e-6,
    "source_latitude": 1e-6,
}


def kelvin_to_celsius(kelvin: float | np.ndarray) -> float | np.ndarray:
    return np.asarray(kelvin, dtype=np.float64) - KELVIN_OFFSET


def meters_to_mm(meters: float | np.ndarray) -> float | np.ndarray:
    return np.asarray(meters, dtype=np.float64) * METERS_TO_MM


def wind_speed(u: float | np.ndarray, v: float | np.ndarray) -> float | np.ndarray:
    return np.sqrt(
        np.asarray(u, dtype=np.float64) ** 2 + np.asarray(v, dtype=np.float64) ** 2
    )


def saturation_vapor_pressure_hpa(temperature_c: float | np.ndarray) -> np.ndarray:
    """Magnus-Tetens saturation vapor pressure in hPa."""
    temperature = np.asarray(temperature_c, dtype=np.float64)
    return MAGNUS_C * np.exp((MAGNUS_A * temperature) / (MAGNUS_B + temperature))


def relative_humidity_pct(
    temperature_c: float | np.ndarray,
    dewpoint_c: float | np.ndarray,
) -> np.ndarray:
    """Relative humidity from air and dew-point temperature.

    RH = 100 * e(Td) / e_sat(T). Values slightly outside 0–100 from
    floating-point noise are clamped. Larger impossibilities are kept.
    """
    e_air = saturation_vapor_pressure_hpa(dewpoint_c)
    e_sat = saturation_vapor_pressure_hpa(temperature_c)
    with np.errstate(divide="ignore", invalid="ignore"):
        humidity = 100.0 * e_air / e_sat
    humidity = np.asarray(humidity, dtype=np.float64)
    near_high = (humidity > 100.0) & (humidity <= 100.0 + ROUNDING_RH)
    near_low = (humidity < 0.0) & (humidity >= -ROUNDING_RH)
    humidity = np.where(near_high, 100.0, humidity)
    humidity = np.where(near_low, 0.0, humidity)
    return humidity


def convert_evaporation_mm(accumulated_m: float | np.ndarray) -> np.ndarray:
    """Convert ERA5-Land accumulated evaporation to upward millimetres."""
    return EVAPORATION_SIGN * meters_to_mm(accumulated_m)


def era5_land_hourly_increments(accumulated: Iterable[float]) -> list[float | None]:
    """Derive hourly increments from ERA5-Land cumulative forecast values.

    At 01 UTC the stored value is already the first-hour increment.
    Later hours are differences from the previous cumulative step.
    A reset (current < previous) starts a new forecast cycle.
    """
    values = [None if item is None or _is_nan(item) else float(item) for item in accumulated]
    increments: list[float | None] = []
    previous = None
    for index, current in enumerate(values):
        if current is None:
            increments.append(None)
            previous = None
            continue
        if previous is None:
            increments.append(current)
        elif current + ROUNDING_MM < previous:
            increments.append(current)
        else:
            increments.append(current - previous)
        previous = current
        _ = index
    return increments


def era5_land_daily_total_mm(
    next_day_00_accumulated_m: float | None,
    *,
    hourly_increments_m: list[float | None] | None = None,
) -> tuple[float | None, str]:
    """Daily precipitation/evaporation in millimetres.

    Official ERA5-Land method: the 00:00 UTC value of day D+1 is the
    accumulation for UTC day D. Hourly increments are a fallback when
    that boundary record is missing.
    """
    if next_day_00_accumulated_m is not None and not _is_nan(next_day_00_accumulated_m):
        return float(meters_to_mm(next_day_00_accumulated_m)), "next_day_00utc"
    if not hourly_increments_m:
        return None, "missing_boundary"
    finite = [float(value) for value in hourly_increments_m if value is not None and not _is_nan(value)]
    if not finite:
        return None, "missing_increments"
    return float(meters_to_mm(sum(finite))), "hourly_increments"


def nearest_era5_land_cell(
    longitude: float,
    latitude: float,
    longitudes: Iterable[float],
    latitudes: Iterable[float],
) -> dict[str, Any]:
    """Select the nearest native ERA5-Land grid point to a query location.

    Distance is geographic (haversine), not an independent 1-D degree
    snap. The query must be the study AOI centroid, not the centroid of
    an expanded CDS retrieval box.
    """
    lon_array = np.asarray(list(longitudes), dtype=np.float64)
    lat_array = np.asarray(list(latitudes), dtype=np.float64)
    if lon_array.size == 0 or lat_array.size == 0:
        raise ValueError("ERA5-Land coordinates are missing.")
    lon_grid, lat_grid = np.meshgrid(lon_array, lat_array)
    distances = geographic_distance_km(longitude, latitude, lon_grid, lat_grid)
    lat_idx, lon_idx = np.unravel_index(int(np.argmin(distances)), distances.shape)
    return {
        "method": "nearest_grid_cell",
        "source_longitude": float(lon_array[lon_idx]),
        "source_latitude": float(lat_array[lat_idx]),
        "longitude_index": int(lon_idx),
        "latitude_index": int(lat_idx),
        "distance_km": float(distances[lat_idx, lon_idx]),
        "native_resolution_deg": NATIVE_RESOLUTION_DEG,
        "query_longitude": float(longitude),
        "query_latitude": float(latitude),
    }


def geographic_distance_km(
    longitude: float,
    latitude: float,
    longitudes: float | np.ndarray,
    latitudes: float | np.ndarray,
) -> np.ndarray:
    """Haversine distance in kilometres on a spherical Earth."""
    lon1 = np.radians(longitude)
    lat1 = np.radians(latitude)
    lon2 = np.radians(np.asarray(longitudes, dtype=np.float64))
    lat2 = np.radians(np.asarray(latitudes, dtype=np.float64))
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    angle = (
        np.sin(dlat / 2.0) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    )
    return 2.0 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(angle, 0.0, 1.0)))


def aoi_centroid(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
    west, south, east, north = bbox
    return ((west + east) / 2.0, (south + north) / 2.0)


def expand_bbox_to_retrieval_area(
    bbox: tuple[float, float, float, float],
    *,
    resolution_deg: float = NATIVE_RESOLUTION_DEG,
) -> tuple[float, float, float, float]:
    """Pad a study AOI so a CDS crop can contain an ERA5-Land grid point.

    Returned order is north, west, south, east — the CDS ``area`` convention.
    """
    west, south, east, north = bbox
    pad = float(resolution_deg)
    return (north + pad, west - pad, south - pad, east + pad)


def era5_land_grid_points(
    retrieval_area: tuple[float, float, float, float] | list[float],
    *,
    resolution_deg: float = NATIVE_RESOLUTION_DEG,
) -> tuple[list[float], list[float]]:
    """Nominal 0.1° ERA5-Land axes that fall inside a CDS area crop."""
    north, west, south, east = (float(value) for value in retrieval_area)
    longitudes = _regular_axis(west, east, resolution_deg)
    latitudes = _regular_axis(south, north, resolution_deg)
    return longitudes, latitudes


def retrieval_area_has_grid_points(
    retrieval_area: tuple[float, float, float, float] | list[float],
    *,
    resolution_deg: float = NATIVE_RESOLUTION_DEG,
) -> bool:
    longitudes, latitudes = era5_land_grid_points(
        retrieval_area,
        resolution_deg=resolution_deg,
    )
    return bool(longitudes) and bool(latitudes)


def _regular_axis(low: float, high: float, resolution: float) -> list[float]:
    first = math.ceil(low / resolution - 1e-9) * resolution
    last = math.floor(high / resolution + 1e-9) * resolution
    if first > last + 1e-9:
        return []
    count = int(round((last - first) / resolution)) + 1
    return [round(first + index * resolution, 10) for index in range(count)]


def annotate_hourly_records(
    records: list[dict[str, Any]],
    *,
    month: str,
    filename: str,
    role: str,
    spatial: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Copy hourly records and tag their source month, file, and role."""
    annotated = []
    for item in records:
        record = dict(item)
        record["source_month"] = month
        record["source_file"] = filename
        record["record_role"] = role
        if spatial:
            if record.get("source_longitude") is None:
                record["source_longitude"] = spatial.get("source_longitude")
            if record.get("source_latitude") is None:
                record["source_latitude"] = spatial.get("source_latitude")
        annotated.append(record)
    return annotated


def reconcile_hourly_records(
    records: list[dict[str, Any]],
    *,
    downloaded_months: list[str] | None = None,
) -> dict[str, Any]:
    """Deduplicate expected month-boundary overlaps; keep unexpected copies.

    Matching ``D+1 00:00`` boundary hours and the next month's opening
    ``00:00`` record are the same ERA5-Land valid time. When values agree
    within float32-safe tolerances the observation is kept. Conflicting
    pairs are not silently discarded: the observation is used for
    aggregation and both values are stored for review. Duplicates inside
    the same source file stay in the stream so quality checks can reject
    them. A boundary whose calendar month was not downloaded is marked
    ``boundary_only`` and may close the previous day without becoming an
    observation of the following day.
    """
    downloaded = set(downloaded_months or [])
    grouped: dict[datetime, list[dict[str, Any]]] = defaultdict(list)
    for item in records:
        stamp = _as_utc(item.get("timestamp_utc") or item.get("time"))
        if stamp is None:
            grouped.setdefault(datetime.min.replace(tzinfo=timezone.utc), []).append(dict(item))
            continue
        grouped[stamp].append(dict(item))

    reconciled: list[dict[str, Any]] = []
    overlaps: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    unexpected: list[dict[str, Any]] = []
    boundary_only: list[str] = []

    for stamp, group in sorted(grouped.items(), key=lambda item: item[0]):
        if stamp == datetime.min.replace(tzinfo=timezone.utc):
            reconciled.extend(group)
            continue
        if len(group) == 1:
            record = _mark_boundary_only(group[0], stamp, downloaded)
            if record.get("record_role") == ROLE_BOUNDARY_ONLY:
                boundary_only.append(_stamp_text(stamp))
            reconciled.append(record)
            continue

        observations = [item for item in group if item.get("record_role") == ROLE_OBSERVATION]
        boundaries = [item for item in group if item.get("record_role") == ROLE_BOUNDARY]
        expected_pair = len(group) == 2 and len(observations) == 1 and len(boundaries) == 1
        if expected_pair:
            observation = observations[0]
            boundary = boundaries[0]
            if hourly_measurements_match(observation, boundary):
                kept = dict(observation)
                kept["record_role"] = ROLE_OBSERVATION
                kept["boundary_overlap"] = "reconciled"
                kept["overlap_source_files"] = [
                    observation.get("source_file"),
                    boundary.get("source_file"),
                ]
                reconciled.append(kept)
                overlaps.append({
                    "timestamp_utc": _stamp_text(stamp),
                    "status": "reconciled",
                    "sources": [
                        observation.get("source_file"),
                        boundary.get("source_file"),
                    ],
                })
                continue
            kept = dict(observation)
            kept["record_role"] = ROLE_OBSERVATION
            kept["boundary_overlap"] = "conflict"
            kept["overlap_source_files"] = [
                observation.get("source_file"),
                boundary.get("source_file"),
            ]
            reconciled.append(kept)
            conflicts.append({
                "timestamp_utc": _stamp_text(stamp),
                "status": "requires_review",
                "sources": [
                    observation.get("source_file"),
                    boundary.get("source_file"),
                ],
                "values": _overlap_values(observation, boundary),
            })
            continue

        unexpected.append({
            "timestamp_utc": _stamp_text(stamp),
            "status": "rejected",
            "count": len(group),
            "sources": [item.get("source_file") for item in group],
        })
        reconciled.extend(group)

    reconciled.sort(key=lambda item: _as_utc(item.get("timestamp_utc") or item.get("time")) or datetime.min.replace(tzinfo=timezone.utc))
    return {
        "records": reconciled,
        "overlaps": overlaps,
        "conflicts": conflicts,
        "unexpected_duplicates": unexpected,
        "boundary_only_timestamps": boundary_only,
    }


def hourly_measurements_match(
    left: dict[str, Any],
    right: dict[str, Any],
) -> bool:
    """Return True when overlapping hours agree within justified tolerances."""
    for field in BOUNDARY_OVERLAP_FIELDS:
        first = _maybe_float(left.get(field))
        second = _maybe_float(right.get(field))
        if first is None and second is None:
            continue
        if first is None or second is None:
            return False
        tolerance = BOUNDARY_OVERLAP_TOLERANCE.get(field, 1e-8)
        if abs(first - second) > tolerance:
            return False
    return True


def _mark_boundary_only(
    record: dict[str, Any],
    stamp: datetime,
    downloaded_months: set[str],
) -> dict[str, Any]:
    marked = dict(record)
    if marked.get("record_role") != ROLE_BOUNDARY:
        return marked
    stamp_month = f"{stamp.year:04d}-{stamp.month:02d}"
    if downloaded_months and stamp_month not in downloaded_months:
        marked["record_role"] = ROLE_BOUNDARY_ONLY
    elif not downloaded_months:
        source_month = marked.get("source_month")
        if source_month and stamp_month != source_month:
            marked["record_role"] = ROLE_BOUNDARY_ONLY
    return marked


def _overlap_values(
    left: dict[str, Any],
    right: dict[str, Any],
) -> dict[str, list[float | None]]:
    values = {}
    for field in BOUNDARY_OVERLAP_FIELDS:
        first = _maybe_float(left.get(field))
        second = _maybe_float(right.get(field))
        if first is None and second is None:
            continue
        values[field] = [first, second]
    return values


def _stamp_text(stamp: datetime) -> str:
    return stamp.isoformat().replace("+00:00", "Z")


def _is_day_instant(record: dict[str, Any]) -> bool:
    return record.get("record_role") != ROLE_BOUNDARY_ONLY


def aggregate_daily_weather(
    hourly_records: list[dict[str, Any]],
    *,
    period_start: date,
    period_end: date,
    aoi_id: str,
    source_dataset: str = "reanalysis-era5-land",
    spatial: dict[str, Any] | None = None,
    require_complete_days: bool = True,
) -> list[dict[str, Any]]:
    """Build one UTC-day row for every date in ``period_start``..``period_end``.

    Missing source hours stay missing. Precipitation uses the ERA5-Land
    next-day 00:00 convention and is never a naive sum of cumulatives.
    A ``boundary_only`` hour closes the previous UTC day and is not an
    observation of the following calendar day.
    """
    by_time: dict[datetime, dict[str, Any]] = {}
    for record in hourly_records:
        stamp = _as_utc(record.get("timestamp_utc") or record.get("time"))
        if stamp is None:
            continue
        by_time[stamp] = record

    days = _date_range(period_start, period_end)
    rows = []
    for day in days:
        start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        instants = [
            by_time[start + timedelta(hours=hour)]
            for hour in range(24)
            if (start + timedelta(hours=hour)) in by_time
            and _is_day_instant(by_time[start + timedelta(hours=hour)])
        ]
        next_00 = by_time.get(end)
        temperatures = [_maybe_float(item.get("t2m_c", item.get("t2m"))) for item in instants]
        temperatures = [_maybe_celsius(value, item) for value, item in zip(temperatures, instants)]
        dewpoints = [_maybe_float(item.get("d2m_c", item.get("d2m"))) for item in instants]
        dewpoints = [_maybe_celsius(value, item, key="d2m") for value, item in zip(dewpoints, instants)]
        winds = []
        for item in instants:
            if item.get("wind_speed_ms") is not None:
                winds.append(_maybe_float(item["wind_speed_ms"]))
            else:
                winds.append(_maybe_float(wind_speed(item.get("u10"), item.get("v10"))))
        humidities = []
        for temp, dew in zip(temperatures, dewpoints):
            if temp is None or dew is None:
                humidities.append(None)
            else:
                humidities.append(float(relative_humidity_pct(temp, dew)))

        precip, precip_method = _daily_flux(
            instants,
            next_00,
            field="tp",
        )
        evaporation, evap_method = _daily_flux(
            instants,
            next_00,
            field="e",
            convert=convert_evaporation_mm,
        )
        available = len(instants)
        complete = available == 24 and next_00 is not None
        status = "valid"
        if not complete:
            status = "warning" if available else "missing"
            if require_complete_days and next_00 is None:
                status = "requires_review" if available else "missing"
        if precip is not None and precip < -0.05:
            status = "requires_review"
        observation_kind = "complete" if complete else ("partial" if available else "missing")

        rows.append({
            "date_utc": day.isoformat(),
            "period_start_utc": start.isoformat().replace("+00:00", "Z"),
            "period_end_utc": end.isoformat().replace("+00:00", "Z"),
            "timezone": "UTC",
            "aoi_id": aoi_id,
            "temperature_mean_c": _mean(temperatures),
            "temperature_min_c": _min(temperatures),
            "temperature_max_c": _max(temperatures),
            "dewpoint_mean_c": _mean(dewpoints),
            "relative_humidity_mean_pct": _mean(humidities),
            "precipitation_total_mm": precip,
            "wind_speed_mean_ms": _mean(winds),
            "evaporation_total_mm": evaporation,
            "hourly_records_expected": 24,
            "hourly_records_available": available,
            "boundary_00utc_available": next_00 is not None,
            "precipitation_method": precip_method,
            "evaporation_method": evap_method,
            "quality_status": status,
            "observation_kind": observation_kind,
            "source_dataset": source_dataset,
            "source_grid_id": None if spatial is None else (
                f"{spatial.get('source_latitude')},{spatial.get('source_longitude')}"
            ),
            "spatial": spatial,
        })
    return rows


def _daily_flux(
    instants: list[dict[str, Any]],
    next_00: dict[str, Any] | None,
    *,
    field: str,
    convert=meters_to_mm,
) -> tuple[float | None, str]:
    next_value = None if next_00 is None else _maybe_float(next_00.get(field))
    if next_value is not None:
        return float(convert(next_value)), "next_day_00utc"
    ordered = sorted(instants, key=lambda item: _as_utc(item.get("timestamp_utc")) or datetime.min.replace(tzinfo=timezone.utc))
    values = [_maybe_float(item.get(field)) for item in ordered]
    increments = era5_land_hourly_increments(values)
    if next_00 is None:
        return None, "missing_boundary"
    finite = [float(convert(value)) for value in increments if value is not None]
    if not finite:
        return None, "missing_increments"
    return float(sum(finite)), "hourly_increments"


def _maybe_celsius(value: float | None, record: dict[str, Any], key: str = "t2m") -> float | None:
    if value is None:
        return None
    if f"{key}_c" in record or (key.endswith("_c")):
        return float(value)
    if value > 100:
        return float(kelvin_to_celsius(value))
    return float(value)


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


def _date_range(start: date, end: date) -> list[date]:
    days = []
    cursor = start
    while cursor <= end:
        days.append(cursor)
        cursor += timedelta(days=1)
    return days


def _maybe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    number = float(value)
    if _is_nan(number):
        return None
    return number


def _is_nan(value: Any) -> bool:
    try:
        return bool(np.isnan(value))
    except TypeError:
        return False


def _mean(values: list[float | None]) -> float | None:
    finite = [float(value) for value in values if value is not None]
    if not finite:
        return None
    return float(sum(finite) / len(finite))


def _min(values: list[float | None]) -> float | None:
    finite = [float(value) for value in values if value is not None]
    return None if not finite else float(min(finite))


def _max(values: list[float | None]) -> float | None:
    finite = [float(value) for value in values if value is not None]
    return None if not finite else float(max(finite))
