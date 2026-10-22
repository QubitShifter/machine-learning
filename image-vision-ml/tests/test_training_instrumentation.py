from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from ml.ingestion.manifest import write_json_atomic
from ml.preprocessing.errors import SoilForecastingError
from ml.soil_forecasting.training_instrumentation import execute_train_run
from scripts.soil_forecasting_experiment import main as forecast_main


FEATURE_C = [
    "swvl1_prev1",
    "swvl1_prev3d_mean",
    "swvl1_prev7d_mean",
    "swvl1_delta_prev1",
    "precip_prev_7d_mm",
    "day_of_year_sin",
    "day_of_year_cos",
]


def _config_yaml(tmp_path: Path, experiment_dir: Path) -> Path:
    payload = yaml.safe_load(Path("configs/soil_forecasting_experiment.yaml").read_text(encoding="utf-8"))
    payload["experiment_id"] = "telemetry_fixture_v1"
    payload["output"] = {"directory": str(experiment_dir)}
    payload["feature_sets"]["C"]["columns"] = FEATURE_C
    path = tmp_path / "experiment.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _row(split: str, issue: str, horizon: int, moisture: float, rain: float) -> dict:
    year_frac = int(issue[5:7]) / 12.0
    return {
        "issue_date_utc": issue,
        "target_date_utc": issue,  # simplified; tests do not evaluate target-date leakage here
        "horizon_days": horizon,
        "split": split,
        "excluded_flag": False,
        "target_available_flag": True,
        "absolute_target": moisture,
        "change_target": 0.01,
        "target_variable": "swvl1",
        "swvl1_prev1": moisture - 0.01,
        "swvl1_prev3d_mean": moisture - 0.008,
        "swvl1_prev7d_mean": moisture - 0.006,
        "swvl1_delta_prev1": 0.002,
        "precip_prev_7d_mm": rain,
        "day_of_year_sin": year_frac,
        "day_of_year_cos": 1.0 - year_frac,
    }


def _joined_frame() -> pd.DataFrame:
    rows = []
    for day in range(1, 41):
        rows.append(_row("training", f"2023-03-{day:02d}" if day <= 31 else f"2023-04-{day - 31:02d}", 1, 0.20 + day * 0.001, float(day % 5)))
    # March has 31 days; days 32-40 -> April 1-9
    rows = []
    for day in range(1, 32):
        rows.append(_row("training", f"2023-03-{day:02d}", 1, 0.18 + day * 0.002, float(day % 6)))
    for day in range(1, 16):
        rows.append(_row("training", f"2023-04-{day:02d}", 1, 0.22 + day * 0.001, float(day % 4)))
    for day in range(1, 21):
        rows.append(_row("validation", f"2024-03-{day:02d}", 1, 0.21 + day * 0.0015, float(day % 5)))
    for day in range(1, 6):
        rows.append(_row("test", f"2025-03-{day:02d}", 1, 0.99, 999.0))
    return pd.DataFrame(rows)


def _experiment(tmp_path: Path) -> tuple[Path, Path, str]:
    experiment_dir = tmp_path / "experiments" / "telemetry_fixture_v1"
    experiment_dir.mkdir(parents=True)
    frame = _joined_frame()
    frame.to_csv(experiment_dir / "joined_modeling_frame.csv", index=False)
    frozen = {"experiment_id": "telemetry_fixture_v1", "frozen": True, "test_consulted": True, "selected": []}
    write_json_atomic(experiment_dir / "frozen_experiment.json", frozen)
    (experiment_dir / "final_test_metrics.csv").write_text("model_id,mae\npersistence,0.02\n", encoding="utf-8")
    write_json_atomic(experiment_dir / "training_summary.json", {"fitted_on": "training", "trained": ["frozen"]})
    write_json_atomic(experiment_dir / "data_fingerprint.json", {
        "features_daily_sha256": {"sha256": "fixture-features"},
    })
    config = _config_yaml(tmp_path, experiment_dir)
    return config, experiment_dir, hashlib.sha256((experiment_dir / "frozen_experiment.json").read_bytes()).hexdigest()


