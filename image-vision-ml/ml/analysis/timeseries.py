"""Aggregate scene-level NDVI measurements into a chronological series."""

from __future__ import annotations

import csv
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from ml.ingestion.manifest import write_json_atomic


logger = logging.getLogger(__name__)

GROWING_SEASON_MONTHS = (4, 5, 6, 7, 8, 9)
AGGREGATION_NOTES = (
    "Monthly and yearly summaries weight each observation equally. "
    "They are not pixel-weighted monthly climatologies and do not "
    "represent an unbiased month-long mean when sampling is uneven."
)


def build_ndvi_timeseries(
    observations: list[dict[str, Any]],
    *,
    deduplicate_by_date: bool = True,
    include_partial_coverage: bool = True,
    validated_scene_ids: set[str] | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
) -> dict[str, Any]:
    """Create chronological NDVI observations and change summaries.

    Missing months are listed, not interpolated. Partial-coverage means
    are retained as observations and flagged; they are not treated as
    equivalent to full-area means.
    """
    cleaned = [_normalize_observation(item) for item in observations]
    cleaned = [item for item in cleaned if item["date"]]
    if validated_scene_ids is not None:
        cleaned = [
            item for item in cleaned
            if item.get("scene_id") in validated_scene_ids
        ]
    if not include_partial_coverage:
        cleaned = [item for item in cleaned if not item.get("partial_coverage")]
    cleaned.sort(key=lambda item: (item["date"], item["scene_id"] or ""))
    if deduplicate_by_date:
        cleaned = _drop_duplicate_dates(cleaned)

    consecutive = []
    for earlier, later in zip(cleaned, cleaned[1:]):
        if earlier["mean"] is None or later["mean"] is None:
            continue
        change = later["mean"] - earlier["mean"]
        consecutive.append({
            "from_date": earlier["date"],
            "to_date": later["date"],
            "from_scene_id": earlier["scene_id"],
            "to_scene_id": later["scene_id"],
            "absolute_change": change,
            "direction": (
                "increase" if change > 0
                else "decrease" if change < 0
                else "unchanged"
            ),
            "partial_coverage": bool(
                earlier.get("partial_coverage") or later.get("partial_coverage")
            ),
        })

    monthly = monthly_ndvi_summary(cleaned)
    yearly = yearly_ndvi_summary(cleaned)
    comparison = interannual_comparison(cleaned)
    observed_months = {item["month"] for item in monthly}
    missing_months = _missing_months(
        cleaned,
        observed_months,
        period_start=period_start,
        period_end=period_end,
    )

    return {
        "metric": "ndvi",
        "observations": cleaned,
        "consecutive_changes": consecutive,
        "monthly": monthly,
        "yearly": yearly,
        "comparison": comparison,
        "missing_months": missing_months,
        "observation_count": len(cleaned),
        "aggregation": {
            "method": "equal_scene_weight",
            "notes": AGGREGATION_NOTES,
        },
        "quality": {
            "partial_coverage_observations": sum(
                1 for item in cleaned if item.get("partial_coverage")
            ),
            "zero_valid_pixel_observations": sum(
                1 for item in cleaned if (item.get("valid_pixels") or 0) == 0
            ),
        },
    }


