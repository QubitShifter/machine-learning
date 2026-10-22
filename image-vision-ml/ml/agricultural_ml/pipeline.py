"""Build, validate and audit the agricultural ML research dataset."""

from __future__ import annotations

import math
import statistics
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from ml.agricultural_ml.baselines import baseline_catalog
from ml.agricultural_ml.catalog import feature_catalog, target_catalog
from ml.agricultural_ml.config import (
    PIPELINE_VERSION,
    load_ml_config,
    output_directory,
)
from ml.agricultural_ml.features import build_daily_features, index_by_date
from ml.agricultural_ml.leakage import run_leakage_audit
from ml.agricultural_ml.readiness import assess_agricultural_ml_readiness
from ml.agricultural_ml.satellite import load_eligible_satellite_observations, satellite_by_issue_date
from ml.agricultural_ml.splits import build_split_membership
from ml.agricultural_ml.targets import build_targets, wide_targets
from ml.agricultural_ml.time_semantics import daterange, parse_utc_date
from ml.analysis.soil_timeseries import read_daily_soil
from ml.analysis.weather_timeseries import _write_csv, _write_parquet, read_daily_weather
from ml.ingestion.manifest import now_iso, write_json_atomic
from ml.ingestion.soil_pipeline import default_soil_processed_root, soil_paths
from ml.ingestion.weather_download import default_weather_processed_root, weather_paths
from ml.integration.satellite_weather import source_fingerprint
from ml.preprocessing.errors import AgriculturalMlError, MissingProcessedOutputError
from ml.preprocessing.raster import project_root, read_json


def check_config(config_path: Path | str, *, root: Path | None = None) -> dict[str, Any]:
    config = load_ml_config(config_path)
    base = root or project_root()
    weather = weather_paths(config["sources"]["weather_dataset_id"], processed_root=default_weather_processed_root())
    soil = soil_paths(config["sources"]["soil_dataset_id"], processed_root=default_soil_processed_root())
    missing = [
        str(path) for path in (weather["daily_csv"], soil["daily_csv"])
        if not Path(path).is_file()
    ]
    return {
        "dataset_id": config["dataset_id"],
        "pipeline_version": config["pipeline_version"],
        "config_fingerprint": config["_config_fingerprint"],
        "research_mode": config["issue_time"]["research_mode"],
        "operational_availability_verified": False,
        "source_files_missing": missing,
        "ok": not missing,
        "network_used": False,
    }


