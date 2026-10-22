"""Run the Phase 4.1 soil-forecasting experiment. No CDS. No operational predict API."""

from __future__ import annotations

import shutil
import sys
from datetime import datetime, timezone
from importlib import metadata
from itertools import product
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from ml.agricultural_ml.config import load_ml_config
from ml.agricultural_ml.pipeline import (
    _git_reference,
    audit_leakage,
    validate_dataset,
)
from ml.ingestion.manifest import now_iso, write_json_atomic
from ml.preprocessing.errors import MissingProcessedOutputError, SoilForecastingError
from ml.integration.satellite_weather import source_fingerprint
from ml.preprocessing.raster import project_root, read_json
from ml.soil_forecasting.config import (
    PIPELINE_VERSION,
    load_experiment_config,
    output_directory,
    source_directory,
)
from ml.soil_forecasting.dataset import (
    assert_documented_features,
    catalog_by_column,
    complete_mask,
    eligible_mask,
    enabled_feature_sets,
    load_joined_frame,
    partition_frame,
)
from ml.soil_forecasting.evaluate import (
    aligned_metrics,
    attach_predictions,
    physical_sanity,
    prediction_records,
    subset_metrics,
)
from ml.soil_forecasting.models import (
    boosting_estimator,
    fit_seasonal_monthly,
    fit_sklearn,
    load_joblib,
    persistence_predict,
    predict_sklearn,
    ridge_pipeline,
    save_joblib,
    seasonal_predict,
)


FROZEN_NAME = "frozen_experiment.json"
TEST_METRICS = "final_test_metrics.csv"


def check_experiment(config_path: Path | str, *, root: Path | None = None) -> dict[str, Any]:
    config = load_experiment_config(config_path)
    base = root or project_root()
    ml_path = base / str(config["source"]["ml_config"])
    dataset = validate_dataset(ml_path, root=base)
    leakage = audit_leakage(ml_path, root=base)
    if leakage.get("status") != "passed":
        raise SoilForecastingError("Phase 4.0 leakage audit is not passed. Training aborted.")
    source = source_directory(config, root=base)
    missing = [name for name in ("features_daily.csv", "targets.csv", "split_membership.csv") if not (source / name).is_file()]
    if missing:
        raise MissingProcessedOutputError(f"Phase 4.0 tables missing: {missing}")
    quality = read_json(source / "dataset_quality.json") if (source / "dataset_quality.json").is_file() else {}
    if quality.get("suitable_for_modeling") is True:
        raise SoilForecastingError("Refusing to train: source suitable_for_modeling is true.")
    ml_config = load_ml_config(ml_path)
    columns = sorted({col for cols in enabled_feature_sets(config).values() for col in cols})
    assert_documented_features(config, ml_config, columns)
    sklearn_version = metadata.version("scikit-learn")
    return {
        "ok": True,
        "experiment_id": config["experiment_id"],
        "dataset_id": dataset["dataset_id"],
        "leakage_status": leakage["status"],
        "suitable_for_modeling": False,
        "satellite_features_enabled": False,
        "sklearn_version": sklearn_version,
        "aoi_id": config["source"].get("aoi_id"),
        "network_used": False,
        "operational_forecast": False,
    }


