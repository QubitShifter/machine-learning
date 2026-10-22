"""Read-only agricultural ML research-dataset and experiment summaries."""

from __future__ import annotations

from pathlib import Path

import csv

import yaml

from backend.app.schemas.ml import (
    AgriculturalMlSummaryResponse,
    ExperimentDatasetResponse,
    ExperimentDetailResponse,
    ExperimentFeatureRecord,
    ExperimentFeaturesResponse,
    ExperimentListItem,
    ExperimentMetricsResponse,
    ExperimentPredictionsResponse,
    ExperimentProvenanceResponse,
    ExperimentTrainingResponse,
    TrainingLifecycleStage,
)
from ml.agricultural_ml.config import load_ml_config, output_directory
from ml.ingestion.manifest import validate_safe_id
from ml.preprocessing.errors import DatasetNotFoundError, MissingProcessedOutputError
from ml.preprocessing.raster import project_root, read_json

DEFAULT_CONFIG = project_root() / "configs" / "agricultural_ml_dataset.yaml"
EXPERIMENTS_ROOT = project_root() / "data" / "processed" / "ml" / "experiments"


def research_summary(dataset_id: str | None = None) -> AgriculturalMlSummaryResponse:
    if not DEFAULT_CONFIG.is_file():
        raise DatasetNotFoundError("Agricultural ML configuration is not present.")
    config = load_ml_config(DEFAULT_CONFIG)
    if dataset_id and dataset_id != config["dataset_id"]:
        raise DatasetNotFoundError(dataset_id)
    summary_path = output_directory(config) / "dataset_summary.json"
    if not summary_path.is_file():
        return AgriculturalMlSummaryResponse(
            available=False,
            dataset_id=config["dataset_id"],
            label="Research dataset — no trained model yet.",
        )
    payload = read_json(summary_path)
    readiness = (payload.get("research_readiness") or {})
    period = payload.get("period") or {}
    return AgriculturalMlSummaryResponse(
        available=True,
        label=str(payload.get("label") or "Research dataset — no trained model yet."),
        dataset_id=payload.get("dataset_id"),
        period_start=period.get("start"),
        period_end=period.get("end"),
        feature_row_count=payload.get("feature_row_count"),
        feature_catalog_count=payload.get("feature_catalog_count"),
        target_row_count=payload.get("target_row_count"),
        horizons_days=list(payload.get("horizons_days") or []),
        leakage_status=payload.get("leakage_status"),
        historical_research_readiness=readiness.get("historical_research_readiness"),
        operational_forecast_readiness=readiness.get("operational_forecast_readiness"),
        independent_ground_truth_readiness=readiness.get("independent_ground_truth_readiness"),
        suitable_for_modeling=False,
        trained_model_present=False,
        eligible_satellite_scenes=payload.get("eligible_satellite_scenes"),
    )


def _experiment_dir(experiment_id: str) -> Path:
    safe = validate_safe_id(experiment_id, "experiment_id")
    root = EXPERIMENTS_ROOT.resolve()
    path = (root / safe).resolve()
    if root not in path.parents:
        raise DatasetNotFoundError(experiment_id)
    if not path.is_dir():
        raise DatasetNotFoundError(experiment_id)
    return path


def list_experiments() -> list[ExperimentListItem]:
    if not EXPERIMENTS_ROOT.is_dir():
        return []
    items = []
    for path in sorted(EXPERIMENTS_ROOT.iterdir()):
        summary = path / "experiment_summary.json"
        manifest = path / "experiment_manifest.json"
        if not summary.is_file() and not manifest.is_file():
            continue
        payload = read_json(summary) if summary.is_file() else read_json(manifest)
        items.append(ExperimentListItem(
            experiment_id=str(payload.get("experiment_id") or path.name),
            label=str(payload.get("label") or "Research experiment on modeled ERA5-Land soil moisture."),
            frozen=bool(payload.get("frozen") or (path / "frozen_experiment.json").is_file()),
            test_evaluated=bool(payload.get("test_evaluated") or (path / "final_test_metrics.csv").is_file()),
            operational_forecast=False,
            suitable_for_modeling=False,
        ))
    return items