def build_dataset(
    config_path: Path | str,
    *,
    root: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    config = load_ml_config(config_path)
    base = root or project_root()
    weather_id = config["sources"]["weather_dataset_id"]
    soil_id = config["sources"]["soil_dataset_id"]
    satellite_id = config["sources"]["satellite_dataset_id"]
    weather = weather_paths(weather_id, processed_root=default_weather_processed_root())
    soil = soil_paths(soil_id, processed_root=default_soil_processed_root())
    if not weather["daily_csv"].is_file() or not soil["daily_csv"].is_file():
        raise MissingProcessedOutputError("Daily weather and soil CSVs are required; none were downloaded.")
    weather_rows = read_daily_weather(weather["daily_csv"])
    soil_rows = read_daily_soil(soil["daily_csv"])
    weather_quality = read_json(weather["quality"]) if weather["quality"].is_file() else {}
    soil_quality = read_json(soil["quality"]) if soil["quality"].is_file() else {}
    if soil_quality.get("suitable_for_modeling") is True:
        raise AgriculturalMlError("Refusing to proceed: source soil quality set suitable_for_modeling true.")
    spatial = dict(soil_quality.get("spatial") or weather_quality.get("spatial") or {})
    if not spatial.get("source_grid_id") and spatial.get("source_latitude") is not None:
        spatial["source_grid_id"] = f"{spatial.get('source_latitude')},{spatial.get('source_longitude')}"
    period_start = parse_utc_date(config["period"]["start"])
    period_end = parse_utc_date(config["period"]["end"])
    if period_start is None or period_end is None:
        raise AgriculturalMlError("Research period is invalid.")
    issue_dates = daterange(period_start, period_end)
    sat_cfg = config.get("satellite") or {}
    observations = load_eligible_satellite_observations(
        satellite_id,
        quality_statuses=tuple(sat_cfg.get("quality_statuses") or ("valid",)),
        calibration_statuses=tuple(sat_cfg.get("calibration_statuses") or ("verified",)),
        exclude_scene_quality=tuple(sat_cfg.get("exclude_scene_quality") or ("rejected", "requires_review")),
    )
    satellite_map = satellite_by_issue_date(
        issue_dates,
        observations,
        max_age_days=int(sat_cfg.get("max_age_days") or 14),
        assumption=str(sat_cfg.get("availability_assumption") or "acquisition_time_only_research"),
    )
    features = build_daily_features(
        issue_dates=issue_dates,
        weather_rows=weather_rows,
        soil_rows=soil_rows,
        config=config,
        spatial=spatial,
        satellite_by_issue=satellite_map,
    )
    targets = build_targets(
        issue_dates=issue_dates,
        soil_rows=soil_rows,
        config=config,
        period_end=period_end,
    )
    splits = build_split_membership(targets, config)
    leakage = run_leakage_audit(feature_rows=features, target_rows=targets, split_rows=splits)
    if leakage["status"] != "passed" and (config.get("validation") or {}).get("fail_on_critical_leakage", True):
        raise AgriculturalMlError(f"Critical leakage checks failed: {leakage['critical_failures']}.")
    readiness = assess_agricultural_ml_readiness(
        feature_rows=features,
        target_rows=targets,
        split_rows=splits,
        leakage=leakage,
        satellite_eligible=len(observations),
        operational_verified=False,
        suitable_for_modeling=bool(soil_quality.get("suitable_for_modeling")),
        ground_truth=bool(soil_quality.get("is_ground_truth")),
    )
    diagnostics = _diagnostics(features, targets, splits)
    git_meta = _git_reference(base)
    fingerprints = {
        "daily_weather": source_fingerprint(weather["daily_csv"]),
        "daily_soil": source_fingerprint(soil["daily_csv"]),
        "weather_quality": source_fingerprint(weather["quality"]),
        "soil_quality": source_fingerprint(soil["quality"]),
        "config": {"sha256": config["_config_fingerprint"], "path": config["_config_path"]},
    }
    out = output_directory(config, root=base)
    if dry_run:
        return {
            "dataset_id": config["dataset_id"],
            "dry_run": True,
            "feature_rows": len(features),
            "target_rows": len(targets),
            "output_directory": str(out),
        }
    out.mkdir(parents=True, exist_ok=True)
    feature_columns = _union_columns(features)
    target_columns = _union_columns(targets)
    split_columns = _union_columns(splits)
    _write_csv(out / "features_daily.csv", features, feature_columns)
    _write_csv(out / "targets.csv", targets, target_columns)
    _write_csv(out / "split_membership.csv", splits, split_columns)
    parquet = {}
    if config["output"].get("write_parquet", True):
        if _write_parquet(features, out / "features_daily.parquet"):
            parquet["features"] = "features_daily.parquet"
        if _write_parquet(targets, out / "targets.parquet"):
            parquet["targets"] = "targets.parquet"
    if config["output"].get("write_modeling_samples", True):
        samples = _modeling_samples(features, targets, splits)
        _write_csv(out / "modeling_samples.csv", samples, _union_columns(samples))
    write_json_atomic(out / "feature_catalog.json", feature_catalog(config))
    write_json_atomic(out / "target_catalog.json", target_catalog(config))
    write_json_atomic(out / "source_fingerprints.json", fingerprints)
    write_json_atomic(out / "temporal_leakage_report.json", leakage)
    write_json_atomic(out / "split_quality_report.json", _split_report(splits, targets))
    write_json_atomic(out / "modeling_readiness.json", readiness)
    write_json_atomic(out / "dataset_quality.json", {
        "status": "valid" if leakage["status"] == "passed" else "failed",
        "suitable_for_modeling": False,
        "is_ground_truth": False,
        "operational_availability_verified": False,
        "leakage_status": leakage["status"],
        "research_mode": config["issue_time"]["research_mode"],
    })
    write_json_atomic(out / "baseline_contracts.json", baseline_catalog())
    write_json_atomic(out / "dataset_diagnostics.json", diagnostics)
    summary = {
        "dataset_id": config["dataset_id"],
        "dataset_version": config["dataset_version"],
        "pipeline_version": PIPELINE_VERSION,
        "label": "Research dataset — no trained model yet.",
        "period": config["period"],
        "aoi_id": config.get("aoi_id"),
        "sources": config["sources"],
        "feature_row_count": len(features),
        "feature_catalog_count": feature_catalog(config)["count"],
        "target_row_count": len(targets),
        "horizons_days": config["targets"]["horizons_days"],
        "eligible_satellite_scenes": len(observations),
        "issue_days_with_satellite": sum(1 for row in features if row.get("satellite_available")),
        "history_complete_rows": sum(1 for row in features if row.get("history_window_complete")),
        "available_targets": sum(1 for row in targets if row.get("target_available")),
        "missing_targets": sum(1 for row in targets if not row.get("target_available")),
        "leakage_status": leakage["status"],
        "research_readiness": readiness["summary"],
        "suitable_for_modeling": False,
        "trained_model_present": False,
        "generated_at_utc": now_iso(),
        "git": git_meta,
        "config_fingerprint": config["_config_fingerprint"],
        "parquet": parquet,
    }
    write_json_atomic(out / "dataset_summary.json", summary)
    write_json_atomic(out / "dataset_manifest.json", {
        **summary,
        "source_fingerprints": fingerprints,
        "output_files": sorted(path.name for path in out.iterdir() if path.is_file() and not path.name.startswith(".")),
    })
    return summary


def validate_dataset(config_path: Path | str, *, root: Path | None = None) -> dict[str, Any]:
    config = load_ml_config(config_path)
    out = output_directory(config, root=root)
    required = [
        "features_daily.csv", "targets.csv", "split_membership.csv",
        "temporal_leakage_report.json", "modeling_readiness.json", "dataset_summary.json",
    ]
    missing = [name for name in required if not (out / name).is_file()]
    if missing:
        raise MissingProcessedOutputError(f"Research dataset outputs missing: {missing}")
    leakage = read_json(out / "temporal_leakage_report.json")
    summary = read_json(out / "dataset_summary.json")
    readiness = read_json(out / "modeling_readiness.json")
    if summary.get("suitable_for_modeling") or readiness.get("suitable_for_modeling"):
        raise AgriculturalMlError("suitable_for_modeling must remain false.")
    if leakage.get("status") != "passed":
        raise AgriculturalMlError("Stored leakage audit is not passed.")
    return {"ok": True, "dataset_id": config["dataset_id"], "leakage_status": leakage["status"]}


def audit_leakage(config_path: Path | str, *, root: Path | None = None) -> dict[str, Any]:
    config = load_ml_config(config_path)
    out = output_directory(config, root=root)
    return read_json(out / "temporal_leakage_report.json")


def split_summary(config_path: Path | str, *, root: Path | None = None) -> dict[str, Any]:
    config = load_ml_config(config_path)
    out = output_directory(config, root=root)
    return read_json(out / "split_quality_report.json")


def report_dataset(config_path: Path | str, *, root: Path | None = None) -> dict[str, Any]:
    config = load_ml_config(config_path)
    out = output_directory(config, root=root)
    return read_json(out / "dataset_summary.json")


def _modeling_samples(
    features: list[dict[str, Any]],
    targets: list[dict[str, Any]],
    splits: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    wide = wide_targets(targets)
    split_by_key: dict[str, dict[str, Any]] = defaultdict(dict)
    for row in splits:
        key = str(row["issue_row_key"])
        horizon = int(row["horizon_days"])
        split_by_key[key][f"split_h{horizon}"] = row["split"]
        split_by_key[key][f"split_h{horizon}_excluded"] = row["excluded"]
    samples = []
    skip = {
        "ndvi_last_valid_mean", "ndvi_last_valid_median", "ndvi_last_valid_std",
        "ndvi_last_valid_p10", "ndvi_last_valid_p90", "satellite_scene_id",
        "satellite_acquisition_date_utc", "satellite_acquisition_timestamp_utc",
        "satellite_age_days", "satellite_available", "satellite_stale",
        "satellite_missing", "satellite_valid_pixel_fraction",
        "satellite_calibration_status", "satellite_scene_quality_status",
    }
    for row in features:
        key = str(row["issue_row_key"])
        sample = {name: value for name, value in row.items() if name not in skip}
        sample["experiment"] = "weather_soil_history"
        sample.update(wide.get(key) or {})
        sample.update(split_by_key.get(key) or {})
        samples.append(sample)
    return samples


def _split_report(splits: list[dict[str, Any]], targets: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, Counter] = defaultdict(Counter)
    excluded = Counter()
    available = defaultdict(Counter)
    for row in splits:
        horizon = str(row["horizon_days"])
        counts[horizon][str(row["split"])] += 1
        if row.get("excluded"):
            excluded[str(row.get("exclusion_reason") or "excluded")] += 1
    for row in targets:
        if row.get("target_available"):
            available[str(row["horizon_days"])][str(row["target_variable"])] += 1
    return {
        "strategy": "chronological_holdout",
        "counts_by_horizon": {key: dict(value) for key, value in counts.items()},
        "excluded_reasons": dict(excluded),
        "available_targets_by_horizon": {key: dict(value) for key, value in available.items()},
        "note": "Validation/test features may use earlier historical observations. Labels may not cross forward.",
    }


def _diagnostics(
    features: list[dict[str, Any]],
    targets: list[dict[str, Any]],
    splits: list[dict[str, Any]],
) -> dict[str, Any]:
    def series(rows: list[dict[str, Any]], field: str) -> list[float]:
        values = []
        for row in rows:
            try:
                value = row.get(field)
            except Exception:
                value = None
            if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)):
                values.append(float(value))
        return values

    def describe(values: list[float]) -> dict[str, float | None]:
        if not values:
            return {"n": 0, "mean": None, "stdev": None, "minimum": None, "maximum": None}
        return {
            "n": len(values),
            "mean": statistics.fmean(values),
            "stdev": statistics.pstdev(values) if len(values) > 1 else 0.0,
            "minimum": min(values),
            "maximum": max(values),
        }

    ages = series(features, "satellite_age_days")
    return {
        "correlation_is_not_skill": True,
        "shared_era5_land_ancestry": True,
        "do_not_reuse_as_preprocessing_parameters": True,
        "soil_prev1": describe(series(features, "theta_root_zone_0_100_prev1")),
        "precip_prev_7d_mm": describe(series(features, "precip_prev_7d_mm")),
        "api_k090_mm": describe(series(features, "api_k090_mm")),
        "target_theta_h1": describe([
            float(row["absolute_target"])
            for row in targets
            if row.get("target_variable") == "theta_root_zone_0_100"
            and row.get("horizon_days") == 1
            and row.get("absolute_target") is not None
        ]),
        "target_change_h1": describe([
            float(row["change_target"])
            for row in targets
            if row.get("target_variable") == "theta_root_zone_0_100"
            and row.get("horizon_days") == 1
            and row.get("change_target") is not None
        ]),
        "satellite_age_days": describe(ages),
        "feature_completeness": {
            "history_window_complete": sum(1 for row in features if row.get("history_window_complete")),
            "rows": len(features),
        },
        "split_issue_counts": dict(Counter(
            row["split"] for row in splits if row.get("target_variable") == "theta_root_zone_0_100" and row.get("horizon_days") == 1
        )),
    }


def _git_reference(root: Path) -> dict[str, Any]:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL,
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=root, text=True, stderr=subprocess.DEVNULL,
        )
        dirty = bool(status.strip())
        return {
            "commit": commit,
            "dirty": dirty,
            "git_reference": "uncommitted" if dirty else commit,
        }
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": True, "git_reference": "unknown"}


def _union_columns(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    if not rows:
        return ()
    keys: list[str] = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                keys.append(key)
    return tuple(keys)