def _events(run_dir: Path) -> list[dict]:
    rows = []
    for line in (run_dir / "training_events.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def test_train_run_requires_telemetry_flag(tmp_path: Path):
    config, _experiment_dir, _digest = _experiment(tmp_path)
    with pytest.raises(SoilForecastingError, match="telemetry"):
        execute_train_run(config, model="ridge", horizon=1, feature_set="C", telemetry=False)


def test_cli_train_run_without_flag_fails(tmp_path: Path):
    config, _experiment_dir, _digest = _experiment(tmp_path)
    assert forecast_main(["train-run", "--config", str(config), "--model", "ridge", "--horizon", "1"]) == 1


def test_persistence_has_no_invented_iterations(tmp_path: Path):
    config, experiment_dir, digest = _experiment(tmp_path)
    result = execute_train_run(config, model="persistence", horizon=1, feature_set="C", telemetry=True)
    run_dir = experiment_dir / "runs" / result["run_id"]
    summary = json.loads((run_dir / "training_summary.json").read_text(encoding="utf-8"))
    diagnostics = summary["diagnostics"]
    assert diagnostics["training_iterations"] == 0
    assert diagnostics["optimizer"] == "none"
    assert diagnostics["convergence_status"] == "not_applicable"
    events = _events(run_dir)
    assert not any(item["event_type"] == "training_iteration" for item in events)
    assert hashlib.sha256((experiment_dir / "frozen_experiment.json").read_bytes()).hexdigest() == digest
    assert result["test_targets_accessed"] is False


def test_seasonal_has_no_optimization_curve(tmp_path: Path):
    config, experiment_dir, _digest = _experiment(tmp_path)
    result = execute_train_run(config, model="seasonal", horizon=1, feature_set="C", telemetry=True)
    run_dir = experiment_dir / "runs" / result["run_id"]
    diagnostics = json.loads((run_dir / "training_summary.json").read_text(encoding="utf-8"))["diagnostics"]
    assert diagnostics["optimizer"] == "none"
    assert diagnostics["training_iterations"] == 0
    assert diagnostics["n_calendar_groups"] >= 1
    events = _events(run_dir)
    assert not any(item["event_type"] == "training_iteration" for item in events)
    assert not any(item.get("metric_name") == "training_loss" for item in events)


def test_ridge_records_fit_metadata_without_epoch_curve(tmp_path: Path):
    config, experiment_dir, digest = _experiment(tmp_path)
    before_test = (experiment_dir / "final_test_metrics.csv").read_bytes()
    result = execute_train_run(
        config, model="ridge", horizon=1, feature_set="C", telemetry=True, alpha=1.0,
    )
    run_dir = experiment_dir / "runs" / result["run_id"]
    diagnostics = json.loads((run_dir / "training_summary.json").read_text(encoding="utf-8"))["diagnostics"]
    assert diagnostics["iteration_history_available"] is False
    assert diagnostics["iteration_history_reason"] == "not_exposed_by_estimator"
    assert diagnostics["fitted_coefficient_count"] == len(FEATURE_C)
    assert diagnostics["alpha"] == pytest.approx(1.0)
    assert diagnostics["fitting_duration_ms"] >= 0
    assert diagnostics["training_iterations"] is None
    events = _events(run_dir)
    assert not any(item["event_type"] == "training_iteration" for item in events)
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    train_mae = next(item for item in metrics["records"] if item["metric_name"] == "mae" and item["dataset_partition"] == "train")
    val_mae = next(item for item in metrics["records"] if item["metric_name"] == "mae" and item["dataset_partition"] == "validation")
    assert train_mae["optimization_objective"] is False
    assert val_mae["calculation_method"] == "aligned_metrics_after_fit"
    assert (experiment_dir / "final_test_metrics.csv").read_bytes() == before_test
    assert hashlib.sha256((experiment_dir / "frozen_experiment.json").read_bytes()).hexdigest() == digest
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["is_frozen_phase_4_1_model"] is False
    assert manifest["test_targets_accessed"] is False
    assert manifest["suitable_for_modeling"] is False


def test_gradient_boosting_records_actual_n_iter_and_staged_history(tmp_path: Path):
    config, experiment_dir, _digest = _experiment(tmp_path)
    result = execute_train_run(
        config,
        model="gradient_boosting",
        horizon=1,
        feature_set="C",
        telemetry=True,
        max_iter=8,
        max_depth=2,
        learning_rate=0.1,
        seed=42,
    )
    run_dir = experiment_dir / "runs" / result["run_id"]
    diagnostics = json.loads((run_dir / "training_summary.json").read_text(encoding="utf-8"))["diagnostics"]
    assert diagnostics["n_iter_"] == 8
    assert diagnostics["training_iterations"] == 8
    assert diagnostics["early_stopping"] is False
    assert diagnostics["native_train_score_available"] is False
    assert diagnostics["iteration_history_source"] == "staged_predict_after_fit"
    events = _events(run_dir)
    iterations = [item for item in events if item["event_type"] == "training_iteration"]
    assert len(iterations) == 8
    mses = [item["metric_value"] for item in events if item.get("metric_name") == "training_mse"]
    assert len(mses) == 8
    assert all(isinstance(value, float) for value in mses)
    # Do not invent extra in-between points.
    assert [item["iteration"] for item in iterations] == list(range(1, 9))
    assert result["test_targets_accessed"] is False


def test_development_run_does_not_access_test_split(tmp_path: Path, monkeypatch):
    config, experiment_dir, _digest = _experiment(tmp_path)
    requested = []
    from ml.soil_forecasting import training_instrumentation as inst
    original = inst.partition_frame

    def wrapped(frame, *, split, horizon, columns, require_complete=True):
        requested.append(split)
        if split == "test":
            raise AssertionError("test partition requested")
        return original(frame, split=split, horizon=horizon, columns=columns, require_complete=require_complete)

    monkeypatch.setattr(inst, "partition_frame", wrapped)
    execute_train_run(config, model="ridge", horizon=1, feature_set="C", telemetry=True, alpha=1.0)
    assert "test" not in requested
    assert set(requested) <= {"training", "validation"}
    runs = list((experiment_dir / "runs").iterdir())
    assert len(runs) == 1
    preds = pd.read_csv(runs[0] / "validation_predictions.csv")
    assert "2025" not in preds["issue_date_utc"].astype(str).str.slice(0, 4).tolist()


def test_run_directories_are_unique_and_source_archive_untouched(tmp_path: Path):
    config, experiment_dir, digest = _experiment(tmp_path)
    first = execute_train_run(config, model="ridge", horizon=1, feature_set="C", telemetry=True, alpha=1.0)
    second = execute_train_run(config, model="ridge", horizon=1, feature_set="C", telemetry=True, alpha=1.0)
    assert first["run_id"] != second["run_id"]
    assert hashlib.sha256((experiment_dir / "frozen_experiment.json").read_bytes()).hexdigest() == digest
    assert json.loads((experiment_dir / "training_summary.json").read_text(encoding="utf-8"))["trained"] == ["frozen"]


def test_failed_run_is_not_completed(tmp_path: Path, monkeypatch):
    config, experiment_dir, _digest = _experiment(tmp_path)
    from ml.soil_forecasting import training_instrumentation as inst

    def boom(*_args, **_kwargs):
        raise SoilForecastingError("synthetic fit failure")

    monkeypatch.setattr(inst, "fit_sklearn", boom)
    with pytest.raises(SoilForecastingError, match="synthetic fit failure"):
        execute_train_run(config, model="ridge", horizon=1, feature_set="C", telemetry=True)
    run_dir = next((experiment_dir / "runs").iterdir())
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "failed"
    events = _events(run_dir)
    assert events[-1]["event_type"] == "run_failed"
    assert not any(item["event_type"] == "run_completed" for item in events)