def prepare_experiment(config_path: Path | str, *, root: Path | None = None) -> dict[str, Any]:
    config = load_experiment_config(config_path)
    check_experiment(config_path, root=root)
    base = root or project_root()
    source = source_directory(config, root=base)
    out = output_directory(config, root=base)
    out.mkdir(parents=True, exist_ok=True)
    ml_config = load_ml_config(base / str(config["source"]["ml_config"]))
    frame = load_joined_frame(source, target_variable=config["target"]["variable"])
    sets = enabled_feature_sets(config)
    catalog = catalog_by_column(ml_config)
    fingerprints = read_json(source / "source_fingerprints.json") if (source / "source_fingerprints.json").is_file() else {}
    provenance = _provenance_audit(source)
    counts = []
    for horizon in config["target"]["horizons_days"]:
        for split in ("training", "validation", "test"):
            for set_id, columns in sets.items():
                part = partition_frame(frame, split=split, horizon=horizon, columns=columns)
                counts.append({
                    "split": split,
                    "horizon_days": horizon,
                    "feature_set": set_id,
                    "n": int(len(part)),
                    "purged_or_missing": int(
                        ((frame["horizon_days"] == horizon) & (frame["split"] == split)).sum() - len(part)
                    ),
                })
    feature_docs = []
    for set_id, columns in sets.items():
        for column in columns:
            item = dict(catalog[column])
            item["feature_set"] = set_id
            feature_docs.append(item)
    snapshot = {key: value for key, value in config.items() if not str(key).startswith("_")}
    (out / "experiment_config_snapshot.yaml").write_text(
        yaml.safe_dump(snapshot, sort_keys=False), encoding="utf-8",
    )
    write_json_atomic(out / "data_fingerprint.json", _data_fingerprint(source, fingerprints, config))
    write_json_atomic(out / "feature_selection.json", {
        "primary_feature_set": config.get("primary_feature_set"),
        "satellite_excluded": True,
        "satellite_reason": (config.get("feature_sets") or {}).get("D", {}).get("reason"),
        "catalog_extensions_phase_4_1": ["temp_mean_prev_7d_c", "day_of_year_cos"],
        "features": feature_docs,
    })
    write_json_atomic(out / "provenance_audit.json", provenance)
    write_json_atomic(out / "prepared_summary.json", {
        "experiment_id": config["experiment_id"],
        "n_joined_rows": int(len(frame)),
        "eligible_rows": int(eligible_mask(frame).sum()),
        "counts": counts,
        "generated_at_utc": now_iso(),
    })
    frame.to_csv(out / "joined_modeling_frame.csv", index=False)
    return {"ok": True, "output_directory": str(out), "counts": counts}


def train_models(config_path: Path | str, *, root: Path | None = None) -> dict[str, Any]:
    config = load_experiment_config(config_path)
    base = root or project_root()
    out = output_directory(config, root=base)
    if not (out / "joined_modeling_frame.csv").is_file():
        prepare_experiment(config_path, root=root)
    frame = pd.read_csv(out / "joined_modeling_frame.csv")
    sets = enabled_feature_sets(config)
    seed = int(config.get("random_seed") or 42)
    model_dir = out / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    trained = []
    for horizon in config["target"]["horizons_days"]:
        persist_col = config["target"]["persistence_feature"]
        train_c = partition_frame(frame, split="training", horizon=horizon, columns=sets["C"])
        seasonal = fit_seasonal_monthly(train_c if len(train_c) else partition_frame(
            frame, split="training", horizon=horizon, columns=[persist_col],
        ))
        seasonal_path = model_dir / f"seasonal_h{horizon}.json"
        write_json_atomic(seasonal_path, {
            "method": "training_year_monthly_mean",
            "label": "training_year_seasonal_reference",
            "horizon_days": horizon,
            "monthly_means": {str(k): v for k, v in seasonal.items()},
            "n_train": int(len(train_c)),
            "fitted_on": "training",
        })
        trained.append({"model_id": "seasonal", "horizon_days": horizon, "path": seasonal_path.name, "n_train": int(len(train_c))})
        ridge_cfg = config["models"]["ridge"]
        gb_cfg = config["models"]["gradient_boosting"]
        for set_id in ridge_cfg.get("feature_sets") or ["C"]:
            columns = sets[set_id]
            train = partition_frame(frame, split="training", horizon=horizon, columns=columns)
            for alpha in ridge_cfg.get("alphas") or [1.0]:
                pipe = ridge_pipeline(float(alpha))
                fit_sklearn(pipe, train, columns)
                path = model_dir / f"ridge_h{horizon}_{set_id}_alpha{alpha}.joblib"
                save_joblib(path, {
                    "estimator": pipe,
                    "columns": columns,
                    "feature_set": set_id,
                    "horizon_days": horizon,
                    "alpha": float(alpha),
                    "n_train": int(len(train)),
                    "fitted_on": "training",
                })
                trained.append({"model_id": "ridge", "horizon_days": horizon, "feature_set": set_id, "alpha": float(alpha), "n_train": int(len(train)), "path": path.name})
            grid = gb_cfg.get("grid") or {}
            for depth, rate, n_iter in product(
                grid.get("max_depth") or [3],
                grid.get("learning_rate") or [0.1],
                grid.get("max_iter") or [100],
            ):
                est = boosting_estimator(max_depth=depth, learning_rate=rate, max_iter=n_iter, seed=seed)
                fit_sklearn(est, train, columns)
                path = model_dir / f"gb_h{horizon}_{set_id}_d{depth}_lr{rate}_n{n_iter}.joblib"
                save_joblib(path, {
                    "estimator": est,
                    "columns": columns,
                    "feature_set": set_id,
                    "horizon_days": horizon,
                    "max_depth": int(depth),
                    "learning_rate": float(rate),
                    "max_iter": int(n_iter),
                    "n_train": int(len(train)),
                    "fitted_on": "training",
                    "random_seed": seed,
                })
                trained.append({
                    "model_id": "gradient_boosting", "horizon_days": horizon, "feature_set": set_id,
                    "max_depth": int(depth), "learning_rate": float(rate), "max_iter": int(n_iter),
                    "n_train": int(len(train)), "path": path.name,
                })
    summary = {
        "experiment_id": config["experiment_id"],
        "fitted_on": "training",
        "validation_used_for_fitting": False,
        "test_used_for_fitting": False,
        "trained": trained,
        "generated_at_utc": now_iso(),
        "git": _git_reference(base),
        "versions": _versions(),
        "random_seed": seed,
    }
    write_json_atomic(out / "training_summary.json", summary)
    return {"ok": True, "n_artifacts": len(trained)}


