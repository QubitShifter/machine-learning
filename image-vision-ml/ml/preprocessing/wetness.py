"""Rainfall-history and weather-derived wetness indicators.

These are not measured soil moisture and not ERA5-Land volumetric water.
Missing precipitation is never treated as zero.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from ml.integration.satellite_weather import prior_window_dates
from ml.preprocessing.weather import _maybe_float


WETNESS_VERSION = "3.4.0"
DEFAULT_API_K = 0.90
DEFAULT_API_FACTORS = (0.85, 0.90, 0.95)
DEFAULT_WARMUP_DAYS = 30
DEFAULT_DRY_DAY_MM = 1.0
TRAILING_WINDOWS = (1, 3, 7, 14, 30)

KIND_RAINFALL_HISTORY = "rainfall_history_indicator"
KIND_WETNESS_PROXY = "weather_derived_wetness_proxy"
KIND_MODELED_MOISTURE = "modeled_volumetric_soil_moisture"
KIND_MEASURED_MOISTURE = "measured_soil_moisture"
KIND_PREDICTED_MOISTURE = "predicted_soil_moisture"

WATER_BALANCE_STATUS = "not_estimated"
WATER_BALANCE_REASON = (
    "Irrigation, runoff, drainage, and crop ET are not available. "
    "ERA5-Land total evaporation is not reference or crop evapotranspiration. "
    "S_{t+1}=S_t+P_t+I_t-ET_t-R_t-D_t remains conceptual."
)


def antecedent_precipitation_index(
    precipitation_mm: list[float | None],
    *,
    k: float = DEFAULT_API_K,
    initial: float = 0.0,
) -> list[float | None]:
    """API_t = P_t + k API_{t-1}.

    ``initial`` is API before the first element (API_0). A missing P_t
    yields API_t = None and all subsequent values remain None.
    k must be in (0, 1].
    """
    if k <= 0 or k > 1:
        raise ValueError("API decay k must satisfy 0 < k <= 1.")
    previous: float | None = float(initial)
    output: list[float | None] = []
    for precip in precipitation_mm:
        if previous is None or precip is None:
            output.append(None)
            previous = None
            continue
        current = float(precip) + float(k) * previous
        output.append(current)
        previous = current
    return output


def days_since_rain(
    precipitation_mm: list[float | None],
    *,
    dry_day_mm: float = DEFAULT_DRY_DAY_MM,
) -> list[int | None]:
    """Days since last P >= dry_day_mm. None until the first rain, and after gaps."""
    counts: list[int | None] = []
    last_rain_index: int | None = None
    broken = False
    for index, precip in enumerate(precipitation_mm):
        if precip is None:
            counts.append(None)
            broken = True
            continue
        if float(precip) >= float(dry_day_mm):
            last_rain_index = index
            broken = False
            counts.append(0)
            continue
        if broken or last_rain_index is None:
            counts.append(None)
            continue
        counts.append(index - last_rain_index)
    return counts


def consecutive_dry_days(
    precipitation_mm: list[float | None],
    *,
    dry_day_mm: float = DEFAULT_DRY_DAY_MM,
) -> list[int | None]:
    """Run length of days with P < dry_day_mm. Missing P breaks the run."""
    output: list[int | None] = []
    run: int | None = 0
    for precip in precipitation_mm:
        if precip is None:
            output.append(None)
            run = None
            continue
        if run is None:
            run = 0
        if float(precip) < float(dry_day_mm):
            run += 1
            output.append(run)
        else:
            run = 0
            output.append(0)
    return output


def trailing_sum(
    values: list[float | None],
    window: int,
    *,
    include_current: bool,
) -> list[float | None]:
    """Rolling sum. Incomplete windows or any missing value yield None."""
    if window < 1:
        raise ValueError("window must be >= 1.")
    output: list[float | None] = []
    for index in range(len(values)):
        if include_current:
            start = index - window + 1
            end = index
        else:
            start = index - window
            end = index - 1
        if start < 0 or end < 0:
            output.append(None)
            continue
        slice_values = values[start:end + 1]
        if len(slice_values) != window or any(item is None for item in slice_values):
            output.append(None)
            continue
        output.append(float(sum(slice_values)))
    return output


def attach_wetness_features(
    daily_rows: list[dict[str, Any]],
    *,
    k_factors: tuple[float, ...] = DEFAULT_API_FACTORS,
    warmup_days: int = DEFAULT_WARMUP_DAYS,
    dry_day_mm: float = DEFAULT_DRY_DAY_MM,
    windows: tuple[int, ...] = TRAILING_WINDOWS,
) -> list[dict[str, Any]]:
    """Add rainfall-history and wetness-proxy columns to daily weather rows.

    End-of-day API includes P_t. Satellite-aligned precip_prev_N excludes
    date D and is provided for explicit comparison; existing integration
    windows are not rewritten.
    """
    ordered = sorted(daily_rows, key=lambda item: str(item.get("date_utc") or ""))
    precip = [_maybe_float(item.get("precipitation_total_mm")) for item in ordered]
    evap = [_maybe_float(item.get("evaporation_total_mm")) for item in ordered]
    dry_flags = consecutive_dry_days(precip, dry_day_mm=dry_day_mm)
    since = days_since_rain(precip, dry_day_mm=dry_day_mm)

    api_series = {
        k: antecedent_precipitation_index(precip, k=k)
        for k in k_factors
    }
    end_of_day_sums = {
        window: trailing_sum(precip, window, include_current=True)
        for window in windows
    }
    prev_sums = {
        window: trailing_sum(precip, window, include_current=False)
        for window in windows
    }
    evap_end = {
        window: trailing_sum(evap, window, include_current=True)
        for window in (7, 30) if window in windows or True
    }

    for index, row in enumerate(ordered):
        valid_precip_so_far = sum(1 for value in precip[: index + 1] if value is not None)
        row["wetness_version"] = WETNESS_VERSION
        row["rainfall_history_kind"] = KIND_RAINFALL_HISTORY
        row["wetness_proxy_kind"] = KIND_WETNESS_PROXY
        row["is_measured_soil_moisture"] = False
        row["is_modeled_soil_moisture"] = False
        row["water_balance_status"] = WATER_BALANCE_STATUS
        row["water_balance_reason"] = WATER_BALANCE_REASON
        row["dry_day_precipitation_mm"] = dry_day_mm
        row["consecutive_dry_days"] = dry_flags[index]
        row["days_since_rain"] = since[index]
        row["api_warmup_days"] = warmup_days
        for k, series in api_series.items():
            key = _api_key(k)
            value = series[index]
            row[key] = value
            row[f"{key}_warmup"] = bool(
                value is not None and valid_precip_so_far <= warmup_days
            )
        for window in windows:
            row[f"precip_trailing_{window}d_end_of_day_mm"] = end_of_day_sums[window][index]
            row[f"precip_prev_{window}d_mm"] = prev_sums[window][index]
            row[f"precip_prev_{window}d_excludes_date_d"] = True
            row[f"precip_trailing_{window}d_includes_date_d"] = True
        for window in (7, 30):
            evap_sum = evap_end[window][index]
            rain_sum = end_of_day_sums.get(window, prev_sums.get(window))[index]
            row[f"evap_trailing_{window}d_end_of_day_mm"] = evap_sum
            if rain_sum is None or evap_sum is None:
                row[f"precip_minus_evap_{window}d_mm"] = None
            else:
                row[f"precip_minus_evap_{window}d_mm"] = float(rain_sum) - float(evap_sum)
            row[f"precip_minus_evap_{window}d_kind"] = KIND_WETNESS_PROXY
        if index > 0 and precip[index] is not None and precip[index - 1] is not None:
            row["precip_day_to_day_change_mm"] = float(precip[index]) - float(precip[index - 1])
        else:
            row["precip_day_to_day_change_mm"] = None
    return ordered


def satellite_aligned_precip_window(
    observation_date: date,
    weather_by_date: dict[date, dict[str, Any]],
    window: int,
) -> float | None:
    """P_N(D) = sum_{i=1..N} P[D-i]. Acquisition date D is excluded."""
    days = prior_window_dates(observation_date, window)
    values = []
    for day in days:
        record = weather_by_date.get(day) or {}
        value = _maybe_float(record.get("precipitation_total_mm"))
        if value is None:
            return None
        values.append(value)
    if len(values) != window:
        return None
    return float(sum(values))


def _api_key(k: float) -> str:
    text = f"{k:.2f}".replace(".", "")
    return f"api_k{text}_mm"
