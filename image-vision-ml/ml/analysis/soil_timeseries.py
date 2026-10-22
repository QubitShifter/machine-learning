"""Write daily soil-moisture tables, summaries, and chart data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ml.analysis.weather_timeseries import (
    _as_date,
    _max_field,
    _mean_field,
    _min_field,
    _write_csv,
    _write_parquet,
    read_daily_weather,
)
from ml.preprocessing.soil import SOIL_LAYERS
from ml.preprocessing.weather import _maybe_float


DAILY_SOIL_COLUMNS = (
    "date_utc",
    "aoi_id",
    "unit",
    "observation_kind",
    "is_ground_truth",
    "is_measured_soil_moisture",
    "swvl1_mean",
    "swvl1_min",
    "swvl1_max",
    "swvl1_end_of_day",
    "swvl1_daily_change",
    "swvl2_mean",
    "swvl2_min",
    "swvl2_max",
    "swvl2_end_of_day",
    "swvl2_daily_change",
    "swvl3_mean",
    "swvl3_min",
    "swvl3_max",
    "swvl3_end_of_day",
    "swvl3_daily_change",
    "swvl4_mean",
    "swvl4_min",
    "swvl4_max",
    "swvl4_end_of_day",
    "swvl4_daily_change",
    "theta_root_zone_0_100",
    "theta_root_zone_anomaly",
    "plant_available_water_fraction",
    "hourly_records_expected",
    "hourly_records_available",
    "complete_day",
    "quality_status",
    "quality_flags",
    "source_dataset",
    "source_grid_id",
    "aggregation",
    "boundary_rule",
)

read_daily_soil = read_daily_weather


def flatten_soil_row(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    flags = item.get("quality_flags") or []
    if isinstance(flags, list):
        item["quality_flags"] = ";".join(str(flag) for flag in flags)
    spatial = item.get("spatial")
    if isinstance(spatial, dict):
        item.pop("spatial", None)
    return item


def write_daily_soil(rows: list[dict[str, Any]], directory: Path) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=True)
    csv_path = directory / "daily_soil.csv"
    flattened = [flatten_soil_row(item) for item in rows]
    _write_csv(csv_path, flattened, DAILY_SOIL_COLUMNS)
    outputs: dict[str, Any] = {"daily_csv": csv_path.name, "parquet_generated": False}
    parquet_path = directory / "daily_soil.parquet"
    if _write_parquet(flattened, parquet_path):
        outputs["daily_parquet"] = parquet_path.name
        outputs["parquet_generated"] = True
    chart_data = directory / "soil_chart_data.json"
    chart_data.write_text(json.dumps(_chart_points(rows), indent=2), encoding="utf-8")
    outputs["chart_data"] = chart_data.name
    return outputs


def write_monthly_soil_summary(
    rows: list[dict[str, Any]],
    path: Path,
    *,
    downloaded_months: list[str] | None = None,
) -> list[dict[str, Any]]:
    monthly = monthly_soil_summary(rows, downloaded_months=downloaded_months)
    columns = (
        "month",
        "day_count",
        "complete_days",
        "missing_days",
        "availability",
        "swvl1_mean",
        "swvl2_mean",
        "swvl3_mean",
        "swvl4_mean",
        "theta_root_zone_0_100_mean",
        "theta_root_zone_0_100_min",
        "theta_root_zone_0_100_max",
    )
    _write_csv(path, monthly, columns)
    return monthly


def monthly_soil_summary(
    rows: list[dict[str, Any]],
    *,
    downloaded_months: list[str] | None = None,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in rows:
        parsed = _as_date(item.get("date_utc"))
        if parsed is None:
            continue
        grouped.setdefault(parsed.strftime("%Y-%m"), []).append(item)
    months = sorted(set(grouped) | set(downloaded_months or []))
    output = []
    for month in months:
        items = grouped.get(month) or []
        complete = [item for item in items if item.get("complete_day")]
        output.append({
            "month": month,
            "day_count": len(items),
            "complete_days": len(complete),
            "missing_days": sum(1 for item in items if not item.get("hourly_records_available")),
            "availability": "complete" if complete and len(complete) == len(items) else (
                "partial" if complete else "missing"
            ),
            **{
                f"{key}_mean": _mean_field(complete, f"{key}_mean")
                for key in SOIL_LAYERS
            },
            "theta_root_zone_0_100_mean": _mean_field(complete, "theta_root_zone_0_100"),
            "theta_root_zone_0_100_min": _min_field(complete, "theta_root_zone_0_100"),
            "theta_root_zone_0_100_max": _max_field(complete, "theta_root_zone_0_100"),
        })
    return output


def write_soil_chart(rows: list[dict[str, Any]], path: Path) -> Path | None:
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except ImportError:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    dates = []
    surface = []
    root = []
    for item in rows:
        parsed = _as_date(item.get("date_utc"))
        if parsed is None:
            continue
        dates.append(parsed)
        surface.append(_nan(item.get("swvl1_mean")))
        root.append(_nan(item.get("theta_root_zone_0_100")))
    if not dates:
        return None
    figure, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    axes[0].plot(dates, surface, color="tab:brown", linewidth=1.2)
    axes[0].set_ylabel("Layer 1 θ (m³/m³)")
    axes[0].grid(True, alpha=0.3)
    axes[1].plot(dates, root, color="tab:green", linewidth=1.2)
    axes[1].set_ylabel("0–100 cm θ (m³/m³)")
    axes[1].set_xlabel("UTC date")
    locator = mdates.AutoDateLocator()
    formatter = mdates.DateFormatter("%Y-%m-%d")
    for axis in axes:
        axis.xaxis.set_major_locator(locator)
        axis.xaxis.set_major_formatter(formatter)
    figure.autofmt_xdate()
    figure.tight_layout()
    figure.savefig(path, dpi=120)
    plt.close(figure)
    return path


def _chart_points(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    points = []
    for item in rows:
        points.append({
            "date_utc": item.get("date_utc"),
            "swvl1_mean": _maybe_float(item.get("swvl1_mean")),
            "swvl2_mean": _maybe_float(item.get("swvl2_mean")),
            "swvl3_mean": _maybe_float(item.get("swvl3_mean")),
            "swvl4_mean": _maybe_float(item.get("swvl4_mean")),
            "theta_root_zone_0_100": _maybe_float(item.get("theta_root_zone_0_100")),
            "quality_status": item.get("quality_status"),
        })
    return points


def _nan(value: Any) -> float:
    parsed = _maybe_float(value)
    return float("nan") if parsed is None else parsed
