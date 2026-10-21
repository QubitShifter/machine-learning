"""Daily weather summaries and time-series visualization."""

from __future__ import annotations

import csv
import logging
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from ml.ingestion.manifest import write_json_atomic
from ml.preprocessing.weather import _maybe_float


logger = logging.getLogger(__name__)

DAILY_COLUMNS = (
    "date_utc",
    "aoi_id",
    "temperature_mean_c",
    "temperature_min_c",
    "temperature_max_c",
    "dewpoint_mean_c",
    "relative_humidity_mean_pct",
    "precipitation_total_mm",
    "wind_speed_mean_ms",
    "evaporation_total_mm",
    "hourly_records_expected",
    "hourly_records_available",
    "quality_status",
    "source_dataset",
    "source_grid_id",
    "period_start_utc",
    "period_end_utc",
    "timezone",
    "boundary_00utc_available",
    "precipitation_method",
    "evaporation_method",
    "observation_kind",
)


def monthly_weather_summary(
    rows: list[dict[str, Any]],
    *,
    downloaded_months: list[str] | None = None,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("date_utc"):
            grouped[str(row["date_utc"])[:7]].append(row)
    known = set(downloaded_months or [])
    monthly = []
    for month in sorted(grouped):
        items = grouped[month]
        complete_items = [
            item
            for item in items
            if item.get("hourly_records_available") == 24
            and item.get("boundary_00utc_available")
        ]
        observed_items = [
            item for item in items if item.get("hourly_records_available")
        ]
        if downloaded_months is not None:
            availability = "downloaded" if month in known else "missing_source"
        else:
            availability = "downloaded" if complete_items else "missing_source"
        if availability == "downloaded" and len(complete_items) < len(items):
            availability = "partial" if complete_items or observed_items else "downloaded"
        monthly.append({
            "month": month,
            "day_count": len(items),
            "complete_days": len(complete_items),
            "availability": availability,
            "temperature_mean_c": _mean_field(complete_items, "temperature_mean_c"),
            "temperature_min_c": _min_field(complete_items, "temperature_min_c"),
            "temperature_max_c": _max_field(complete_items, "temperature_max_c"),
            "precipitation_total_mm": _sum_field(complete_items, "precipitation_total_mm"),
            "evaporation_total_mm": _sum_field(complete_items, "evaporation_total_mm"),
            "relative_humidity_mean_pct": _mean_field(complete_items, "relative_humidity_mean_pct"),
            "wind_speed_mean_ms": _mean_field(complete_items, "wind_speed_mean_ms"),
            "missing_days": sum(
                1 for item in items if not item.get("hourly_records_available")
            ),
        })
    return monthly


def write_daily_weather(rows: list[dict[str, Any]], directory: Path) -> dict[str, str]:
    directory.mkdir(parents=True, exist_ok=True)
    csv_path = directory / "daily_weather.csv"
    _write_csv(csv_path, rows, DAILY_COLUMNS)
    outputs = {"daily_csv": csv_path.name}
    parquet_path = directory / "daily_weather.parquet"
    if _write_parquet(rows, parquet_path):
        outputs["daily_parquet"] = parquet_path.name
    return outputs


def write_monthly_summary(
    rows: list[dict[str, Any]],
    path: Path,
    *,
    downloaded_months: list[str] | None = None,
) -> list[dict[str, Any]]:
    monthly = monthly_weather_summary(rows, downloaded_months=downloaded_months)
    columns = (
        "month",
        "day_count",
        "complete_days",
        "missing_days",
        "availability",
        "temperature_mean_c",
        "temperature_min_c",
        "temperature_max_c",
        "precipitation_total_mm",
        "evaporation_total_mm",
        "relative_humidity_mean_pct",
        "wind_speed_mean_ms",
    )
    _write_csv(path, monthly, columns)
    return monthly


def write_weather_chart(rows: list[dict[str, Any]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    points = []
    for item in rows:
        parsed = _as_date(item.get("date_utc"))
        if parsed is None:
            continue
        points.append((
            parsed,
            _maybe_float(item.get("temperature_mean_c")),
            _maybe_float(item.get("precipitation_total_mm")),
        ))
    dates = [item[0] for item in points]
    temps = [float("nan") if item[1] is None else item[1] for item in points]
    rain = [float("nan") if item[2] is None else item[2] for item in points]
    figure, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    axes[0].plot(dates, temps, color="tab:red", linewidth=1.2)
    axes[0].set_ylabel("Mean temperature (°C)")
    axes[0].grid(True, alpha=0.3)
    axes[1].bar(dates, rain, color="tab:blue", width=0.8)
    axes[1].set_ylabel("Precipitation (mm)")
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


def _as_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not hasattr(value, "hour"):
        return value
    text = str(value)[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def read_daily_weather(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for item in reader:
            rows.append({
                key: _coerce(item.get(key))
                for key in reader.fieldnames or []
            })
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.stem}.tmp{path.suffix}")
    try:
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({
                    column: "" if row.get(column) is None else row.get(column)
                    for column in columns
                })
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _write_parquet(rows: list[dict[str, Any]], path: Path) -> bool:
    try:
        import pandas as pd
    except ImportError:
        return False
    try:
        frame = pd.DataFrame(rows)
        frame.to_parquet(path, index=False)
        return True
    except Exception as exc:
        logger.info("Parquet export skipped: %s", exc)
        return False


def _mean_field(rows: list[dict[str, Any]], field: str) -> float | None:
    values = [_maybe_float(item.get(field)) for item in rows]
    finite = [value for value in values if value is not None]
    if not finite:
        return None
    return float(sum(finite) / len(finite))


def _sum_field(rows: list[dict[str, Any]], field: str) -> float | None:
    values = [_maybe_float(item.get(field)) for item in rows]
    finite = [value for value in values if value is not None]
    if not finite:
        return None
    return float(sum(finite))


def _min_field(rows: list[dict[str, Any]], field: str) -> float | None:
    values = [_maybe_float(item.get(field)) for item in rows]
    finite = [value for value in values if value is not None]
    return None if not finite else float(min(finite))


def _max_field(rows: list[dict[str, Any]], field: str) -> float | None:
    values = [_maybe_float(item.get(field)) for item in rows]
    finite = [value for value in values if value is not None]
    return None if not finite else float(max(finite))


def _coerce(value: str | None) -> Any:
    if value is None or value == "":
        return None
    if value in {"True", "False"}:
        return value == "True"
    try:
        if "." in value or "e" in value.lower():
            return float(value)
        return int(value)
    except ValueError:
        return value
