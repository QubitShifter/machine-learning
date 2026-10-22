"""Orchestrate weather download processing, quality, and integration."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from ml.analysis.weather_timeseries import (
    read_daily_weather,
    write_daily_weather,
    write_monthly_summary,
    write_weather_chart,
)
from ml.ingestion.era5_land import (
    cds_auth_status,
    extract_hourly_records,
    partition_months,
)
from ml.ingestion.manifest import now_iso, read_manifest, save_manifest
from ml.ingestion.weather_config import load_weather_config
from ml.ingestion.weather_download import (
    download_weather_month,
    download_weather_range,
    empty_weather_manifest,
    plan_weather_downloads,
    weather_paths,
)
from ml.preprocessing.errors import WeatherDownloadError
from ml.integration.features import (
    INTEGRATION_VERSION,
    LEAKAGE_POLICY,
    SAME_DAY_POLICY,
    WINDOW_RULE,
    feature_metadata,
)
from ml.integration.satellite_weather import (
    default_integration_root,
    integrate_satellite_weather,
    load_validated_satellite_observations,
    source_fingerprint,
    write_integration_outputs,
)
from ml.integration.validate import validate_integrated_observations
from ml.preprocessing.errors import DatasetNotFoundError, MissingProcessedOutputError
from ml.preprocessing.raster import default_processed_root, read_json
from ml.preprocessing.weather import (
    ROLE_BOUNDARY,
    ROLE_OBSERVATION,
    aggregate_daily_weather,
    annotate_hourly_records,
    reconcile_hourly_records,
)
from ml.validation.weather_quality import (
    STATUS_REVIEW,
    build_quality_report,
    evaluate_daily_rows,
    evaluate_hourly_records,
    raise_status,
    spatial_selection_issue,
)


def check_weather_config(
    config_path: Path,
    *,
    cds_config_path: Path | None = None,
) -> dict[str, Any]:
    config = load_weather_config(config_path)
    auth = cds_auth_status(cds_config_path)
    return {
        "dataset_id": config["dataset_id"],
        "source": config["source"],
        "area": config["area"],
        "spatial": {
            "method": config["spatial"]["method"],
            "native_resolution_deg": config["spatial"]["native_resolution_deg"],
            "retrieval_area": list(config["spatial"]["retrieval_area"]),
        },
        "study_aoi": list(config["area"]["bbox"]),
        "retrieval_area": list(config["spatial"]["retrieval_area"]),
        "period": config["period"],
        "variables": config["variables"],
        "months": partition_months(config["period"]["start"], config["period"]["end"]),
        "authentication": {
            "configured": auth["configured"],
            "url_present": auth["url_present"],
            "key_present": auth["key_present"],
            "url_host": auth.get("url_host"),
            "message": auth["message"],
        },
    }


def weather_status(
    config_path: Path,
    *,
    start_month: str | None = None,
    end_month: str | None = None,
    raw_root: Path | None = None,
) -> dict[str, Any]:
    config = load_weather_config(config_path)
    return plan_weather_downloads(
        config,
        start_month=start_month,
        end_month=end_month,
        raw_root=raw_root,
    )


def download_weather(
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
    config = load_weather_config(config_path)
    if start_month or end_month:
        if month:
            raise WeatherDownloadError("Use either --month or --start-month/--end-month.")
        return download_weather_range(
            config,
            start_month=start_month or config["period"]["start"][:7],
            end_month=end_month or config["period"]["end"][:7],
            dry_run=dry_run,
            resume=resume,
            raw_root=raw_root,
            retrieve=retrieve,
            client_factory=client_factory,
        )
    if not month:
        raise WeatherDownloadError(
            "Specify --month for one request, or --start-month/--end-month "
            "for a sequential plan. Multi-month downloads require --dry-run "
            "or --resume."
        )
    return download_weather_month(
        config,
        month,
        dry_run=dry_run,
        raw_root=raw_root,
        retrieve=retrieve,
        client_factory=client_factory,
    )


def process_weather_dataset(
    config_path: Path,
    *,
    raw_root: Path | None = None,
    processed_root: Path | None = None,
    full_period: bool = False,
) -> dict[str, Any]:
    config = load_weather_config(config_path)
    paths = weather_paths(
        config["dataset_id"],
        raw_root=raw_root,
        processed_root=processed_root,
    )
    if not paths["raw_manifest"].is_file():
        raise DatasetNotFoundError(
            f"Unknown weather dataset: {config['dataset_id']}"
        )
    raw_manifest = read_manifest(paths["raw_manifest"])
    hours, spatial, downloaded_months, spatials, merge = _load_downloaded_hours(
        config, paths, raw_manifest
    )
    if not downloaded_months and not hours:
        raise MissingProcessedOutputError(
            "No downloaded weather months are available to process."
        )
    period_start, period_end = _process_period(config, downloaded_months, full_period)
    daily = aggregate_daily_weather(
        hours,
        period_start=period_start,
        period_end=period_end,
        aoi_id=config["area"]["name"],
        source_dataset=config["source"]["dataset"],
        spatial=spatial,
        require_complete_days=config["quality"]["require_complete_days"],
    )
    hourly_quality = evaluate_hourly_records(hours)
    hourly_quality["boundary_overlaps"] = merge["overlaps"]
    hourly_quality["expected_boundary_overlaps"] = len(merge["overlaps"])
    hourly_quality["boundary_only_timestamps"] = merge["boundary_only_timestamps"]
    extra_issues = []
    if merge["conflicts"]:
        extra_issues.append({
            "severity": STATUS_REVIEW,
            "code": "conflicting_boundary_overlap",
            "count": len(merge["conflicts"]),
            "records": merge["conflicts"],
        })
        hourly_quality["status"] = raise_status(hourly_quality["status"], STATUS_REVIEW)
        hourly_quality["conflicts"] = merge["conflicts"]
    daily_quality = evaluate_daily_rows(
        daily,
        require_complete_days=config["quality"]["require_complete_days"],
    )
    spatial_issue = spatial_selection_issue(spatials)
    if spatial_issue:
        extra_issues.append(spatial_issue)
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
    report = build_quality_report(
        dataset_id=config["dataset_id"],
        config=config,
        hourly=hourly_quality,
        daily=daily_quality,
        spatial=spatial,
        variables=config["variables"],
        coverage=coverage,
        extra_issues=extra_issues,
    )
    paths["processed"].mkdir(parents=True, exist_ok=True)
    outputs = write_daily_weather(daily_quality["days"], paths["processed"])
    monthly = write_monthly_summary(
        daily_quality["days"],
        paths["monthly_csv"],
        downloaded_months=downloaded_months,
    )
    write_weather_chart(daily_quality["days"], paths["chart"])
    from ml.ingestion.manifest import write_json_atomic

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
        "outputs": {
            **outputs,
            "monthly_csv": paths["monthly_csv"].name,
            "quality": paths["quality"].name,
            "chart": paths["chart"].name,
        },
        "updated_at": now_iso(),
    })
    save_manifest(paths["processed_manifest"], processed_manifest)
    return {
        "dataset_id": config["dataset_id"],
        "day_count": len(daily_quality["days"]),
        "complete_days": daily_quality["complete_days"],
        "quality_status": report["status"],
        "source_integrity": report.get("source_integrity"),
        "observation_validity": report.get("observation_validity"),
        "period_completeness": report.get("period_completeness"),
        "integration_readiness": report.get("integration_readiness"),
        "coverage": coverage,
        "outputs": processed_manifest["outputs"],
        "monthly": monthly,
    }


def validate_weather_dataset(
    config_path: Path,
    *,
    processed_root: Path | None = None,
) -> dict[str, Any]:
    config = load_weather_config(config_path)
    paths = weather_paths(config["dataset_id"], processed_root=processed_root)
    if not paths["quality"].is_file():
        raise MissingProcessedOutputError(
            "Weather quality report is not available yet."
        )
    from ml.preprocessing.raster import read_json

    return read_json(paths["quality"])


def report_weather_dataset(
    config_path: Path,
    *,
    processed_root: Path | None = None,
) -> dict[str, Any]:
    config = load_weather_config(config_path)
    paths = weather_paths(config["dataset_id"], processed_root=processed_root)
    if not paths["daily_csv"].is_file():
        raise MissingProcessedOutputError(
            "Daily weather table is not available yet."
        )
    rows = read_daily_weather(paths["daily_csv"])
    quality = validate_weather_dataset(config_path, processed_root=processed_root)
    downloaded = (quality.get("coverage") or {}).get("downloaded_months")
    monthly = write_monthly_summary(
        rows,
        paths["monthly_csv"],
        downloaded_months=downloaded,
    )
    if rows:
        write_weather_chart(rows, paths["chart"])
    return {
        "dataset_id": config["dataset_id"],
        "day_count": len(rows),
        "monthly": monthly,
        "quality_status": quality.get("status"),
        "source_integrity": quality.get("source_integrity"),
        "observation_validity": quality.get("observation_validity"),
        "period_completeness": quality.get("period_completeness"),
        "integration_readiness": quality.get("integration_readiness"),
        "completeness_pct": (quality.get("daily") or {}).get("completeness_pct"),
        "complete_days": (quality.get("daily") or {}).get("complete_days"),
        "missing_days": (quality.get("daily") or {}).get("missing_days"),
    }


def integrate_weather_dataset(
    config_path: Path,
    *,
    satellite_dataset_id: str,
    processed_root: Path | None = None,
    satellite_root: Path | None = None,
    integration_root: Path | None = None,
) -> dict[str, Any]:
    config = load_weather_config(config_path)
    paths = weather_paths(config["dataset_id"], processed_root=processed_root)
    if not paths["daily_csv"].is_file():
        raise MissingProcessedOutputError(
            "Daily weather table is not available yet."
        )
    weather_rows = read_daily_weather(paths["daily_csv"])
    sat_root = satellite_root or default_processed_root()
    sat_quality_path = sat_root / satellite_dataset_id / "quality" / "dataset_quality.json"
    sat_series_path = sat_root / satellite_dataset_id / "timeseries" / "ndvi_timeseries.json"
    weather_quality = _read_json_if_present(paths["quality"])
    processed_manifest = _read_json_if_present(paths["processed_manifest"])
    satellite_quality = _read_json_if_present(sat_quality_path)
    spatial = weather_quality.get("spatial") or processed_manifest.get("spatial") or {}
    training = satellite_quality.get("training_readiness") or {}
    windows = tuple(config["features"]["windows_days"])
    dry_day_mm = config["features"]["dry_day_precipitation_mm"]
    fingerprints = {
        "integration_version": INTEGRATION_VERSION,
        "daily_weather": source_fingerprint(paths["daily_csv"]),
        "weather_quality": source_fingerprint(paths["quality"]),
        "satellite_quality": source_fingerprint(sat_quality_path),
        "satellite_timeseries": source_fingerprint(sat_series_path),
        "dry_day_precipitation_mm": dry_day_mm,
        "windows_days": list(windows),
    }
    observations = load_validated_satellite_observations(
        satellite_dataset_id,
        processed_root=sat_root,
    )
    dropped: list[str] = []
    rows = integrate_satellite_weather(
        weather_rows,
        observations,
        weather_dataset_id=config["dataset_id"],
        satellite_dataset_id=satellite_dataset_id,
        aoi_id=config["area"]["name"],
        dry_day_mm=dry_day_mm,
        windows=windows,
        spatial=spatial,
        weather_integration_readiness=weather_quality.get("integration_readiness"),
        satellite_supervised_readiness=training.get("supervised_soil_forecasting"),
        duplicate_scene_ids=dropped,
    )
    target = (integration_root or default_integration_root()) / satellite_dataset_id
    previous = _read_json_if_present(target / "integration_metadata.json")
    previous_fingerprints = previous.get("source_fingerprints")
    sources_changed = previous_fingerprints != fingerprints
    quality = validate_integrated_observations(
        rows,
        weather_rows=weather_rows,
        windows=windows,
        source_fingerprints=fingerprints,
        previous_fingerprints=previous_fingerprints,
        dropped_duplicate_scene_ids=dropped,
        dry_day_mm=dry_day_mm,
    )
    created_at = now_iso()
    if previous.get("created_at") and not sources_changed:
        created_at = previous["created_at"]
    catalog = feature_metadata(dry_day_mm=dry_day_mm, windows=windows)
    quality.update({
        "satellite_dataset_id": satellite_dataset_id,
        "weather_dataset_id": config["dataset_id"],
        "aoi_id": config["area"]["name"],
        "leakage_policy": LEAKAGE_POLICY,
        "same_day_weather": SAME_DAY_POLICY,
        "window_rule": WINDOW_RULE,
        "weather_integration_readiness": weather_quality.get("integration_readiness"),
        "satellite_training_readiness": training or None,
        "weather_spatial": {
            key: spatial.get(key)
            for key in (
                "method",
                "source_longitude",
                "source_latitude",
                "distance_km",
                "native_resolution_deg",
                "query_longitude",
                "query_latitude",
                "study_aoi",
            )
            if key in spatial
        },
        "sources_changed": sources_changed,
        "created_at": created_at,
        "updated_at": now_iso(),
        "task_readiness": _task_readiness(satellite_quality, quality, weather_quality),
        "suitable_for_modeling_meaning": (
            "suitable_for_modeling is supervised soil-forecasting eligibility, "
            "not exploratory NDVI or vegetation forecasting."
        ),
    })
    metadata = {
        "satellite_dataset_id": satellite_dataset_id,
        "weather_dataset_id": config["dataset_id"],
        "aoi_id": config["area"]["name"],
        "observation_count": len(rows),
        "dry_day_precipitation_mm": dry_day_mm,
        "windows_days": list(windows),
        "integration_version": INTEGRATION_VERSION,
        "leakage_policy": LEAKAGE_POLICY,
        "same_day_weather": SAME_DAY_POLICY,
        "window_rule": WINDOW_RULE,
        "source_fingerprints": fingerprints,
        "sources_changed": sources_changed,
        "created_at": created_at,
        "updated_at": now_iso(),
        "satellite_observation_valid_count": quality.get("satellite_observation_valid_count"),
        "weather_feature_window_complete_count": quality.get("weather_feature_window_complete_count"),
        "integrated_observation_complete_count": quality.get("integrated_observation_complete_count"),
        "suitable_for_modeling_count": quality.get("suitable_for_modeling_count"),
        "weather_integration_readiness": weather_quality.get("integration_readiness"),
        "satellite_supervised_soil_forecasting": training.get("supervised_soil_forecasting"),
    }
    outputs = write_integration_outputs(
        rows,
        target,
        metadata=metadata,
        quality=quality,
        catalog=catalog,
    )
    return {
        "satellite_dataset_id": satellite_dataset_id,
        "weather_dataset_id": config["dataset_id"],
        "observation_count": len(rows),
        "outputs": outputs,
        "rows": rows,
        "quality": {
            "satellite_observation_valid_count": quality.get("satellite_observation_valid_count"),
            "weather_feature_window_complete_count": quality.get("weather_feature_window_complete_count"),
            "integrated_observation_complete_count": quality.get("integrated_observation_complete_count"),
            "suitable_for_modeling_count": quality.get("suitable_for_modeling_count"),
            "issue_count": len(quality.get("issues") or []),
        },
    }


def _task_readiness(
    satellite_quality: dict[str, Any],
    integration_quality: dict[str, Any],
    weather_quality: dict[str, Any],
) -> dict[str, Any]:
    from ml.validation.modeling_readiness import assess_task_readiness

    training = satellite_quality.get("training_readiness") or {}
    return assess_task_readiness(
        quality={
            **training,
            "coverage": satellite_quality.get("coverage") or {},
            "ground_truth_soil_moisture_available": False,
        },
        integration_metrics={
            "complete_window_count": int(
                integration_quality.get("weather_feature_window_complete_count") or 0
            ),
            "observation_count": int(integration_quality.get("observation_count") or 0),
            "weather_integration_readiness": weather_quality.get("integration_readiness"),
        },
    )


def _read_json_if_present(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return read_json(path)
    except Exception:
        return {}


def _load_downloaded_hours(
    config: dict[str, Any],
    paths: dict[str, Path],
    manifest: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, list[str], list[dict[str, Any]], dict[str, Any]]:
    hours: list[dict[str, Any]] = []
    spatial = None
    spatials: list[dict[str, Any]] = []
    months = []
    bbox = tuple(config["area"]["bbox"])
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
        hours.extend(annotate_hourly_records(
            records,
            month=month,
            filename=filename,
            role=ROLE_OBSERVATION,
            spatial=extracted,
        ))
        spatial = extracted
        spatials.append(extracted)
        boundary = record.get("boundary_filename")
        if boundary:
            boundary_path = paths["hourly"] / boundary
            if boundary_path.is_file():
                extra, _ = extract_hourly_records(boundary_path, bbox=bbox)
                hours.extend(annotate_hourly_records(
                    extra,
                    month=month,
                    filename=boundary,
                    role=ROLE_BOUNDARY,
                    spatial=extracted,
                ))
        months.append(month)
    merge = reconcile_hourly_records(hours, downloaded_months=months)
    return merge["records"], spatial, months, spatials, merge


def _process_period(
    config: dict[str, Any],
    downloaded_months: list[str],
    full_period: bool,
) -> tuple[date, date]:
    if full_period or not downloaded_months:
        return (
            date.fromisoformat(config["period"]["start"]),
            date.fromisoformat(config["period"]["end"]),
        )
    first = downloaded_months[0]
    last = downloaded_months[-1]
    year, month = (int(part) for part in last.split("-"))
    from calendar import monthrange

    return (
        date.fromisoformat(f"{first}-01"),
        date(year, month, monthrange(year, month)[1]),
    )
