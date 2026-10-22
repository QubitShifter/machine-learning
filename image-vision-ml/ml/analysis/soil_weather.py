"""Exploratory relationships between rainfall/weather and modeled soil moisture.

Correlation with ERA5-Land soil water is not independent validation.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from ml.preprocessing.weather import _maybe_float


DIAGNOSTIC_LABEL = "exploratory_not_independent_validation"


def pearson(x: list[float], y: list[float]) -> float | None:
    if len(x) != len(y) or len(x) < 3:
        return None
    mean_x = sum(x) / len(x)
    mean_y = sum(y) / len(y)
    num = sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y))
    den_x = sum((a - mean_x) ** 2 for a in x) ** 0.5
    den_y = sum((b - mean_y) ** 2 for b in y) ** 0.5
    if den_x == 0 or den_y == 0:
        return None
    return num / (den_x * den_y)


def lagged_pairs(
    soil_by_date: dict[date, float],
    driver_by_date: dict[date, float],
    lag_days: int,
) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    for day, theta in soil_by_date.items():
        driver_day = date.fromordinal(day.toordinal() - lag_days)
        driver = driver_by_date.get(driver_day)
        if driver is None:
            continue
        xs.append(driver)
        ys.append(theta)
    return xs, ys


def exploratory_soil_weather_report(
    soil_rows: list[dict[str, Any]],
    weather_rows: list[dict[str, Any]],
    *,
    lags: tuple[int, ...] = (0, 1, 3, 7),
) -> dict[str, Any]:
    soil_by_date: dict[date, dict[str, Any]] = {}
    for item in soil_rows:
        parsed = _as_date(item.get("date_utc"))
        if parsed is None or not item.get("complete_day"):
            continue
        soil_by_date[parsed] = item
    weather_by_date: dict[date, dict[str, Any]] = {}
    for item in weather_rows:
        parsed = _as_date(item.get("date_utc"))
        if parsed is None:
            continue
        weather_by_date[parsed] = item

    surface = {
        day: float(row["swvl1_mean"])
        for day, row in soil_by_date.items()
        if _maybe_float(row.get("swvl1_mean")) is not None
    }
    root = {
        day: float(row["theta_root_zone_0_100"])
        for day, row in soil_by_date.items()
        if _maybe_float(row.get("theta_root_zone_0_100")) is not None
    }
    precip = {
        day: float(row["precipitation_total_mm"])
        for day, row in weather_by_date.items()
        if _maybe_float(row.get("precipitation_total_mm")) is not None
    }
    evap = {
        day: float(row["evaporation_total_mm"])
        for day, row in weather_by_date.items()
        if _maybe_float(row.get("evaporation_total_mm")) is not None
    }
    temp = {
        day: float(row["temperature_mean_c"])
        for day, row in weather_by_date.items()
        if _maybe_float(row.get("temperature_mean_c")) is not None
    }

    correlations = []
    for lag in lags:
        px, py = lagged_pairs(surface, precip, lag)
        correlations.append({
            "soil_layer": "swvl1_mean",
            "driver": "precipitation_total_mm",
            "lag_days": lag,
            "n": len(px),
            "pearson": pearson(px, py),
        })
        rx, ry = lagged_pairs(root, precip, lag)
        correlations.append({
            "soil_layer": "theta_root_zone_0_100",
            "driver": "precipitation_total_mm",
            "lag_days": lag,
            "n": len(rx),
            "pearson": pearson(rx, ry),
        })
    ex, ey = lagged_pairs(surface, evap, 0)
    tx, ty = lagged_pairs(surface, temp, 0)
    correlations.append({
        "soil_layer": "swvl1_mean",
        "driver": "evaporation_total_mm",
        "lag_days": 0,
        "n": len(ex),
        "pearson": pearson(ex, ey),
    })
    correlations.append({
        "soil_layer": "swvl1_mean",
        "driver": "temperature_mean_c",
        "lag_days": 0,
        "n": len(tx),
        "pearson": pearson(tx, ty),
    })
    return {
        "label": DIAGNOSTIC_LABEL,
        "independent_validation": False,
        "reason": (
            "ERA5-Land soil water and ERA5-Land precipitation/evaporation share "
            "land-surface modelling ancestry. Correlation is exploratory only."
        ),
        "paired_complete_days": len(set(surface) & set(precip)),
        "correlations": correlations,
    }


def align_soil_weather_wetness(
    soil_rows: list[dict[str, Any]],
    weather_rows: list[dict[str, Any]] | None = None,
    wetness_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Outer-join daily series on UTC date. Missing values stay None."""
    by_date: dict[str, dict[str, Any]] = {}

    def row_for(day: str) -> dict[str, Any]:
        return by_date.setdefault(day, {"date_utc": day})

    for item in soil_rows or []:
        day = _day_key(item.get("date_utc"))
        if day is None:
            continue
        row = row_for(day)
        row["soil_present"] = True
        for field in ("swvl1_mean", "swvl2_mean", "swvl3_mean", "swvl4_mean", "theta_root_zone_0_100"):
            row[field] = item.get(field)
        row["complete_day_soil"] = item.get("complete_day")
        row["quality_status_soil"] = item.get("quality_status")
        row["observation_kind_soil"] = item.get("observation_kind")
        row["source_grid_id"] = item.get("source_grid_id")
    for item in weather_rows or []:
        day = _day_key(item.get("date_utc"))
        if day is None:
            continue
        row = row_for(day)
        row["weather_present"] = True
        for field in (
            "precipitation_total_mm",
            "evaporation_total_mm",
            "temperature_mean_c",
            "relative_humidity_mean_pct",
            "wind_speed_mean_ms",
        ):
            if row.get(field) is None:
                row[field] = item.get(field)
        row["quality_status_weather"] = item.get("quality_status")
        row["observation_kind_weather"] = item.get("observation_kind")
    for item in wetness_rows or []:
        day = _day_key(item.get("date_utc"))
        if day is None:
            continue
        row = row_for(day)
        row["wetness_present"] = True
        for field in (
            "api_k085_mm",
            "api_k090_mm",
            "api_k095_mm",
            "consecutive_dry_days",
            "days_since_rain",
            "precip_prev_7d_mm",
            "precip_prev_14d_mm",
            "precip_prev_30d_mm",
            "precip_trailing_7d_end_of_day_mm",
            "precip_trailing_14d_end_of_day_mm",
            "precip_trailing_30d_end_of_day_mm",
            "precip_minus_evap_7d_mm",
            "precip_minus_evap_30d_mm",
            "rainfall_history_kind",
            "wetness_proxy_kind",
            "precipitation_total_mm",
        ):
            if row.get(field) is None:
                row[field] = item.get(field)
    aligned = []
    for day in sorted(by_date):
        row = by_date[day]
        weather_kind = str(row.get("observation_kind_weather") or "")
        row["is_forecast"] = "forecast" in weather_kind.lower()
        row["soil_present"] = bool(row.get("soil_present"))
        row["weather_present"] = bool(row.get("weather_present"))
        row["wetness_present"] = bool(row.get("wetness_present"))
        for field in ("swvl1_mean", "swvl2_mean", "swvl3_mean", "swvl4_mean", "theta_root_zone_0_100", "precipitation_total_mm", "api_k090_mm"):
            row.setdefault(field, None)
        aligned.append(row)
    return aligned


def _day_key(value: Any) -> str | None:
    parsed = _as_date(value)
    return None if parsed is None else parsed.isoformat()


def _as_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not hasattr(value, "hour"):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None
