"""Opt-in research-development training with genuine telemetry.

Reads the existing joined modeling frame. Writes only under runs/<run_id>/.
Never loads 2025 test targets. Never mutates frozen Phase 4.1 artifacts.
"""

from __future__ import annotations

import time
from collections import Counter
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import pandas as pd

from ml.ingestion.manifest import write_json_atomic
from ml.preprocessing.errors import SoilForecastingError
from ml.preprocessing.raster import project_root, read_json
from ml.soil_forecasting.config import load_experiment_config, output_directory
from ml.soil_forecasting.dataset import enabled_feature_sets, matrix, partition_frame
from ml.soil_forecasting.evaluate import aligned_metrics, attach_predictions
from ml.soil_forecasting.models import (
    boosting_estimator,
    fit_seasonal_monthly,
    fit_sklearn,
    persistence_predict,
    predict_sklearn,
    ridge_pipeline,
    save_joblib,
    seasonal_predict,
)
from ml.soil_forecasting.run_registry import (
    assert_frozen_unchanged,
    create_run_directory,
    environment_metadata,
    fingerprint_columns,
    initial_manifest,
    new_run_id,
    snapshot_frozen_artifacts,
    write_manifest,
    write_run_config,
)
from ml.soil_forecasting.telemetry import (
    EventWriter,
    assert_transition,
    validate_event_log,
    read_jsonl_events,
    write_validation_report,
)


MODEL_ALIASES = {
    "persistence": "persistence",
    "seasonal": "seasonal",
    "ridge": "ridge",
    "gradient_boosting": "gradient_boosting",
    "hist_gradient_boosting": "gradient_boosting",
    "hgbr": "gradient_boosting",
}
ALLOWED_MODELS = frozenset({"persistence", "seasonal", "ridge", "gradient_boosting"})
PROVENANCE_LABEL = "telemetry_development_run"
EXECUTION_MODE = "research_development"