def monthly_ndvi_summary(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate observation-level statistics by calendar month."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in observations:
        if not item.get("date"):
            continue
        grouped[item["date"][:7]].append(item)
    monthly = []
    for month in sorted(grouped):
        items = grouped[month]
        means = [value for value in (_maybe_float(item.get("mean")) for item in items) if value is not None]
        medians = [value for value in (_maybe_float(item.get("median")) for item in items) if value is not None]
        minima = [value for value in (_maybe_float(item.get("minimum")) for item in items) if value is not None]
        maxima = [value for value in (_maybe_float(item.get("maximum")) for item in items) if value is not None]
        coverage = [
            value for value in (_maybe_float(item.get("valid_percentage")) for item in items)
            if value is not None
        ]
        monthly.append({
            "month": month,
            "year": month[:4],
            "calendar_month": month[5:7],
            "observation_count": len(items),
            "mean": _mean(means),
            "median_of_medians": _median(medians),
            "minimum": min(minima) if minima else None,
            "maximum": max(maxima) if maxima else None,
            "valid_pixel_percentage": _mean(coverage),
            "available_dates": [item["date"] for item in items],
            "partial_coverage": any(item.get("partial_coverage") for item in items),
        })
    return monthly


def yearly_ndvi_summary(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in observations:
        if not item.get("date"):
            continue
        grouped[item["date"][:4]].append(item)
    yearly = []
    for year in sorted(grouped):
        items = grouped[year]
        means = [value for value in (_maybe_float(item.get("mean")) for item in items) if value is not None]
        monthly_keys = {item["date"][:7] for item in items}
        growing = [
            item for item in items
            if _month_number(item["date"]) in GROWING_SEASON_MONTHS
            and item.get("mean") is not None
        ]
        yearly.append({
            "year": year,
            "observation_count": len(items),
            "mean": _mean(means),
            "minimum": min(means) if means else None,
            "maximum": max(means) if means else None,
            "annual_minimum_observed": min(means) if means else None,
            "annual_maximum_observed": max(means) if means else None,
            "growing_season_mean": _mean([item["mean"] for item in growing]),
            "growing_season_observation_count": len(growing),
            "months_with_observations": len(monthly_keys),
            "available_dates": [item["date"] for item in items],
        })
    return yearly


def interannual_comparison(observations: list[dict[str, Any]]) -> dict[str, Any]:
    """Group observations by calendar month across years for charting."""
    by_month: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    years: set[str] = set()
    for item in observations:
        date = item.get("date") or ""
        if len(date) < 7 or item.get("mean") is None:
            continue
        year = date[:4]
        month = date[5:7]
        years.add(year)
        by_month[month][year].append(item)

    months = []
    for month in [f"{index:02d}" for index in range(1, 13)]:
        year_values = {}
        for year in sorted(years):
            items = by_month.get(month, {}).get(year, [])
            means = [item["mean"] for item in items if item.get("mean") is not None]
            year_values[year] = {
                "observation_count": len(items),
                "mean": _mean(means),
                "dates": [item["date"] for item in items],
            }
        months.append({
            "calendar_month": month,
            "years": year_values,
        })

    growing = []
    for year in sorted(years):
        values = [
            item["mean"]
            for item in observations
            if item.get("date", "").startswith(year)
            and _month_number(item.get("date") or "") in GROWING_SEASON_MONTHS
            and item.get("mean") is not None
        ]
        growing.append({
            "year": year,
            "growing_season_mean": _mean(values),
            "observation_count": len(values),
        })

    return {
        "years": sorted(years),
        "months": months,
        "growing_season": growing,
        "notes": (
            "Descriptive comparison only. A three-year NDVI record is not "
            "evidence of climate change, drought, or soil degradation."
        ),
    }


def write_timeseries_outputs(
    payload: dict[str, Any],
    output_dir: Path,
    *,
    title: str = "NDVI time series",
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "ndvi_timeseries.json"
    csv_path = output_dir / "ndvi_timeseries.csv"
    observations_csv = output_dir / "ndvi_observations.csv"
    observations_json = output_dir / "ndvi_observations.json"
    monthly_csv = output_dir / "ndvi_monthly.csv"
    png_path = output_dir / "ndvi_timeseries.png"
    by_year_path = output_dir / "ndvi_by_year.png"
    coverage_path = output_dir / "coverage_report.png"
    write_json_atomic(json_path, payload)
    write_json_atomic(observations_json, {
        "dataset_id": payload.get("dataset_id"),
        "observations": payload["observations"],
    })
    _write_csv(csv_path, payload["observations"])
    _write_csv(observations_csv, payload["observations"])
    _write_monthly_csv(monthly_csv, payload.get("monthly") or [])
    save_ndvi_timeseries_chart(payload["observations"], png_path, title=title)
    save_ndvi_by_year_chart(payload.get("comparison") or interannual_comparison(payload["observations"]), by_year_path)
    save_coverage_report_chart(payload["observations"], coverage_path)
    return {
        "json": json_path.name,
        "csv": csv_path.name,
        "png": png_path.name,
        "observations_csv": observations_csv.name,
        "observations_json": observations_json.name,
        "monthly_csv": monthly_csv.name,
        "by_year_png": by_year_path.name,
        "coverage_png": coverage_path.name,
    }


def save_ndvi_timeseries_chart(
    observations: list[dict[str, Any]],
    path: Path,
    *,
    title: str = "NDVI time series",
) -> None:
    dated = [
        item for item in observations
        if item.get("date") and item.get("mean") is not None
    ]
    figure, axes = plt.subplots(
        2, 1, figsize=(10, 7), sharex=True,
        gridspec_kw={"height_ratios": [2, 1]},
    )
    if dated:
        dates = [datetime.fromisoformat(item["date"]) for item in dated]
        means = [item["mean"] for item in dated]
        coverage = [item.get("valid_percentage") or 0 for item in dated]
        axes[0].plot(dates, means, color="#2e7d32", linewidth=1.4)
        axes[0].scatter(dates, means, color="#1b5e20", zorder=3)
        axes[1].bar(dates, coverage, color="#90caf9", width=8)
    axes[0].set_ylabel("Mean NDVI")
    axes[0].set_title(f"{title} (n={len(dated)} valid scenes)")
    axes[0].set_ylim(-0.2, 1.0)
    axes[1].set_ylabel("Valid NDVI %")
    axes[1].set_xlabel("Acquisition date")
    axes[1].set_ylim(0, 100)
    figure.autofmt_xdate()
    figure.tight_layout()
    _save_figure(figure, path)


def save_ndvi_by_year_chart(comparison: dict[str, Any], path: Path) -> None:
    years = comparison.get("years") or []
    months = comparison.get("months") or []
    figure, axis = plt.subplots(figsize=(10, 5))
    x_values = list(range(1, 13))
    colors = ["#1b5e20", "#1565c0", "#ef6c00", "#6a1b9a"]
    for index, year in enumerate(years):
        values = []
        for month in months:
            year_block = (month.get("years") or {}).get(year) or {}
            values.append(year_block.get("mean"))
        axis.plot(
            x_values,
            values,
            marker="o",
            label=str(year),
            color=colors[index % len(colors)],
        )
    axis.set_xticks(x_values)
    axis.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    axis.set_ylabel("Mean NDVI")
    axis.set_ylim(-0.2, 1.0)
    axis.set_title("Interannual NDVI by calendar month")
    if years:
        axis.legend()
    axis.set_xlabel("Month")
    figure.tight_layout()
    _save_figure(figure, path)


def save_coverage_report_chart(observations: list[dict[str, Any]], path: Path) -> None:
    dated = [item for item in observations if item.get("date")]
    figure, axis = plt.subplots(figsize=(10, 4))
    if dated:
        dates = [datetime.fromisoformat(item["date"]) for item in dated]
        coverage = [item.get("valid_percentage") or 0 for item in dated]
        colors = [
            "#c62828" if (item.get("valid_percentage") or 0) < 70
            else "#f9a825" if item.get("partial_coverage")
            else "#2e7d32"
            for item in dated
        ]
        axis.bar(dates, coverage, color=colors, width=8)
    axis.set_ylim(0, 100)
    axis.set_ylabel("Valid NDVI %")
    axis.set_xlabel("Acquisition date")
    axis.set_title(f"Observation coverage (n={len(dated)})")
    figure.autofmt_xdate()
    figure.tight_layout()
    _save_figure(figure, path)


def _normalize_observation(item: dict[str, Any]) -> dict[str, Any]:
    date = str(item.get("date") or item.get("acquisition_date") or "")[:10]
    valid_percentage = item.get("valid_percentage")
    aoi_coverage = item.get("aoi_coverage")
    partial = bool(
        item.get("partial_coverage")
        or (aoi_coverage is not None and float(aoi_coverage) < 99.0)
    )
    return {
        "scene_id": item.get("scene_id"),
        "date": date,
        "mean": _maybe_float(item.get("mean")),
        "median": _maybe_float(item.get("median")),
        "standard_deviation": _maybe_float(
            item.get("standard_deviation") or item.get("std")
        ),
        "minimum": _maybe_float(item.get("minimum") or item.get("min")),
        "maximum": _maybe_float(item.get("maximum") or item.get("max")),
        "valid_pixels": item.get("valid_pixels"),
        "total_pixels": item.get("total_pixels"),
        "valid_percentage": _maybe_float(valid_percentage),
        "cloud_cover": _maybe_float(item.get("cloud_cover")),
        "aoi_coverage": _maybe_float(aoi_coverage),
        "partial_coverage": partial,
        "quality_status": item.get("quality_status"),
    }


def _drop_duplicate_dates(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep one observation per date, preferring higher valid-pixel percentage."""
    best: dict[str, dict[str, Any]] = {}
    for item in observations:
        current = best.get(item["date"])
        if current is None:
            best[item["date"]] = item
            continue
        current_score = current.get("valid_percentage") or -1
        new_score = item.get("valid_percentage") or -1
        if new_score > current_score:
            best[item["date"]] = item
    return [best[key] for key in sorted(best)]


def _monthly_means(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return monthly_ndvi_summary(
        [item for item in observations if item.get("mean") is not None]
    )


def _missing_months(
    observations: list[dict[str, Any]],
    observed: set[str],
    period_start: str | None = None,
    period_end: str | None = None,
) -> list[str]:
    dates = [item["date"] for item in observations if item.get("date")]
    start_text = (period_start or (min(dates) if dates else ""))[:7]
    end_text = (period_end or (max(dates) if dates else ""))[:7]
    if len(start_text) < 7 or len(end_text) < 7:
        return []
    start = datetime.fromisoformat(start_text + "-01")
    end = datetime.fromisoformat(end_text + "-01")
    missing = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        key = f"{year:04d}-{month:02d}"
        if key not in observed:
            missing.append(key)
        month += 1
        if month == 13:
            year += 1
            month = 1
    return missing


def _write_csv(path: Path, observations: list[dict[str, Any]]) -> None:
    fieldnames = [
        "date",
        "scene_id",
        "mean",
        "median",
        "standard_deviation",
        "minimum",
        "maximum",
        "valid_pixels",
        "valid_percentage",
        "cloud_cover",
        "aoi_coverage",
        "partial_coverage",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(observations)


def _write_monthly_csv(path: Path, monthly: list[dict[str, Any]]) -> None:
    fieldnames = [
        "month",
        "observation_count",
        "mean",
        "median_of_medians",
        "minimum",
        "maximum",
        "valid_pixel_percentage",
        "available_dates",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for item in monthly:
            row = dict(item)
            row["available_dates"] = ";".join(item.get("available_dates") or [])
            writer.writerow(row)


def _save_figure(figure, path: Path) -> None:
    temporary = path.with_name(f".{path.stem}.tmp{path.suffix}")
    try:
        figure.savefig(temporary, dpi=140, bbox_inches="tight")
        temporary.replace(path)
    finally:
        plt.close(figure)
        if temporary.exists():
            temporary.unlink()


def _maybe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return float(sum(values) / len(values))


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return float((ordered[mid - 1] + ordered[mid]) / 2)


def _month_number(date: str) -> int:
    try:
        return int(date[5:7])
    except (TypeError, ValueError):
        return 0