def validate_models(config_path: Path | str, *, root: Path | None = None) -> dict[str, Any]:
    return _score_partition(config_path, split="validation", root=root, allow_test=False)


def compare_models(config_path: Path | str, *, root: Path | None = None) -> dict[str, Any]:
    config = load_experiment_config(config_path)
    out = output_directory(config, root=root)
    frozen_path = out / FROZEN_NAME
    if frozen_path.is_file():
        existing = read_json(frozen_path)
        if existing.get("test_consulted"):
            raise SoilForecastingError(
                "compare cannot overwrite a freeze after the 2025 holdout was consulted."
            )
    metrics_path = out / "validation_metrics.csv"
    if not metrics_path.is_file():
        validate_models(config_path, root=root)
    metrics = pd.read_csv(metrics_path)
    primary = str(config.get("primary_feature_set") or "C")
    selected = []
    comparison_rows = []
    for horizon in config["target"]["horizons_days"]:
        block = metrics[(metrics["horizon_days"] == horizon) & (metrics["partition"] == "validation")]
        persist = block[block["model_id"] == "persistence"]
        if persist.empty:
            raise SoilForecastingError(f"Persistence metrics missing for horizon {horizon}.")
        persist_row = persist.iloc[0].to_dict()
        for model_id in ("persistence", "seasonal", "ridge", "gradient_boosting"):
            family = block[block["model_id"] == model_id]
            if family.empty:
                continue
            preferred = family[family["feature_set"] == primary] if "feature_set" in family.columns else family
            pool = preferred if not preferred.empty else family
            pool = pool.copy()
            pool["mae"] = pd.to_numeric(pool["mae"], errors="coerce")
            winner = pool.sort_values("mae", kind="mergesort").iloc[0].to_dict()
            selected.append(winner)
            comparison_rows.append(winner)
            if model_id in {"ridge", "gradient_boosting"}:
                other = family[family["feature_set"] != primary]
                if not other.empty:
                    other = other.copy()
                    other["mae"] = pd.to_numeric(other["mae"], errors="coerce")
                    comparison_rows.append(other.sort_values("mae", kind="mergesort").iloc[0].to_dict())
        _ = persist_row
    comparison = pd.DataFrame(comparison_rows)
    comparison.to_csv(out / "model_comparison.csv", index=False)
    freeze = {
        "experiment_id": config["experiment_id"],
        "frozen_at_utc": now_iso(),
        "stage": "frozen_for_test",
        "config_fingerprint": config["_config_fingerprint"],
        "pipeline_version": PIPELINE_VERSION,
        "selection_criterion": "validation_mae",
        "primary_feature_set": primary,
        "test_consulted": False,
        "fitted_on": "training_partition_only",
        "selected": _jsonable(selected),
        "git": _git_reference(root or project_root()),
    }
    write_json_atomic(out / FROZEN_NAME, freeze)
    write_selected_validation_analysis(config_path, root=root)
    _write_limitations(out, config, metrics)
    write_json_atomic(out / "experiment_manifest.json", {
        "experiment_id": config["experiment_id"],
        "pipeline_version": PIPELINE_VERSION,
        "config_fingerprint": config["_config_fingerprint"],
        "frozen": True,
        "label": "Research experiment on ERA5-Land modeled soil moisture. Not operational. Not field-validated.",
        "generated_at_utc": now_iso(),
    })
    return {"ok": True, "frozen": True, "n_selected": len(selected)}