def experiment_detail(experiment_id: str) -> ExperimentDetailResponse:
    path = _experiment_dir(experiment_id)
    summary_path = path / "experiment_summary.json"
    payload = read_json(summary_path) if summary_path.is_file() else {}
    snapshot = _snapshot(path)
    frozen = read_json(path / "frozen_experiment.json") if (path / "frozen_experiment.json").is_file() else {}
    training = read_json(path / "training_summary.json") if (path / "training_summary.json").is_file() else {}
    source = snapshot.get("source") or {}
    target = snapshot.get("target") or {}
    feature_sets = [
        name for name, block in (snapshot.get("feature_sets") or {}).items()
        if name != "D" and (block or {}).get("enabled") is not False
    ]
    return ExperimentDetailResponse(
        experiment_id=experiment_id,
        label=str(payload.get("label") or "Research experiment on ERA5-Land modeled soil moisture. Not operational."),
        frozen=(path / "frozen_experiment.json").is_file(),
        test_evaluated=(path / "final_test_metrics.csv").is_file(),
        suitable_for_modeling=False,
        trained_model_present=(path / "training_summary.json").is_file(),
        operational_forecast=False,
        target_source_kind=str(source.get("target_source_kind") or "modeled_reanalysis"),
        dataset_id=source.get("ml_dataset_id"),
        dataset_version=str(source.get("ml_dataset_version")) if source.get("ml_dataset_version") else None,
        pipeline_version=snapshot.get("pipeline_version") or frozen.get("pipeline_version"),
        target_variable=target.get("variable"),
        depth_label=target.get("depth_label"),
        unit=target.get("unit"),
        horizons_days=[int(item) for item in (target.get("horizons_days") or [])],
        feature_sets=feature_sets,
        primary_feature_set=str(snapshot.get("primary_feature_set") or frozen.get("primary_feature_set") or "C"),
        config_fingerprint=frozen.get("config_fingerprint") or payload.get("config_fingerprint"),
        frozen_at_utc=frozen.get("frozen_at_utc"),
        random_seed=_as_int(training.get("random_seed") or snapshot.get("random_seed")),
        research_mode=str((snapshot.get("issue_time") or {}).get("research_mode") or "research_reanalysis"),
        validation_comparison=_sanitize(list(payload.get("validation_comparison") or [])),
        final_test_metrics=_sanitize(payload.get("final_test_metrics")),
    )


