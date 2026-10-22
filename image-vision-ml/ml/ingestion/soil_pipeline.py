"""Orchestrate ERA5-Land soil-water download, processing, and wetness features."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from ml.analysis.soil_timeseries import (
    read_daily_soil,
    write_daily_soil,
    write_monthly_soil_summary,
    write_soil_chart,
)
from ml.analysis.weather_timeseries import read_daily_weather, write_daily_weather
from ml.ingestion.era5_land import cds_auth_status, extract_hourly_records, partition_months
from ml.ingestion.manifest import now_iso, read_manifest, save_manifest, write_json_atomic
from ml.ingestion.soil_config import load_soil_config
from ml.ingestion.weather_config import load_weather_config
from ml.ingestion.weather_download import (
    default_weather_processed_root,
    download_weather_month,
    download_weather_range,
    empty_weather_manifest,
    plan_weather_downloads,
    weather_paths,
)
from ml.ingestion.weather_pipeline import _process_period
from ml.preprocessing.errors import DatasetNotFoundError, MissingProcessedOutputError
from ml.preprocessing.raster import project_root, read_json
from ml.preprocessing.soil import (
    OBSERVATION_KIND,
    SOIL_PROCESSING_VERSION,
    aggregate_daily_soil,
    compare_spatial_selection,
)
from ml.preprocessing.weather import ROLE_OBSERVATION, annotate_hourly_records
from ml.preprocessing.wetness import WETNESS_VERSION, attach_wetness_features
from ml.validation.soil_quality import (
    build_soil_quality_report,
    evaluate_daily_soil,
    evaluate_hourly_soil,
)
from ml.validation.weather_quality import spatial_selection_issue


def default_soil_raw_root() -> Path:
    return project_root() / "data" / "raw" / "soil"


def default_soil_processed_root() -> Path:
    return project_root() / "data" / "processed" / "soil"


def default_wetness_processed_root() -> Path:
    return project_root() / "data" / "processed" / "wetness"


def soil_paths(
    dataset_id: str,
    *,
    raw_root: Path | None = None,
    processed_root: Path | None = None,
) -> dict[str, Path]:
    paths = weather_paths(
        dataset_id,
        raw_root=raw_root or default_soil_raw_root(),
        processed_root=processed_root or default_soil_processed_root(),
    )
    processed = paths["processed"]
    paths["daily_csv"] = processed / "daily_soil.csv"
    paths["daily_parquet"] = processed / "daily_soil.parquet"
    paths["monthly_csv"] = processed / "monthly_summary.csv"
    paths["chart"] = processed / "soil_timeseries.png"
    paths["chart_data"] = processed / "soil_chart_data.json"
    paths["quality"] = processed / "quality_report.json"
    return paths


def check_soil_config(
    config_path: Path,
    *,
    cds_config_path: Path | None = None,
) -> dict[str, Any]:
    config = load_soil_config(config_path)
    auth = cds_auth_status(cds_config_path)
    return {
        "dataset_id": config["dataset_id"],
        "source": config["source"],
        "area": config["area"],
        "spatial": {
            "method": config["spatial"]["method"],
            "native_resolution_deg": config["spatial"]["native_resolution_deg"],
            "retrieval_area": list(config["spatial"]["retrieval_area"]),
            "reference_weather_dataset_id": config["spatial"]["reference_weather_dataset_id"],
        },
        "study_aoi": list(config["area"]["bbox"]),
        "retrieval_area": list(config["spatial"]["retrieval_area"]),
        "period": config["period"],
        "variables": config["variables"],
        "layers": config["layers"],
        "include_next_day_boundary": config["downloads"]["include_next_day_boundary"],
        "observation_kind": OBSERVATION_KIND,
        "processing_version": SOIL_PROCESSING_VERSION,
        "months": partition_months(config["period"]["start"], config["period"]["end"]),
        "authentication": {
            "configured": auth["configured"],
            "url_present": auth["url_present"],
            "key_present": auth["key_present"],
            "url_host": auth.get("url_host"),
            "message": auth["message"],
        },
    }


def soil_status(
    config_path: Path,
    *,
    start_month: str | None = None,
    end_month: str | None = None,
    raw_root: Path | None = None,
) -> dict[str, Any]:
    config = load_soil_config(config_path)
    return plan_weather_downloads(
        config,
        start_month=start_month,
        end_month=end_month,
        raw_root=raw_root or default_soil_raw_root(),
    )


def download_soil(
    config_path: Path,
    *,
    month: str | None = None,
    start_month: str | None = None,
    end_month: str | None = None,
    dry_run: bool = False,
    resume: bool = False,
    raw_root: Path | None = None,
    retrieve=None,
    client_factory=None,
) -> dict[str, Any]:
    config = load_soil_config(config_path)
    root = raw_root or default_soil_raw_root()
    if month:
        result = download_weather_month(
            config,
            month,
            dry_run=dry_run,
            raw_root=root,
            retrieve=retrieve,
            client_factory=client_factory,
        )
        result["include_next_day_boundary"] = False
        result["observation_kind"] = OBSERVATION_KIND
        return result
    return download_weather_range(
        config,
        start_month=start_month or config["period"]["start"][:7],
        end_month=end_month or config["period"]["end"][:7],
        dry_run=dry_run,
        resume=resume,
        raw_root=root,
        retrieve=retrieve,
        client_factory=client_factory,
    )


def process_soil_dataset(
    config_path: Path,
    *,
    raw_root: Path | None = None,
    processed_root: Path | None = None,
    weather_processed_root: Path | None = None,
    full_period: bool = False,
) -> dict[str, Any]:
    config = load_soil_config(config_path)
    paths = soil_paths(
        config["dataset_id"],
        raw_root=raw_root,
        processed_root=processed_root,
    )
    if not paths["raw_manifest"].is_file():
        raise DatasetNotFoundError(f"Unknown soil dataset: {config['dataset_id']}")
    raw_manifest = read_manifest(paths["raw_manifest"])
    hours, spatial, downloaded_months, spatials = _load_downloaded_soil_hours(
        config, paths, raw_manifest
    )
    if not downloaded_months and not hours:
        raise MissingProcessedOutputError(
            "No downloaded soil-water months are available to process."
        )
    period_start, period_end = _process_period(config, downloaded_months, full_period)
    quality_cfg = config["quality"]
    daily = aggregate_daily_soil(
        hours,
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        aoi_id=config["area"]["name"],
        source_dataset=config["source"]["dataset"],
        spatial=spatial,
        require_complete_days=quality_cfg["require_complete_days"],
        field_capacity=quality_cfg.get("field_capacity"),
        wilting_point=quality_cfg.get("wilting_point"),
    )
    hourly_quality = evaluate_hourly_soil(hours)
    daily_quality = evaluate_daily_soil(
        daily,
        require_complete_days=quality_cfg["require_complete_days"],
    )
    extra_issues = []
    spatial_issue = spatial_selection_issue(spatials)
    if spatial_issue:
        extra_issues.append(spatial_issue)
    weather_spatial = _weather_spatial(
        config["spatial"]["reference_weather_dataset_id"],
        weather_processed_root,
    )
    grid_comparison = compare_spatial_selection(spatial, weather_spatial)
    expected_months = partition_months(config["period"]["start"], config["period"]["end"])
    missing_months = [month for month in expected_months if month not in downloaded_months]
    coverage = {
        "expected_months": expected_months,
        "downloaded_months": downloaded_months,
        "missing_months": missing_months,
        "month_availability": {
            month: ("downloaded" if month in downloaded_months else "missing_source")
            for month in expected_months
        },
        "expected_days": (
            date.fromisoformat(config["period"]["end"])
            - date.fromisoformat(config["period"]["start"])
        ).days + 1,
        "processed_start": period_start.isoformat(),
        "processed_end": period_end.isoformat(),
    }
    report = build_soil_quality_report(
        dataset_id=config["dataset_id"],
        config=config,
        hourly=hourly_quality,
        daily=daily_quality,
        spatial=spatial,
        coverage=coverage,
        extra_issues=extra_issues,
        weather_spatial=weather_spatial,
        grid_comparison=grid_comparison,
    )
    paths["processed"].mkdir(parents=True, exist_ok=True)
    outputs = write_daily_soil(daily_quality["days"], paths["processed"])
    monthly = write_monthly_soil_summary(
        daily_quality["days"],
        paths["monthly_csv"],
        downloaded_months=downloaded_months,
    )
    chart = write_soil_chart(daily_quality["days"], paths["chart"])
    if chart is not None:
        outputs["chart"] = paths["chart"].name
    write_json_atomic(paths["quality"], report)
    processed_manifest = empty_weather_manifest(config)
    processed_manifest.update({
        "spatial": spatial,
        "period_processed": {
            "start": period_start.isoformat(),
            "end": period_end.isoformat(),
        },
        "day_count": len(daily_quality["days"]),
        "complete_days": daily_quality["complete_days"],
        "quality_status": report["status"],
        "observation_kind": OBSERVATION_KIND,
        "is_ground_truth": False,
        "processing_version": SOIL_PROCESSING_VERSION,
        "parquet_generated": bool(outputs.get("parquet_generated")),
        "outputs": {
            **outputs,
            "monthly_csv": paths["monthly_csv"].name,
            "quality": paths["quality"].name,
        },
        "updated_at": now_iso(),
    })
    save_manifest(paths["processed_manifest"], processed_manifest)
    return {
        "dataset_id": config["dataset_id"],
        "day_count": len(daily_quality["days"]),
        "complete_days": daily_quality["complete_days"],
        "quality_status": report["status"],
        "observation_kind": OBSERVATION_KIND,
        "is_ground_truth": False,
        "suitable_for_modeling": False,
        "modeled_soil_readiness": report.get("modeled_soil_readiness"),
        "grid_comparison": grid_comparison,
        "coverage": coverage,
        "outputs": processed_manifest["outputs"],
        "parquet_generated": bool(outputs.get("parquet_generated")),
        "monthly": monthly,
        "processing_version": SOIL_PROCESSING_VERSION,
    }


def validate_soil_dataset(
    config_path: Path,
    *,
    processed_root: Path | None = None,
) -> dict[str, Any]:
    config = load_soil_config(config_path)
    paths = soil_paths(config["dataset_id"], processed_root=processed_root)
    if not paths["quality"].is_file():
        raise MissingProcessedOutputError("Soil quality report is not available yet.")
    return read_json(paths["quality"])


def report_soil_dataset(
    config_path: Path,
    *,
    processed_root: Path | None = None,
) -> dict[str, Any]:
    config = load_soil_config(config_path)
    paths = soil_paths(config["dataset_id"], processed_root=processed_root)
    if not paths["daily_csv"].is_file():
        raise MissingProcessedOutputError("Daily soil table is not available yet.")
    rows = read_daily_soil(paths["daily_csv"])
    quality = validate_soil_dataset(config_path, processed_root=processed_root)
    downloaded = (quality.get("coverage") or {}).get("downloaded_months")
    monthly = write_monthly_soil_summary(
        rows,
        paths["monthly_csv"],
        downloaded_months=downloaded,
    )
    write_soil_chart(rows, paths["chart"])
    return {
        "dataset_id": config["dataset_id"],
        "day_count": len(rows),
        "complete_days": (quality.get("daily") or {}).get("complete_days"),
        "quality_status": quality.get("status"),
        "observation_kind": quality.get("observation_kind"),
        "is_ground_truth": False,
        "suitable_for_modeling": False,
        "monthly": monthly,
        "grid_comparison": quality.get("grid_comparison"),
        "modeled_soil_readiness": quality.get("modeled_soil_readiness"),
        "parquet_generated": bool((read_manifest(paths["processed_manifest"]) if paths["processed_manifest"].is_file() else {}).get("parquet_generated")),
    }


def generate_wetness_dataset(
    weather_config_path: Path,
    *,
    processed_root: Path | None = None,
    output_root: Path | None = None,
) -> dict[str, Any]:
    config = load_weather_config(weather_config_path)
    weather = weather_paths(
        config["dataset_id"],
        processed_root=processed_root or default_weather_processed_root(),
    )
    if not weather["daily_csv"].is_file():
        raise MissingProcessedOutputError("Daily weather table is not available yet.")
    rows = read_daily_weather(weather["daily_csv"])
    enriched = attach_wetness_features(
        rows,
        dry_day_mm=float(config["features"]["dry_day_precipitation_mm"]),
    )
    target = (output_root or default_wetness_processed_root()) / config["dataset_id"]
    target.mkdir(parents=True, exist_ok=True)
    from ml.analysis.weather_timeseries import _write_csv, _write_parquet

    columns = _wetness_columns(enriched)
    csv_path = target / "wetness_indicators.csv"
    _write_csv(csv_path, enriched, columns)
    parquet_generated = _write_parquet(enriched, target / "wetness_indicators.parquet")
    metadata = {
        "weather_dataset_id": config["dataset_id"],
        "wetness_version": WETNESS_VERSION,
        "observation_kinds": [
            "rainfall_history_indicator",
            "weather_derived_wetness_proxy",
        ],
        "is_measured_soil_moisture": False,
        "is_modeled_soil_moisture": False,
        "water_balance_status": "not_estimated",
        "row_count": len(enriched),
        "parquet_generated": parquet_generated,
        "dry_day_precipitation_mm": config["features"]["dry_day_precipitation_mm"],
        "updated_at": now_iso(),
    }
    write_json_atomic(target / "wetness_metadata.json", metadata)
    return {
        "weather_dataset_id": config["dataset_id"],
        "row_count": len(enriched),
        "output_csv": str(csv_path),
        "parquet_generated": parquet_generated,
        "wetness_version": WETNESS_VERSION,
        "metadata": metadata,
    }


def _load_downloaded_soil_hours(
    config: dict[str, Any],
    paths: dict[str, Path],
    manifest: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, list[str], list[dict[str, Any]]]:
    hours: list[dict[str, Any]] = []
    spatial = None
    spatials: list[dict[str, Any]] = []
    months: list[str] = []
    bbox = tuple(config["area"]["bbox"])
    seen: set[str] = set()
    for month, record in sorted((manifest.get("months") or {}).items()):
        if record.get("status") != "downloaded":
            continue
        filename = record.get("filename")
        if not filename:
            continue
        path = paths["hourly"] / filename
        if not path.is_file():
            continue
        records, extracted = extract_hourly_records(path, bbox=bbox)
        annotated = annotate_hourly_records(
            records,
            month=month,
            filename=filename,
            role=ROLE_OBSERVATION,
            spatial=extracted,
        )
        for item in annotated:
            stamp = str(item.get("timestamp_utc") or "")
            if stamp in seen:
                item = dict(item)
                item["duplicate_timestamp"] = True
            seen.add(stamp)
            hours.append(item)
        spatial = extracted
        spatials.append(extracted)
        months.append(month)
    return hours, spatial, months, spatials


def _weather_spatial(
    weather_dataset_id: str,
    weather_processed_root: Path | None,
) -> dict[str, Any] | None:
    root = weather_processed_root or default_weather_processed_root()
    quality_path = root / weather_dataset_id / "quality_report.json"
    if not quality_path.is_file():
        return None
    try:
        payload = read_json(quality_path)
    except Exception:
        return None
    spatial = payload.get("spatial")
    return spatial if isinstance(spatial, dict) else None


def _wetness_columns(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key in seen or key == "spatial":
                continue
            seen.add(key)
            keys.append(key)
    preferred = [
        "date_utc",
        "precipitation_total_mm",
        "api_k085_mm",
        "api_k090_mm",
        "api_k095_mm",
        "consecutive_dry_days",
        "days_since_rain",
        "precip_prev_7d_mm",
        "precip_trailing_7d_end_of_day_mm",
        "precip_minus_evap_7d_mm",
        "water_balance_status",
    ]
    ordered = [key for key in preferred if key in seen]
    ordered.extend(key for key in keys if key not in ordered)
    return tuple(ordered)