def evaluate_test(config_path: Path | str, *, root: Path | None = None) -> dict[str, Any]:
    config = load_experiment_config(config_path)
    out = output_directory(config, root=root)
    frozen_path = out / FROZEN_NAME
    if not frozen_path.is_file():
        raise SoilForecastingError("evaluate-test requires frozen_experiment.json from compare.")
    frozen = read_json(frozen_path)
    if frozen.get("config_fingerprint") != config["_config_fingerprint"]:
        raise SoilForecastingError("Frozen configuration fingerprint does not match the current config.")
    if frozen.get("test_consulted") and (out / TEST_METRICS).is_file():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        repeats = out / "repeats"
        repeats.mkdir(exist_ok=True)
        shutil.copy2(out / TEST_METRICS, repeats / f"final_test_metrics_{stamp}.csv")
        if (out / "final_test_predictions.csv").is_file():
            shutil.copy2(out / "final_test_predictions.csv", repeats / f"final_test_predictions_{stamp}.csv")
        log = {
            "repeat": True,
            "original_preserved": True,
            "repeat_at_utc": now_iso(),
            "note": "Original held-out record was preserved. This invocation is a documented repeat.",
        }
        write_json_atomic(out / "test_evaluation_log.json", log)
        return {"ok": True, "repeat": True, "original_preserved": True}
    result = _score_partition(
        config_path, split="test", root=root, allow_test=True, selected=frozen.get("selected") or [],
    )
    frozen["test_consulted"] = True
    frozen["test_evaluated_at_utc"] = now_iso()
    write_json_atomic(frozen_path, frozen)
    write_json_atomic(out / "test_evaluation_log.json", {
        "repeat": False,
        "test_evaluated_at_utc": frozen["test_evaluated_at_utc"],
        "config_fingerprint": config["_config_fingerprint"],
        "n": result.get("n_prediction_rows"),
    })
    return result


def write_selected_validation_analysis(config_path: Path | str, *, root: Path | None = None) -> dict[str, Any]:
    """Score frozen selected models on validation only. Does not refit or touch test artifacts."""
    config = load_experiment_config(config_path)
    out = output_directory(config, root=root)
    frozen_path = out / FROZEN_NAME
    if not frozen_path.is_file():
        raise SoilForecastingError("Selected analysis requires frozen_experiment.json.")
    frozen = read_json(frozen_path)
    return _score_partition(
        config_path,
        split="validation",
        root=root,
        allow_test=False,
        selected=frozen.get("selected") or [],
        predictions_filename="selected_validation_predictions.csv",
        metrics_filename=None,
        analysis_filename="error_analysis.json",
        selected_only=True,
    )


def report_experiment(config_path: Path | str, *, root: Path | None = None) -> dict[str, Any]:
    config = load_experiment_config(config_path)
    out = output_directory(config, root=root)
    if (out / FROZEN_NAME).is_file() and (out / "training_summary.json").is_file():
        write_selected_validation_analysis(config_path, root=root)
    payload = {
        "experiment_id": config["experiment_id"],
        "label": "Research experiment on ERA5-Land modeled soil moisture. Not operational.",
        "frozen": (out / FROZEN_NAME).is_file(),
        "test_evaluated": (out / TEST_METRICS).is_file(),
        "suitable_for_modeling": False,
        "trained_model_present": (out / "training_summary.json").is_file(),
        "config_fingerprint": config["_config_fingerprint"],
    }
    if (out / "model_comparison.csv").is_file():
        payload["validation_comparison"] = pd.read_csv(out / "model_comparison.csv").to_dict(orient="records")
    if (out / TEST_METRICS).is_file():
        payload["final_test_metrics"] = pd.read_csv(out / TEST_METRICS).to_dict(orient="records")
    write_json_atomic(out / "experiment_summary.json", _jsonable(payload))
    return payload