def _csv_records(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def experiment_metrics(experiment_id: str, *, partition: str = "validation") -> ExperimentMetricsResponse:
    path = _experiment_dir(experiment_id)
    if partition == "test":
        records = _csv_records(path / "final_test_metrics.csv")
    else:
        records = _csv_records(path / "model_comparison.csv") or _csv_records(path / "validation_metrics.csv")
    return ExperimentMetricsResponse(
        experiment_id=experiment_id,
        partition=partition,
        total=len(records),
        records=records,
    )


def experiment_predictions(
    experiment_id: str,
    *,
    partition: str = "validation",
    horizon_days: int | None = None,
    model_id: str | None = None,
    feature_set: str | None = None,
    offset: int = 0,
    limit: int = 200,
) -> ExperimentPredictionsResponse:
    path = _experiment_dir(experiment_id)
    selected_only = False
    if partition == "test":
        records = _csv_records(path / "final_test_predictions.csv")
        selected_only = True
    else:
        selected = path / "selected_validation_predictions.csv"
        if selected.is_file():
            records = _csv_records(selected)
            selected_only = True
        else:
            records = _csv_records(path / "validation_predictions.csv")
    if horizon_days is not None:
        records = [row for row in records if str(row.get("horizon_days")) == str(horizon_days)]
    if model_id:
        records = [row for row in records if str(row.get("model_id")) == model_id]
    if feature_set:
        records = [row for row in records if str(row.get("feature_set")) == feature_set]
    limit = max(1, min(int(limit), 2000))
    offset = max(0, int(offset))
    page = records[offset:offset + limit]
    return ExperimentPredictionsResponse(
        experiment_id=experiment_id,
        partition=partition,
        total=len(records),
        offset=offset,
        limit=limit,
        records=page,
        selected_only=selected_only,
    )


def experiment_dataset(experiment_id: str) -> ExperimentDatasetResponse:
    path = _experiment_dir(experiment_id)
    prepared_path = path / "prepared_summary.json"
    if not prepared_path.is_file():
        return ExperimentDatasetResponse(experiment_id=experiment_id, available=False)
    prepared = read_json(prepared_path)
    snapshot = _snapshot(path)
    source = snapshot.get("source") or {}
    target = snapshot.get("target") or {}
    missing = snapshot.get("missing_data") or {}
    feature_sets = []
    for name, block in (snapshot.get("feature_sets") or {}).items():
        enabled = name != "D" and (block or {}).get("enabled") is not False
        feature_sets.append({
            "id": name,
            "name": (block or {}).get("name"),
            "enabled": enabled,
            "status": "available" if enabled else "not_trained",
            "columns": list((block or {}).get("columns") or []),
            "reason": (block or {}).get("reason"),
        })
    return ExperimentDatasetResponse(
        experiment_id=experiment_id,
        available=True,
        dataset_id=source.get("ml_dataset_id"),
        dataset_version=str(source.get("ml_dataset_version")) if source.get("ml_dataset_version") else None,
        pipeline_version=snapshot.get("pipeline_version"),
        target_variable=target.get("variable"),
        depth_label=target.get("depth_label"),
        unit=target.get("unit"),
        horizons_days=[int(item) for item in (target.get("horizons_days") or [])],
        feature_sets=feature_sets,
        n_joined_rows=_as_int(prepared.get("n_joined_rows")),
        eligible_rows=_as_int(prepared.get("eligible_rows")),
        counts=list(prepared.get("counts") or []),
        missing_data_policy=str(missing.get("policy") or "complete_case"),
        satellite_features_enabled=bool(snapshot.get("satellite_features_enabled")),
        chronological_splits={
            "training": "2023",
            "validation": "2024",
            "test": "2025",
            "source": (snapshot.get("splits") or {}).get("source"),
            "horizon_purge": bool((snapshot.get("splits") or {}).get("respect_horizon_purge", True)),
            "final_training_policy": (snapshot.get("splits") or {}).get("final_training_policy"),
            "note": "Years follow the Phase 4.0 chronological holdout used by this experiment.",
        },
        target_source_kind=str(source.get("target_source_kind") or "modeled_reanalysis"),
    )


def experiment_features(experiment_id: str) -> ExperimentFeaturesResponse:
    path = _experiment_dir(experiment_id)
    catalog_path = path / "feature_selection.json"
    if not catalog_path.is_file():
        return ExperimentFeaturesResponse(experiment_id=experiment_id, available=False)
    payload = read_json(catalog_path)
    grouped: dict[str, ExperimentFeatureRecord] = {}
    primary = str(payload.get("primary_feature_set") or "C")
    for item in payload.get("features") or []:
        column = str(item.get("column_name") or "")
        if not column:
            continue
        current = grouped.get(column)
        set_id = str(item.get("feature_set") or "")
        if current is None:
            grouped[column] = ExperimentFeatureRecord(
                feature_id=item.get("feature_id"),
                column_name=column,
                scientific_meaning=item.get("formula") or item.get("source_variable"),
                input_source=item.get("input_source"),
                source_variable=item.get("source_variable"),
                units=item.get("units"),
                temporal_window=item.get("temporal_window"),
                formula=item.get("formula"),
                missing_data_policy=item.get("missing_data_policy"),
                feature_sets=[set_id] if set_id else [],
                used_by_primary=set_id == primary,
                satellite=str(item.get("feature_id") or "").startswith("satellite."),
            )
        else:
            if set_id and set_id not in current.feature_sets:
                current.feature_sets.append(set_id)
            current.used_by_primary = current.used_by_primary or set_id == primary
    records = list(grouped.values())
    primary_count = sum(1 for item in records if item.used_by_primary)
    return ExperimentFeaturesResponse(
        experiment_id=experiment_id,
        available=True,
        primary_feature_set=primary,
        satellite_excluded=bool(payload.get("satellite_excluded", True)),
        satellite_reason=payload.get("satellite_reason"),
        predictive_feature_count=primary_count,
        records=records,
    )


def experiment_training(experiment_id: str) -> ExperimentTrainingResponse:
    path = _experiment_dir(experiment_id)
    summary_path = path / "training_summary.json"
    if not summary_path.is_file():
        return ExperimentTrainingResponse(
            experiment_id=experiment_id,
            available=False,
            telemetry={
                "available": False,
                "reason": "Training history unavailable — this experiment recorded final metrics but not per-iteration telemetry.",
            },
            lifecycle=_lifecycle(path),
        )
    summary = read_json(summary_path)
    frozen = read_json(path / "frozen_experiment.json") if (path / "frozen_experiment.json").is_file() else {}
    events_present = (path / "training_events.jsonl").is_file()
    selected = _sanitize(list(frozen.get("selected") or []))
    coefficients = _ridge_coefficients(path, selected)
    seasonal = _seasonal_means(path, selected)
    return ExperimentTrainingResponse(
        experiment_id=experiment_id,
        available=True,
        live_training=False,
        fitted_on=str(summary.get("fitted_on") or frozen.get("fitted_on") or "training"),
        validation_used_for_fitting=bool(summary.get("validation_used_for_fitting")),
        test_used_for_fitting=bool(summary.get("test_used_for_fitting")),
        random_seed=_as_int(summary.get("random_seed")),
        generated_at_utc=summary.get("generated_at_utc"),
        selected=selected,
        trained_candidate_count=len(summary.get("trained") or []),
        telemetry={
            "available": events_present,
            "format": "training_events.jsonl",
            "reason": None if events_present else (
                "Training history unavailable — this experiment recorded final metrics "
                "but not per-iteration telemetry."
            ),
        },
        lifecycle=_lifecycle(path),
        coefficients=coefficients,
        seasonal_monthly_means=seasonal,
    )


def experiment_provenance(experiment_id: str) -> ExperimentProvenanceResponse:
    path = _experiment_dir(experiment_id)
    snapshot = _snapshot(path)
    frozen = read_json(path / "frozen_experiment.json") if (path / "frozen_experiment.json").is_file() else {}
    training = read_json(path / "training_summary.json") if (path / "training_summary.json").is_file() else {}
    fingerprint = read_json(path / "data_fingerprint.json") if (path / "data_fingerprint.json").is_file() else {}
    log = read_json(path / "test_evaluation_log.json") if (path / "test_evaluation_log.json").is_file() else {}
    git_meta = training.get("git") or frozen.get("git") or {}
    versions = training.get("versions") or {}
    source = snapshot.get("source") or {}
    issue = snapshot.get("issue_time") or {}
    features_hash = fingerprint.get("features_daily_sha256") or {}
    if isinstance(features_hash, dict):
        features_sha = features_hash.get("sha256")
    else:
        features_sha = features_hash
    python = versions.get("python")
    packages = {key: value for key, value in versions.items() if key != "python"}
    return ExperimentProvenanceResponse(
        experiment_id=experiment_id,
        available=True,
        pipeline_version=snapshot.get("pipeline_version") or frozen.get("pipeline_version"),
        dataset_id=source.get("ml_dataset_id"),
        dataset_version=str(source.get("ml_dataset_version")) if source.get("ml_dataset_version") else None,
        config_fingerprint=frozen.get("config_fingerprint") or fingerprint.get("config_fingerprint"),
        features_daily_sha256=features_sha,
        frozen=(path / "frozen_experiment.json").is_file(),
        frozen_at_utc=frozen.get("frozen_at_utc"),
        test_consulted=bool(frozen.get("test_consulted")),
        test_evaluated_at_utc=frozen.get("test_evaluated_at_utc") or log.get("test_evaluated_at_utc"),
        test_repeat=log.get("repeat"),
        git_revision=git_meta.get("commit") or git_meta.get("git_reference"),
        git_dirty=git_meta.get("dirty"),
        python_version=python,
        package_versions=packages,
        random_seed=_as_int(training.get("random_seed") or snapshot.get("random_seed")),
        research_mode=str(issue.get("research_mode") or "research_reanalysis"),
        operational_availability_verified=False,
        training_events_present=(path / "training_events.jsonl").is_file(),
        label=str(
            (read_json(path / "experiment_manifest.json") if (path / "experiment_manifest.json").is_file() else {}).get("label")
            or "Research experiment on ERA5-Land modeled soil moisture. Not operational."
        ),
    )


def _snapshot(path: Path) -> dict:
    snapshot_path = path / "experiment_config_snapshot.yaml"
    if not snapshot_path.is_file():
        return {}
    payload = yaml.safe_load(snapshot_path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {}


def _lifecycle(path: Path) -> list[TrainingLifecycleStage]:
    stages = [
        ("source_validated", "Source dataset validated", "experiment_config_snapshot.yaml"),
        ("features_selected", "Features selected", "feature_selection.json"),
        ("samples_filtered", "Historical samples filtered", "prepared_summary.json"),
        ("splits_verified", "Chronological split verified", "prepared_summary.json"),
        ("preprocessor_fitted", "Preprocessor fitted", "training_summary.json"),
        ("model_training", "Model training", "training_summary.json"),
        ("validation_predictions", "Validation predictions", "validation_metrics.csv"),
        ("hyperparameters_selected", "Hyperparameters selected", "model_comparison.csv"),
        ("configuration_frozen", "Configuration frozen", "frozen_experiment.json"),
        ("final_test_evaluation", "Final test evaluation", "final_test_metrics.csv"),
        ("artifacts_saved", "Artifacts saved", "experiment_manifest.json"),
    ]
    rows = []
    for stage, label, artifact in stages:
        present = (path / artifact).is_file()
        rows.append(TrainingLifecycleStage(
            stage=stage,
            label=label,
            status="completed" if present else "unavailable",
            artifact=artifact if present else None,
        ))
    return rows


def _ridge_coefficients(path: Path, selected: list[dict]) -> list[dict]:
    rows = []
    models_dir = path / "models"
    for item in selected:
        if str(item.get("model_id")) != "ridge":
            continue
        filename = str(item.get("path") or "")
        if not filename or "/" in filename or "\\" in filename:
            continue
        artifact = models_dir / filename
        if not artifact.is_file():
            rows.append({
                "model_id": "ridge",
                "horizon_days": item.get("horizon_days"),
                "feature_set": item.get("feature_set"),
                "available": False,
                "reason": "Fitted Ridge artifact is missing.",
            })
            continue
        try:
            from ml.soil_forecasting.models import load_joblib
            payload = load_joblib(artifact)
            estimator = payload.get("estimator")
            columns = list(payload.get("columns") or [])
            ridge = getattr(estimator, "named_steps", {}).get("ridge") if estimator is not None else None
            if ridge is None or not hasattr(ridge, "coef_"):
                rows.append({
                    "model_id": "ridge",
                    "horizon_days": item.get("horizon_days"),
                    "available": False,
                    "reason": "Ridge coefficients are not present on the stored estimator.",
                })
                continue
            coef = [float(value) for value in list(ridge.coef_)]
            rows.append({
                "model_id": "ridge",
                "horizon_days": item.get("horizon_days"),
                "feature_set": item.get("feature_set"),
                "alpha": item.get("alpha"),
                "available": True,
                "scaled": True,
                "intercept": float(ridge.intercept_) if hasattr(ridge, "intercept_") else None,
                "coefficients": [
                    {"feature": columns[index] if index < len(columns) else f"x{index}", "value": value}
                    for index, value in enumerate(coef)
                ],
                "note": "Coefficients are on StandardScaler units fitted on the training partition only.",
            })
        except Exception:
            rows.append({
                "model_id": "ridge",
                "horizon_days": item.get("horizon_days"),
                "available": False,
                "reason": "Ridge artifact could not be deserialized for coefficients.",
            })
    return rows


def _seasonal_means(path: Path, selected: list[dict]) -> dict | None:
    means = {}
    for item in selected:
        if str(item.get("model_id")) != "seasonal":
            continue
        filename = str(item.get("path") or f"seasonal_h{item.get('horizon_days')}.json")
        if "/" in filename or "\\" in filename:
            continue
        artifact = path / "models" / filename
        if not artifact.is_file():
            continue
        payload = read_json(artifact)
        means[str(item.get("horizon_days"))] = {
            "label": payload.get("label") or "training_year_seasonal_reference",
            "n_train": payload.get("n_train"),
            "monthly_means": payload.get("monthly_means") or {},
        }
    return means or None


def _as_int(value) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _sanitize(value):
    if isinstance(value, dict):
        clean = {}
        for key, item in value.items():
            if key in {"source_dataset_dir", "directory", "_config_path"}:
                continue
            if key == "path" and isinstance(item, str) and ("/" in item or "\\" in item):
                clean[key] = Path(item).name
            else:
                clean[key] = _sanitize(item)
        return clean
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value