def execute_train_run(
    config_path: Path | str,
    *,
    model: str,
    horizon: int,
    feature_set: str = "C",
    telemetry: bool = False,
    alpha: float | None = None,
    max_depth: int | None = None,
    learning_rate: float | None = None,
    max_iter: int | None = None,
    seed: int | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    if not telemetry:
        raise SoilForecastingError("train-run requires an explicit --telemetry flag.")
    algorithm = MODEL_ALIASES.get(str(model))
    if algorithm not in ALLOWED_MODELS:
        raise SoilForecastingError(f"Unsupported model {model}.")
    if int(horizon) not in {1, 3, 7}:
        raise SoilForecastingError("horizon must be 1, 3 or 7.")
    config = load_experiment_config(config_path)
    base = root or project_root()
    experiment_dir = output_directory(config, root=base)
    joined = experiment_dir / "joined_modeling_frame.csv"
    if not joined.is_file():
        raise SoilForecastingError(
            "joined_modeling_frame.csv is missing. train-run reads the existing prepared "
            "frame and will not call prepare or overwrite frozen artifacts."
        )
    sets = enabled_feature_sets(config)
    set_id = str(feature_set)
    if set_id not in sets:
        raise SoilForecastingError(f"Feature set {set_id} is not enabled.")
    columns = list(sets[set_id])
    frozen_before = snapshot_frozen_artifacts(experiment_dir)
    run_id = new_run_id()
    run_dir = create_run_directory(experiment_dir, run_id)
    random_seed = int(seed if seed is not None else config.get("random_seed") or 42)
    hyperparameters = _hyperparameters(
        algorithm, config, alpha=alpha, max_depth=max_depth,
        learning_rate=learning_rate, max_iter=max_iter, seed=random_seed,
    )
    fingerprints = _fingerprints(config, experiment_dir, columns)
    environment = environment_metadata(base)
    manifest = initial_manifest(
        run_id=run_id,
        experiment_id=str(config["experiment_id"]),
        algorithm=algorithm,
        horizon_days=int(horizon),
        feature_set=set_id,
        target_variable=str(config["target"]["variable"]),
        provenance_label=PROVENANCE_LABEL,
        research_mode="research_reanalysis",
        execution_mode=EXECUTION_MODE,
        hyperparameters=hyperparameters,
        random_seed=random_seed,
        environment=environment,
        fingerprints=fingerprints,
        pipeline_version=str(config.get("pipeline_version") or "4.1.0"),
    )
    write_manifest(run_dir, manifest)
    write_run_config(run_dir, {
        "run_id": run_id,
        "experiment_id": config["experiment_id"],
        "execution_mode": EXECUTION_MODE,
        "provenance_label": PROVENANCE_LABEL,
        "algorithm": algorithm,
        "horizon_days": int(horizon),
        "feature_set": set_id,
        "columns": columns,
        "hyperparameters": hyperparameters,
        "random_seed": random_seed,
        "matches_historical_config": _matches_historical(algorithm, hyperparameters, config, set_id),
        "is_frozen_phase_4_1_model": False,
        "test_targets_accessed": False,
        "allow_test": False,
        "research_mode": "research_reanalysis",
        "suitable_for_modeling": False,
        "parent_config_fingerprint": config.get("_config_fingerprint"),
    })
    timings: dict[str, int] = {}
    writer = EventWriter(run_dir, run_id)
    try:
        writer.emit(
            event_type="run_created",
            phase="created",
            model=algorithm,
            horizon_days=int(horizon),
            details={
                "execution_mode": EXECUTION_MODE,
                "provenance_label": PROVENANCE_LABEL,
                "feature_set": set_id,
            },
        )
        _set_status(manifest, "preparing", run_dir)
        with _timed(timings, "dataset_loading"):
            frame = pd.read_csv(joined)
        _assert_no_test_partition_request(frame)
        with _timed(timings, "input_validation"):
            writer.emit(event_type="dataset_validation_started", phase="dataset", model=algorithm, horizon_days=int(horizon))
            train, validation = _development_partitions(frame, split_horizon=int(horizon), columns=columns)
            writer.emit(
                event_type="dataset_validation_completed",
                phase="dataset",
                model=algorithm,
                horizon_days=int(horizon),
                details={
                    "training_rows": int(len(train)),
                    "validation_rows": int(len(validation)),
                    "test_rows_used": 0,
                },
            )
        with _timed(timings, "feature_preparation"):
            writer.emit(
                event_type="features_prepared",
                phase="features",
                model=algorithm,
                horizon_days=int(horizon),
                details={"feature_set": set_id, "n_features": len(columns), "columns": columns},
            )
        with _timed(timings, "split_verification"):
            split_info = _verify_splits(train, validation)
            writer.emit(event_type="split_verified", phase="split", model=algorithm, horizon_days=int(horizon), details=split_info)
        dataset_summary = {
            "run_id": run_id,
            "experiment_id": config["experiment_id"],
            "target_variable": config["target"]["variable"],
            "depth_label": config["target"].get("depth_label"),
            "unit": config["target"].get("unit") or "m3 m-3",
            "horizon_days": int(horizon),
            "feature_set": set_id,
            "training_sample_count": int(len(train)),
            "validation_sample_count": int(len(validation)),
            "test_sample_count_used": 0,
            "selected_feature_count": len(columns),
            "split_verification": split_info,
            "test_targets_accessed": False,
        }
        write_json_atomic(run_dir / "dataset_summary.json", dataset_summary)
        write_json_atomic(run_dir / "feature_manifest.json", {
            "run_id": run_id,
            "feature_set": set_id,
            "columns": columns,
            "selected_feature_count": len(columns),
            "feature_schema_fingerprint": fingerprints["feature_schema_fingerprint"],
            "satellite_features_enabled": False,
        })
        persist_col = str(config["target"]["persistence_feature"])
        diagnostics: dict[str, Any] = {}
        _set_status(manifest, "training", run_dir)
        with _timed(timings, "model_fitting"):
            fitted = _fit_algorithm(
                writer=writer,
                algorithm=algorithm,
                train=train,
                validation=validation,
                columns=columns,
                persist_col=persist_col,
                hyperparameters=hyperparameters,
                horizon=int(horizon),
                timings=timings,
            )
        diagnostics = fitted["diagnostics"]
        _set_status(manifest, "validating", run_dir)
        writer.emit(event_type="validation_started", phase="validation", model=algorithm, horizon_days=int(horizon))
        with _timed(timings, "validation_prediction"):
            train_hat = fitted["train_predictions"]
            val_hat = fitted["validation_predictions"]
            train_scored = attach_predictions(train, train_hat, persistence_feature=persist_col)
            val_scored = attach_predictions(validation, val_hat, persistence_feature=persist_col)
        tolerance = float((config.get("evaluation") or {}).get("direction_tolerance") or 1e-4)
        with _timed(timings, "metric_calculation"):
            train_metrics = aligned_metrics(
                train_scored["absolute_target"], train_scored["prediction"],
                train_scored["persistence_prediction"], train_scored["persistence_prediction"],
                direction_tolerance=tolerance,
            )
            val_metrics = aligned_metrics(
                val_scored["absolute_target"], val_scored["prediction"],
                val_scored["persistence_prediction"], val_scored["persistence_prediction"],
                direction_tolerance=tolerance,
            )
        metric_records = _metric_records(train_metrics, val_metrics, algorithm=algorithm, fitted=fitted)
        for record in metric_records:
            if record["dataset_partition"] == "validation" or record.get("emit_event"):
                writer.emit(
                    event_type="training_metric",
                    phase="validation" if record["dataset_partition"] == "validation" else "fit",
                    model=algorithm,
                    horizon_days=int(horizon),
                    metric_name=record["metric_name"],
                    metric_value=record["metric_value"],
                    metric_unit=record["metric_unit"],
                    dataset_partition=record["dataset_partition"],
                    details={
                        "calculation_method": record["calculation_method"],
                        "sample_count": record["sample_count"],
                        "directionality": record["directionality"],
                        "computed_during": record["computed_during"],
                        "optimization_objective": record["optimization_objective"],
                    },
                )
        writer.emit(
            event_type="validation_completed",
            phase="validation",
            model=algorithm,
            horizon_days=int(horizon),
            details={"n": val_metrics.get("n"), "mae": val_metrics.get("mae"), "rmse": val_metrics.get("rmse")},
        )
        _set_status(manifest, "saving", run_dir)
        with _timed(timings, "artifact_serialization"):
            artifacts = _save_artifacts(
                writer=writer,
                run_dir=run_dir,
                algorithm=algorithm,
                fitted=fitted,
                val_scored=val_scored,
                config=config,
                set_id=set_id,
                horizon=int(horizon),
            )
        timings["total_run"] = writer.elapsed_ms()
        training_summary = {
            "run_id": run_id,
            "experiment_id": config["experiment_id"],
            "algorithm": algorithm,
            "horizon_days": int(horizon),
            "feature_set": set_id,
            "fitted_on": "training",
            "validation_used_for_fitting": False,
            "test_used_for_fitting": False,
            "test_targets_accessed": False,
            "training_sample_count": int(len(train)),
            "validation_sample_count": int(len(validation)),
            "selected_feature_count": len(columns),
            "hyperparameters": hyperparameters,
            "diagnostics": diagnostics,
            "timings_ms": timings,
            "provenance_label": PROVENANCE_LABEL,
            "execution_mode": EXECUTION_MODE,
            "is_frozen_phase_4_1_model": False,
        }
        write_json_atomic(run_dir / "training_summary.json", training_summary)
        write_json_atomic(run_dir / "metrics.json", {
            "run_id": run_id,
            "records": metric_records,
            "training": train_metrics,
            "validation": val_metrics,
        })
        val_scored.assign(model_id=algorithm, feature_set=set_id, partition="validation").to_csv(
            run_dir / "validation_predictions.csv", index=False,
        )
        writer.emit(event_type="artifact_saved", phase="saving", model=algorithm, horizon_days=int(horizon), details={"file": "validation_predictions.csv"})
        events, read_info = read_jsonl_events(run_dir / "training_events.jsonl", run_id=run_id)
        # The just-written events are on disk; run_completed is emitted next.
        manifest.update({
            "training_sample_count": int(len(train)),
            "validation_sample_count": int(len(validation)),
            "selected_feature_count": len(columns),
            "artifacts": artifacts,
            "timings_ms": timings,
            "validation_mae": val_metrics.get("mae"),
            "validation_rmse": val_metrics.get("rmse"),
            "validation_skill_mae": val_metrics.get("skill_mae"),
            "diagnostics": {
                key: diagnostics[key]
                for key in (
                    "optimizer", "training_iterations", "convergence_status",
                    "iteration_history_available", "iteration_history_reason",
                    "n_iter_", "max_iter", "solver",
                )
                if key in diagnostics
            },
        })
        writer.emit(
            event_type="run_completed",
            phase="completed",
            model=algorithm,
            horizon_days=int(horizon),
            details={"status": "completed", "event_count_before_completion": len(events)},
        )
        writer.mark_immutable()
        _set_status(manifest, "completed", run_dir, finish=True)
        events, read_info = read_jsonl_events(run_dir / "training_events.jsonl", run_id=run_id)
        report = validate_event_log(
            events,
            run_id=run_id,
            expected_model=algorithm,
            expected_horizon=int(horizon),
            read_info=read_info,
            status="completed",
        )
        write_validation_report(run_dir / "telemetry_validation.json", report)
        if not report["ok"]:
            raise SoilForecastingError("Telemetry validation failed: " + "; ".join(report["errors"]))
        assert_frozen_unchanged(experiment_dir, frozen_before)
        manifest["event_count"] = report["event_count"]
        write_manifest(run_dir, manifest)
        return {
            "ok": True,
            "run_id": run_id,
            "experiment_id": config["experiment_id"],
            "status": "completed",
            "algorithm": algorithm,
            "horizon_days": int(horizon),
            "feature_set": set_id,
            "training_sample_count": int(len(train)),
            "validation_sample_count": int(len(validation)),
            "event_count": report["event_count"],
            "timings_ms": timings,
            "validation_mae": val_metrics.get("mae"),
            "test_targets_accessed": False,
            "frozen_artifacts_unchanged": True,
            "run_directory": "runs/" + run_id,
        }
    except Exception as exc:
        _record_failure(writer, manifest, run_dir, exc)
        raise
    finally:
        writer.close()
        try:
            assert_frozen_unchanged(experiment_dir, frozen_before)
        except SoilForecastingError:
            raise


def _record_failure(writer: EventWriter, manifest: dict[str, Any], run_dir: Path, exc: BaseException) -> None:
    message = _safe_error(exc)
    try:
        if not writer._closed and not writer._immutable:
            writer.emit(
                event_type="run_failed",
                phase="failed",
                model=str(manifest.get("algorithm")),
                horizon_days=manifest.get("forecast_horizon_days"),
                details={"error": message},
            )
            writer.mark_immutable()
    except Exception:
        pass
    try:
        current = str(manifest.get("status") or "created")
        if current not in {"completed", "failed", "interrupted"}:
            try:
                assert_transition(current, "failed")
            except SoilForecastingError:
                pass
            manifest["status"] = "failed"
        manifest["error"] = message
        manifest["finish_at_utc"] = manifest.get("finish_at_utc")
        from ml.soil_forecasting.telemetry import utc_z
        manifest["finish_at_utc"] = utc_z()
        write_manifest(run_dir, manifest)
    except Exception:
        pass


def _safe_error(exc: BaseException) -> str:
    text = f"{type(exc).__name__}: {exc}"
    return text.replace("\\", "/").split("\n")[0][:500]


def _set_status(manifest: dict[str, Any], status: str, run_dir: Path, *, finish: bool = False) -> None:
    from ml.soil_forecasting.telemetry import utc_z
    assert_transition(str(manifest["status"]), status)
    manifest["status"] = status
    if finish:
        manifest["finish_at_utc"] = utc_z()
    write_manifest(run_dir, manifest)


@contextmanager
def _timed(timings: dict[str, int], name: str) -> Iterator[None]:
    start = time.monotonic()
    yield
    timings[name] = int((time.monotonic() - start) * 1000)


def _hyperparameters(
    algorithm: str,
    config: dict[str, Any],
    *,
    alpha: float | None,
    max_depth: int | None,
    learning_rate: float | None,
    max_iter: int | None,
    seed: int,
) -> dict[str, Any]:
    if algorithm == "persistence":
        return {"optimizer": "none", "feature": config["target"]["persistence_feature"]}
    if algorithm == "seasonal":
        seasonal = config.get("models", {}).get("seasonal") or {}
        return {
            "optimizer": "none",
            "method": seasonal.get("method") or "training_year_monthly_mean",
        }
    if algorithm == "ridge":
        return {
            "alpha": float(alpha if alpha is not None else 1.0),
            "solver": "auto",
            "fit_intercept": True,
            "scaler": "StandardScaler",
        }
    gb = config.get("models", {}).get("gradient_boosting") or {}
    grid = gb.get("grid") or {}
    return {
        "estimator": "HistGradientBoostingRegressor",
        "max_depth": int(max_depth if max_depth is not None else (grid.get("max_depth") or [3])[0]),
        "learning_rate": float(learning_rate if learning_rate is not None else (grid.get("learning_rate") or [0.1])[0]),
        "max_iter": int(max_iter if max_iter is not None else (grid.get("max_iter") or [50])[0]),
        "early_stopping": False,
        "random_state": int(seed),
        "loss": "squared_error",
    }


def _matches_historical(algorithm: str, hyperparameters: dict[str, Any], config: dict[str, Any], feature_set: str) -> bool:
    if algorithm == "ridge":
        alphas = [float(item) for item in (config.get("models", {}).get("ridge") or {}).get("alphas") or []]
        return hyperparameters.get("alpha") in alphas and feature_set in ((config.get("models", {}).get("ridge") or {}).get("feature_sets") or [])
    if algorithm == "gradient_boosting":
        grid = (config.get("models", {}).get("gradient_boosting") or {}).get("grid") or {}
        return (
            hyperparameters.get("max_depth") in (grid.get("max_depth") or [])
            and hyperparameters.get("learning_rate") in (grid.get("learning_rate") or [])
            and hyperparameters.get("max_iter") in (grid.get("max_iter") or [])
        )
    return algorithm in {"persistence", "seasonal"}


def _fingerprints(config: dict[str, Any], experiment_dir: Path, columns: list[str]) -> dict[str, Any]:
    data_fp = read_json(experiment_dir / "data_fingerprint.json") if (experiment_dir / "data_fingerprint.json").is_file() else {}
    features_hash = data_fp.get("features_daily_sha256")
    if isinstance(features_hash, dict):
        features_hash = features_hash.get("sha256")
    return {
        "source_dataset_fingerprint": features_hash,
        "feature_schema_fingerprint": fingerprint_columns(columns),
        "configuration_fingerprint": config.get("_config_fingerprint"),
    }


def _assert_no_test_partition_request(frame: pd.DataFrame) -> None:
    if "split" not in frame.columns:
        raise SoilForecastingError("Modeling frame is missing the split column.")


def _development_partitions(frame: pd.DataFrame, *, split_horizon: int, columns: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = partition_frame(frame, split="training", horizon=split_horizon, columns=columns)
    validation = partition_frame(frame, split="validation", horizon=split_horizon, columns=columns)
    if (train["split"] == "test").any() or (validation["split"] == "test").any():
        raise SoilForecastingError("Development partitions included test-split rows.")
    return train, validation


def _verify_splits(train: pd.DataFrame, validation: pd.DataFrame) -> dict[str, Any]:
    def years(frame: pd.DataFrame) -> list[str]:
        stamps = frame["issue_date_utc"].astype(str).str.slice(0, 4)
        return sorted({item for item in stamps.tolist() if item.isdigit()})

    train_years = years(train)
    val_years = years(validation)
    if "2025" in train_years or "2025" in val_years:
        raise SoilForecastingError("Research-development runs cannot use 2025 issue dates.")
    return {
        "training_issue_years": train_years,
        "validation_issue_years": val_years,
        "training_rows": int(len(train)),
        "validation_rows": int(len(validation)),
        "test_rows_used": 0,
        "chronological": True,
        "shuffled": False,
    }


def _fit_algorithm(
    *,
    writer: EventWriter,
    algorithm: str,
    train: pd.DataFrame,
    validation: pd.DataFrame,
    columns: list[str],
    persist_col: str,
    hyperparameters: dict[str, Any],
    horizon: int,
    timings: dict[str, int],
) -> dict[str, Any]:
    writer.emit(event_type="preprocessing_started", phase="preprocessing", model=algorithm, horizon_days=horizon)
    if algorithm == "persistence":
        writer.emit(event_type="preprocessing_completed", phase="preprocessing", model=algorithm, horizon_days=horizon, details={"scaler": None})
        return _fit_persistence(writer, train, validation, persist_col, horizon, timings)
    if algorithm == "seasonal":
        writer.emit(event_type="preprocessing_completed", phase="preprocessing", model=algorithm, horizon_days=horizon, details={"scaler": None})
        return _fit_seasonal(writer, train, validation, persist_col, hyperparameters, horizon, timings)
    if algorithm == "ridge":
        return _fit_ridge(writer, train, validation, columns, persist_col, hyperparameters, horizon, timings)
    return _fit_boosting(writer, train, validation, columns, persist_col, hyperparameters, horizon, timings)


def _fit_persistence(writer, train, validation, persist_col, horizon, timings) -> dict[str, Any]:
    writer.emit(event_type="training_started", phase="fit", model="persistence", horizon_days=horizon, details={"trainable": False})
    start = time.monotonic()
    train_hat = persistence_predict(train, persist_col)
    val_hat = persistence_predict(validation, persist_col)
    duration = int((time.monotonic() - start) * 1000)
    timings["baseline_computation"] = duration
    diagnostics = {
        "optimizer": "none",
        "training_iterations": 0,
        "convergence_status": "not_applicable",
        "iteration_history_available": False,
        "iteration_history_reason": "non_trained_baseline",
        "formula": "hat_theta_D_plus_h = theta_D_minus_1",
        "historical_source_day": "D-1",
        "persistence_feature": persist_col,
        "trainable_coefficients": 0,
        "computation_duration_ms": duration,
        "n_train": int(len(train)),
        "n_validation": int(len(validation)),
    }
    writer.emit(
        event_type="training_completed",
        phase="fit",
        model="persistence",
        horizon_days=horizon,
        details={**diagnostics, "note": "Persistence is a non-trained forecasting baseline."},
    )
    return {
        "train_predictions": train_hat,
        "validation_predictions": val_hat,
        "diagnostics": diagnostics,
        "estimator": None,
        "payload": {"kind": "persistence", "feature": persist_col, "diagnostics": diagnostics},
    }


def _fit_seasonal(writer, train, validation, persist_col, hyperparameters, horizon, timings) -> dict[str, Any]:
    writer.emit(event_type="training_started", phase="fit", model="seasonal", horizon_days=horizon, details={"optimizer": "none"})
    start = time.monotonic()
    monthly = fit_seasonal_monthly(train)
    duration = int((time.monotonic() - start) * 1000)
    timings["seasonal_estimation"] = duration
    counts: Counter[int] = Counter()
    for _, row in train.iterrows():
        stamp = str(row.get("target_date_utc") or "")[:10]
        if stamp:
            counts[date.fromisoformat(stamp).month] += 1
    missing = [month for month in range(1, 13) if month not in monthly]
    train_hat = seasonal_predict(train, monthly)
    val_hat = seasonal_predict(validation, monthly)
    diagnostics = {
        "optimizer": "none",
        "training_iterations": 0,
        "convergence_status": "not_applicable",
        "iteration_history_available": False,
        "iteration_history_reason": "seasonal_mean_estimator",
        "method": hyperparameters.get("method"),
        "n_calendar_groups": len(monthly),
        "missing_seasonal_groups": missing,
        "observations_per_month": {str(k): int(v) for k, v in sorted(counts.items())},
        "monthly_means": {str(k): float(v) for k, v in sorted(monthly.items())},
        "estimation_duration_ms": duration,
        "n_train": int(len(train)),
        "training_period": "training partition only",
    }
    writer.emit(event_type="training_completed", phase="fit", model="seasonal", horizon_days=horizon, details={
        "n_calendar_groups": len(monthly),
        "missing_seasonal_groups": missing,
        "estimation_duration_ms": duration,
        "training_iterations": 0,
        "optimizer": "none",
    })
    return {
        "train_predictions": train_hat,
        "validation_predictions": val_hat,
        "diagnostics": diagnostics,
        "estimator": None,
        "payload": {"kind": "seasonal", "monthly_means": diagnostics["monthly_means"], "diagnostics": diagnostics},
    }


def _fit_ridge(writer, train, validation, columns, persist_col, hyperparameters, horizon, timings) -> dict[str, Any]:
    writer.emit(
        event_type="preprocessing_completed",
        phase="preprocessing",
        model="ridge",
        horizon_days=horizon,
        details={"scaler": "StandardScaler", "fitted_on": "training"},
    )
    pipe = ridge_pipeline(float(hyperparameters["alpha"]))
    writer.emit(
        event_type="training_started",
        phase="fit",
        model="ridge",
        horizon_days=horizon,
        details={"alpha": hyperparameters["alpha"], "solver": "auto", "n_features": len(columns), "n_train": int(len(train))},
    )
    start = time.monotonic()
    fit_sklearn(pipe, train, columns)
    duration = int((time.monotonic() - start) * 1000)
    timings["ridge_fit"] = duration
    ridge = pipe.named_steps["ridge"]
    scaler = pipe.named_steps["scaler"]
    n_iter = getattr(ridge, "n_iter_", None)
    if n_iter is not None:
        n_iter_value = [int(item) for item in np.atleast_1d(n_iter)]
    else:
        n_iter_value = None
    coef = [float(item) for item in np.asarray(ridge.coef_).tolist()]
    diagnostics = {
        "optimizer": f"ridge_{getattr(ridge, 'solver', 'auto')}",
        "training_iterations": None,
        "convergence_status": "solved" if n_iter_value is None else "solver_reported_n_iter",
        "iteration_history_available": False,
        "iteration_history_reason": "not_exposed_by_estimator",
        "alpha": float(ridge.alpha),
        "solver": str(getattr(ridge, "solver", "auto")),
        "fit_intercept": bool(ridge.fit_intercept),
        "n_features": len(columns),
        "fitted_coefficient_count": len(coef),
        "intercept": float(ridge.intercept_) if np.ndim(ridge.intercept_) == 0 else [float(x) for x in np.atleast_1d(ridge.intercept_)],
        "coefficients": [{"feature": columns[i], "value": coef[i]} for i in range(len(coef))],
        "scaler": "StandardScaler",
        "solver_n_iter": n_iter_value,
        "fitting_duration_ms": duration,
        "n_train": int(len(train)),
        "note": "Standard Ridge solves a regularized linear system. No epoch loss curve is recorded.",
    }
    train_hat = predict_sklearn(pipe, train, columns)
    val_hat = predict_sklearn(pipe, validation, columns)
    writer.emit(
        event_type="convergence_diagnostic",
        phase="fit",
        model="ridge",
        horizon_days=horizon,
        details={
            "iteration_history_available": False,
            "iteration_history_reason": "not_exposed_by_estimator",
            "solver": diagnostics["solver"],
            "solver_n_iter": n_iter_value,
        },
    )
    writer.emit(
        event_type="training_completed",
        phase="fit",
        model="ridge",
        horizon_days=horizon,
        details={"fitting_duration_ms": duration, "fitted_coefficient_count": len(coef), "alpha": float(ridge.alpha)},
    )
    return {
        "train_predictions": train_hat,
        "validation_predictions": val_hat,
        "diagnostics": diagnostics,
        "estimator": pipe,
        "payload": {
            "kind": "ridge",
            "estimator": pipe,
            "columns": columns,
            "alpha": float(ridge.alpha),
            "diagnostics": {key: diagnostics[key] for key in diagnostics if key != "coefficients"},
            "coefficients": diagnostics["coefficients"],
            "scaler_mean": [float(item) for item in np.asarray(scaler.mean_).tolist()],
            "scaler_scale": [float(item) for item in np.asarray(scaler.scale_).tolist()],
        },
    }


def _fit_boosting(writer, train, validation, columns, persist_col, hyperparameters, horizon, timings) -> dict[str, Any]:
    writer.emit(
        event_type="preprocessing_completed",
        phase="preprocessing",
        model="gradient_boosting",
        horizon_days=horizon,
        details={"scaler": None, "early_stopping": False},
    )
    estimator = boosting_estimator(
        max_depth=int(hyperparameters["max_depth"]),
        learning_rate=float(hyperparameters["learning_rate"]),
        max_iter=int(hyperparameters["max_iter"]),
        seed=int(hyperparameters["random_state"]),
    )
    writer.emit(
        event_type="training_started",
        phase="fit",
        model="gradient_boosting",
        horizon_days=horizon,
        details={
            "max_iter": hyperparameters["max_iter"],
            "learning_rate": hyperparameters["learning_rate"],
            "max_depth": hyperparameters["max_depth"],
            "early_stopping": False,
            "n_train": int(len(train)),
        },
    )
    start = time.monotonic()
    fit_sklearn(estimator, train, columns)
    duration = int((time.monotonic() - start) * 1000)
    timings["boosting_fit"] = duration
    n_iter = int(getattr(estimator, "n_iter_", hyperparameters["max_iter"]))
    native_train = np.asarray(getattr(estimator, "train_score_", []))
    native_val = np.asarray(getattr(estimator, "validation_score_", []))
    native_history = native_train.size > 0 or native_val.size > 0
    diagnostics = {
        "optimizer": "histogram_gradient_boosting",
        "training_iterations": n_iter,
        "max_iter": int(hyperparameters["max_iter"]),
        "n_iter_": n_iter,
        "learning_rate": float(hyperparameters["learning_rate"]),
        "max_depth": int(hyperparameters["max_depth"]),
        "early_stopping": False,
        "early_stopping_reason": "disabled_to_preserve_chronological_training_contract",
        "loss": "squared_error",
        "native_train_score_available": bool(native_train.size),
        "native_validation_score_available": bool(native_val.size),
        "iteration_history_available": True,
        "iteration_history_reason": None,
        "iteration_history_source": "staged_predict_after_fit",
        "iteration_history_note": (
            "Native train_score_ is empty because early_stopping is False. "
            "Stagewise MSE is measured after fitting via staged_predict on the training partition."
        ),
        "higher_is_better": False,
        "fitting_duration_ms": duration,
        "termination": "reached_max_iter" if n_iter >= int(hyperparameters["max_iter"]) else "stopped_before_max_iter",
        "n_train": int(len(train)),
    }
    if not native_history:
        diagnostics["native_score_reason"] = "empty_because_early_stopping_disabled"
    x_train, y_train = matrix(train, columns)
    stage_mses = []
    for index, pred in enumerate(estimator.staged_predict(x_train), start=1):
        mse = float(np.mean((y_train - pred) ** 2))
        if not np.isfinite(mse):
            continue
        stage_mses.append(mse)
        writer.emit(
            event_type="training_iteration",
            phase="fit",
            model="gradient_boosting",
            horizon_days=horizon,
            iteration=index,
            details={"source": "staged_predict_after_fit", "used_for_fitting": False},
        )
        writer.emit(
            event_type="training_metric",
            phase="fit",
            model="gradient_boosting",
            horizon_days=horizon,
            iteration=index,
            metric_name="training_mse",
            metric_value=mse,
            metric_unit="squared_m3_per_m3",
            dataset_partition="train",
            details={
                "calculation_method": "staged_predict_after_fit",
                "used_for_fitting": False,
                "optimization_objective": True,
                "directionality": "lower_is_better",
                "note": "Post-fit stagewise training-partition MSE. Not native train_score_.",
            },
        )
    diagnostics["staged_predict_points"] = len(stage_mses)
    train_hat = predict_sklearn(estimator, train, columns)
    val_hat = predict_sklearn(estimator, validation, columns)
    writer.emit(
        event_type="training_completed",
        phase="fit",
        model="gradient_boosting",
        horizon_days=horizon,
        details={
            "n_iter_": n_iter,
            "max_iter": int(hyperparameters["max_iter"]),
            "fitting_duration_ms": duration,
            "staged_predict_points": len(stage_mses),
        },
    )
    return {
        "train_predictions": train_hat,
        "validation_predictions": val_hat,
        "diagnostics": diagnostics,
        "estimator": estimator,
        "payload": {
            "kind": "gradient_boosting",
            "estimator": estimator,
            "columns": columns,
            "hyperparameters": hyperparameters,
            "diagnostics": diagnostics,
        },
    }


def _metric_records(train_metrics: dict[str, Any], val_metrics: dict[str, Any], *, algorithm: str, fitted: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    _ = algorithm, fitted
    for partition, metrics, computed in (
        ("train", train_metrics, "after_fitting"),
        ("validation", val_metrics, "after_fitting"),
    ):
        for name, unit, direction, objective in (
            ("mae", "m3_per_m3", "lower_is_better", False),
            ("rmse", "m3_per_m3", "lower_is_better", False),
            ("mbe", "m3_per_m3", "closer_to_zero", False),
            ("r2", "dimensionless", "higher_is_better", False),
            ("skill_mae", "dimensionless", "higher_is_better", False),
        ):
            value = metrics.get(name)
            if value is None:
                continue
            records.append({
                "metric_name": name,
                "metric_value": float(value),
                "metric_unit": unit,
                "dataset_partition": partition,
                "calculation_method": "aligned_metrics_after_fit",
                "sample_count": metrics.get("n"),
                "iteration": None,
                "directionality": direction,
                "computed_during": computed,
                "optimization_objective": objective,
                "emit_event": partition == "validation" and name in {"mae", "rmse", "skill_mae"},
            })
    return records


def _save_artifacts(*, writer, run_dir: Path, algorithm: str, fitted: dict[str, Any], val_scored, config, set_id, horizon) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    payload = fitted["payload"]
    artifact_dir = run_dir / "model_artifacts"
    if algorithm == "ridge":
        save_joblib(artifact_dir / "estimator.joblib", payload)
        artifacts["estimator"] = "model_artifacts/estimator.joblib"
        write_json_atomic(artifact_dir / "coefficients.json", {
            "alpha": payload.get("alpha"),
            "coefficients": payload.get("coefficients"),
            "intercept": fitted["diagnostics"].get("intercept"),
            "scaled": True,
            "note": "Coefficients are on StandardScaler units fitted on the training partition only.",
        })
        artifacts["coefficients"] = "model_artifacts/coefficients.json"
        writer.emit(event_type="artifact_saved", phase="saving", model=algorithm, horizon_days=horizon, details={"file": "model_artifacts/estimator.joblib"})
    elif algorithm == "gradient_boosting":
        save_joblib(artifact_dir / "estimator.joblib", payload)
        artifacts["estimator"] = "model_artifacts/estimator.joblib"
        writer.emit(event_type="artifact_saved", phase="saving", model=algorithm, horizon_days=horizon, details={"file": "model_artifacts/estimator.joblib"})
    elif algorithm == "seasonal":
        write_json_atomic(artifact_dir / "seasonal_means.json", payload)
        artifacts["seasonal_means"] = "model_artifacts/seasonal_means.json"
        writer.emit(event_type="artifact_saved", phase="saving", model=algorithm, horizon_days=horizon, details={"file": "model_artifacts/seasonal_means.json"})
    else:
        write_json_atomic(artifact_dir / "baseline.json", payload)
        artifacts["baseline"] = "model_artifacts/baseline.json"
        writer.emit(event_type="artifact_saved", phase="saving", model=algorithm, horizon_days=horizon, details={"file": "model_artifacts/baseline.json"})
    write_json_atomic(artifact_dir / "diagnostics.json", fitted["diagnostics"])
    artifacts["diagnostics"] = "model_artifacts/diagnostics.json"
    return artifacts