def _score_partition(
    config_path: Path | str,
    *,
    split: str,
    root: Path | None,
    allow_test: bool,
    selected: list[dict[str, Any]] | None = None,
    predictions_filename: str | None = None,
    metrics_filename: str | None = None,
    analysis_filename: str | None = None,
    selected_only: bool = False,
) -> dict[str, Any]:
    if split == "test" and not allow_test:
        raise SoilForecastingError("Test partition cannot be scored during development commands.")
    config = load_experiment_config(config_path)
    out = output_directory(config, root=root)
    if not (out / "training_summary.json").is_file():
        raise SoilForecastingError("train must run before scoring.")
    frame = pd.read_csv(out / "joined_modeling_frame.csv")
    sets = enabled_feature_sets(config)
    persist_col = config["target"]["persistence_feature"]
    primary = str(config.get("matched_comparison_feature_set") or "C")
    eval_cfg = config.get("evaluation") or {}
    tolerance = float(eval_cfg.get("direction_tolerance") or 1e-4)
    records = []
    metric_rows = []
    candidates = selected if selected else _all_candidates(out, config)
    for horizon in config["target"]["horizons_days"]:
        matched = partition_frame(frame, split=split, horizon=horizon, columns=sets[primary])
        if matched.empty:
            continue
        persist_hat = persistence_predict(matched, persist_col)
        persist_frame = attach_predictions(matched, persist_hat, persistence_feature=persist_col)
        records.extend(prediction_records(
            persist_frame, model_id="persistence", feature_set=primary, partition=split, config=config,
        ))
        metric_rows.append(_metric_row(config, "persistence", primary, split, horizon, persist_frame, persist_col, tolerance, extra={"n_train": 0}))
        for candidate in candidates:
            if int(candidate.get("horizon_days") or horizon) != horizon:
                continue
            model_id = str(candidate.get("model_id"))
            if model_id == "persistence":
                continue
            set_id = str(candidate.get("feature_set") or primary)
            columns = sets.get(set_id) or sets[primary]
            scored = matched if set_id == primary else matched.loc[complete_mask(matched, columns)].copy()
            predicted = _predict_candidate(out, candidate, scored, columns, persist_col)
            scored = attach_predictions(scored, predicted, persistence_feature=persist_col)
            extra = {key: candidate.get(key) for key in ("alpha", "max_depth", "learning_rate", "max_iter", "path", "n_train") if key in candidate}
            records.extend(prediction_records(
                scored, model_id=model_id, feature_set=set_id, partition=split, config=config, extra=extra,
            ))
            metric_rows.append(_metric_row(config, model_id, set_id, split, horizon, scored, persist_col, tolerance, extra=extra))
    pred_df = pd.DataFrame(records)
    metrics_df = pd.DataFrame(metric_rows)
    if split == "validation":
        pred_name = predictions_filename or "validation_predictions.csv"
        pred_df.to_csv(out / pred_name, index=False)
        if metrics_filename or not selected_only:
            metrics_df.to_csv(out / (metrics_filename or "validation_metrics.csv"), index=False)
        if analysis_filename or selected_only:
            _write_analysis(
                out, pred_df, config, partition="validation",
                name=analysis_filename or "error_analysis.json",
                selected_only=selected_only,
            )
    elif split == "test":
        pred_df.to_csv(out / (predictions_filename or "final_test_predictions.csv"), index=False)
        metrics_df.to_csv(out / (metrics_filename or TEST_METRICS), index=False)
        _write_analysis(
            out, pred_df, config, partition="test",
            name=analysis_filename or "test_error_analysis.json",
            selected_only=True,
        )
        sanity = physical_sanity(
            pred_df["prediction"], pred_df["observed_modeled_target"],
            pred_df["persistence_prediction"], config,
        )
        write_json_atomic(out / "physical_sanity_report.json", sanity)
    return {"ok": True, "partition": split, "n_prediction_rows": int(len(pred_df)), "n_metric_rows": int(len(metrics_df))}


def _predict_candidate(out: Path, candidate: dict[str, Any], frame, columns: list[str], persist_col: str):
    model_id = candidate.get("model_id")
    if model_id == "seasonal":
        path = out / "models" / f"seasonal_h{int(candidate['horizon_days'])}.json"
        payload = read_json(path) if path.is_file() else read_json(out / "models" / candidate["path"])
        monthly = {int(k): float(v) for k, v in (payload.get("monthly_means") or {}).items()}
        return seasonal_predict(frame, monthly)
    if model_id in {"ridge", "gradient_boosting"}:
        payload = load_joblib(out / "models" / str(candidate["path"]))
        return predict_sklearn(payload["estimator"], frame, payload.get("columns") or columns)
    return persistence_predict(frame, persist_col)


def _all_candidates(out: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    summary = read_json(out / "training_summary.json")
    candidates = list(summary.get("trained") or [])
    primary = config.get("primary_feature_set") or "C"
    for horizon in config["target"]["horizons_days"]:
        candidates.append({
            "model_id": "persistence",
            "horizon_days": horizon,
            "feature_set": primary,
        })
    return candidates


def _metric_row(config, model_id, feature_set, split, horizon, frame, persist_col, tolerance, extra=None):
    metrics = aligned_metrics(
        frame["absolute_target"], frame["prediction"],
        frame[persist_col], frame[persist_col],
        direction_tolerance=tolerance,
    )
    row = {
        "experiment_id": config["experiment_id"],
        "model_id": model_id,
        "feature_set": feature_set,
        "partition": split,
        "horizon_days": horizon,
        "target_variable": config["target"]["variable"],
        "target_source_kind": "modeled_reanalysis",
        "is_ground_truth": False,
        **metrics,
        **(extra or {}),
    }
    return row


def _write_analysis(
    out: Path,
    predictions: pd.DataFrame,
    config: dict[str, Any],
    *,
    partition: str,
    name: str,
    selected_only: bool = False,
) -> None:
    part = predictions[predictions["partition"] == partition].copy() if "partition" in predictions.columns else predictions
    persist = config["target"]["persistence_feature"]
    if persist not in part.columns and "persistence_prediction" in part.columns:
        part[persist] = part["persistence_prediction"]
    if "absolute_target" not in part.columns and "observed_modeled_target" in part.columns:
        part["absolute_target"] = part["observed_modeled_target"]
    questions = _error_questions(part, config)
    subsets: list[dict[str, Any]] = []
    if persist in part.columns:
        pooled = subset_metrics(part, config)
        for row in pooled:
            row["model_id"] = "pooled_selected" if selected_only else "pooled"
            subsets.append(row)
        if "model_id" in part.columns:
            for model_id, group in part.groupby("model_id", sort=True):
                for row in subset_metrics(group, config):
                    row["model_id"] = str(model_id)
                    subsets.append(row)
    write_json_atomic(out / name, {
        "partition": partition,
        "selected_only": selected_only,
        "generated_at_utc": now_iso(),
        "subsets": subsets,
        "questions": questions,
        "note": (
            "Subset metrics use frozen selected models on matched complete-case rows. "
            "Pooled rows mix families; per-model rows are the interpretable diagnostics."
            if selected_only else
            "Subset metrics may include every candidate unless selected_only is true."
        ),
    })


def _error_questions(frame: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    def skill(model_id: str, horizon: int) -> float | None:
        block = frame[(frame["model_id"] == model_id) & (frame["horizon_days"] == horizon)]
        pers = frame[(frame["model_id"] == persistence_id()) & (frame["horizon_days"] == horizon)]
        if block.empty or pers.empty:
            return None
        from ml.agricultural_ml.metrics import mae, skill_versus_persistence
        return skill_versus_persistence(
            mae(block["observed_modeled_target"], block["prediction"]),
            mae(pers["observed_modeled_target"], pers["persistence_prediction"]),
        )

    def persistence_id() -> str:
        return "persistence"

    persist_h = {
        str(h): _mae(frame, "persistence", h) for h in config["target"]["horizons_days"]
    }
    return {
        "persistence_mae_by_horizon": persist_h,
        "persistence_better_at_h1_than_h7": _less(persist_h.get("1"), persist_h.get("7")),
        "ridge_skill_h1": skill("ridge", 1),
        "ridge_skill_h7": skill("ridge", 7),
        "gradient_boosting_skill_h1": skill("gradient_boosting", 1),
        "note": "Values are computed from this partition only. They are research metrics on modeled ERA5-Land targets.",
    }


def _mae(frame: pd.DataFrame, model_id: str, horizon: int) -> float | None:
    from ml.agricultural_ml.metrics import mae
    block = frame[(frame["model_id"] == model_id) & (frame["horizon_days"] == horizon)]
    if block.empty:
        return None
    pred_col = "prediction" if "prediction" in block.columns else "persistence_prediction"
    obs_col = "observed_modeled_target" if "observed_modeled_target" in block.columns else "absolute_target"
    return mae(block[obs_col], block[pred_col])


def _less(a, b):
    if a is None or b is None:
        return None
    return a < b


def _write_limitations(out: Path, config: dict[str, Any], metrics: pd.DataFrame) -> None:
    write_json_atomic(out / "research_limitations.json", {
        "three_years_only": True,
        "one_training_year": True,
        "serial_dependence": True,
        "shared_era5_land_ancestry": True,
        "coarse_grid": True,
        "not_field_validated": True,
        "not_operational": True,
        "block_bootstrap_deferred": True,
        "satellite_excluded": True,
        "suitable_for_modeling": False,
        "sample_counts": metrics[["model_id", "feature_set", "horizon_days", "n"]].to_dict(orient="records") if not metrics.empty else [],
        "label": "Proof-of-concept research on modeled reanalysis soil moisture.",
    })


def _data_fingerprint(source: Path, fingerprints: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    tables = {}
    for name in ("features_daily.csv", "targets.csv", "split_membership.csv", "dataset_manifest.json"):
        path = source / name
        if path.is_file():
            tables[name] = source_fingerprint(path)
    return {
        "source_fingerprints": fingerprints,
        "config_fingerprint": config["_config_fingerprint"],
        "ml_tables": tables,
        "features_daily_sha256": tables.get("features_daily.csv"),
        "generated_at_utc": now_iso(),
        "note": "features_daily_sha256 is the Phase 4.0 features table, not daily_weather.csv.",
    }


def _provenance_audit(source: Path) -> dict[str, Any]:
    quality_path = project_root() / "data" / "processed" / "satellite" / "plovdiv_2023_2025" / "quality" / "dataset_quality.json"
    n_dt = 0
    n_scenes = 0
    if quality_path.is_file():
        payload = read_json(quality_path)
        scenes = payload.get("scenes") or []
        n_scenes = len(scenes)
        n_dt = sum(1 for item in scenes if item.get("acquisition_datetime"))
    return {
        "satellite_acquisition_datetime_present": n_dt,
        "satellite_scenes": n_scenes,
        "satellite_timestamps": "synthesized_midnight_utc_from_date_only" if n_dt == 0 else "mixed",
        "satellite_used_in_phase_4_1": False,
        "aoi_id": "plovdiv_test",
        "aoi_canonical": True,
        "aoi_note": "plovdiv_test is the registry identity for the Plovdiv study AOI. Source archives were not rewritten.",
        "source_dataset_dir": str(source),
    }


def _versions() -> dict[str, str]:
    names = ["scikit-learn", "numpy", "pandas", "joblib"]
    versions = {"python": sys.version.split()[0]}
    for name in names:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = "missing"
    return versions


def _jsonable(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if hasattr(value, "item") and callable(value.item):
        try:
            return value.item()
        except Exception:
            return str(value)
    if pd.isna(value) if not isinstance(value, (list, dict)) else False:
        return None
    return value
