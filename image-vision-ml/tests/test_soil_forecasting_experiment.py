from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml
from sklearn.pipeline import Pipeline

from ml.agricultural_ml.metrics import mae, skill_versus_persistence
from ml.preprocessing.errors import SoilForecastingError
from ml.soil_forecasting.config import load_experiment_config, validate_experiment_config
from ml.soil_forecasting.dataset import complete_mask, eligible_mask
from ml.soil_forecasting.evaluate import aligned_metrics
from ml.soil_forecasting.models import (
    fit_seasonal_monthly,
    fit_sklearn,
    persistence_predict,
    ridge_pipeline,
    seasonal_predict,
)
from ml.soil_forecasting.pipeline import evaluate_test
from scripts.soil_forecasting_experiment import main as forecast_main


def _frame(**kwargs) -> pd.DataFrame:
    return pd.DataFrame(kwargs)


def test_persistence_uses_d_minus_1_not_issue_day():
    frame = _frame(
        swvl1_prev1=[0.21, 0.22],
        absolute_target=[0.25, 0.18],
    )
    pred = persistence_predict(frame, "swvl1_prev1")
    assert list(pred) == [0.21, 0.22]
    assert pred[0] != frame.loc[0, "absolute_target"]


def test_seasonal_uses_training_months_and_target_month():
    train = _frame(
        target_date_utc=["2023-01-15", "2023-01-20", "2023-07-01"],
        absolute_target=[0.30, 0.32, 0.18],
    )
    monthly = fit_seasonal_monthly(train)
    assert monthly[1] == pytest.approx(0.31)
    assert monthly[7] == pytest.approx(0.18)
    future = _frame(target_date_utc=["2024-01-10", "2024-02-29"])
    pred = seasonal_predict(future, monthly)
    assert pred[0] == pytest.approx(0.31)
    assert pred[1] is None  # no February in training-year monthly means


def test_ridge_scaler_fits_training_only():
    train = _frame(
        swvl1_prev1=[0.1, 0.2, 0.3, 0.4],
        precip_prev_7d_mm=[0.0, 1.0, 2.0, 3.0],
        absolute_target=[0.11, 0.21, 0.31, 0.41],
    )
    holdout = _frame(
        swvl1_prev1=[10.0, 10.0],
        precip_prev_7d_mm=[100.0, 100.0],
        absolute_target=[0.5, 0.5],
    )
    pipe = ridge_pipeline(1.0)
    fit_sklearn(pipe, train, ["swvl1_prev1", "precip_prev_7d_mm"])
    assert isinstance(pipe, Pipeline)
    mean = pipe.named_steps["scaler"].mean_
    assert mean[0] == pytest.approx(0.25)
    assert mean[1] == pytest.approx(1.5)
    # Fitting on holdout would shift the scaler; it must not have been used.
    assert mean[0] != pytest.approx(holdout["swvl1_prev1"].mean())


def test_empty_and_nonfinite_evaluation():
    empty = aligned_metrics([], [], [], [], direction_tolerance=1e-4)
    assert empty["n"] == 0
    assert empty["mae"] is None
    metrics = aligned_metrics(
        [0.2, float("nan")], [0.21, 0.3], [0.2, 0.2], [0.2, 0.2],
        direction_tolerance=1e-4,
    )
    # Non-finite observed values are dropped before scoring.
    assert metrics["n"] == 1
    wetting = aligned_metrics(
        [0.30, 0.10], [0.28, 0.12], [0.20, 0.20], [0.20, 0.20],
        direction_tolerance=1e-4,
    )
    assert wetting["direction_accuracy"] == pytest.approx(1.0)
    assert wetting["change_mae"] == pytest.approx(wetting["mae"])


def test_skill_and_zero_persistence_denominator():
    assert mae([1.0, 2.0], [1.0, 3.0]) == pytest.approx(0.5)
    assert skill_versus_persistence(0.5, 1.0) == pytest.approx(0.5)
    assert skill_versus_persistence(0.1, 0.0) is None
    metrics = aligned_metrics(
        [0.2, 0.3], [0.2, 0.3], [0.2, 0.3], [0.2, 0.3],
        direction_tolerance=1e-4,
    )
    assert metrics["n"] == 2
    assert metrics["skill_mae"] == pytest.approx(0.0)
    assert metrics["change_mae"] == pytest.approx(metrics["mae"])


def test_complete_case_does_not_treat_null_rain_as_zero():
    frame = _frame(
        precip_prev_7d_mm=[0.0, None, 1.0],
        swvl1_prev1=[0.2, 0.2, 0.2],
        target_available_flag=[True, True, True],
        excluded_flag=[False, False, False],
        absolute_target=[0.2, 0.2, 0.2],
        split=["training", "training", "training"],
        horizon_days=[1, 1, 1],
    )
    mask = complete_mask(frame, ["precip_prev_7d_mm", "swvl1_prev1"])
    assert list(mask) == [True, False, True]
    assert bool(eligible_mask(frame).all())


def test_config_rejects_satellite_and_imputation():
    payload = yaml.safe_load(Path("configs/soil_forecasting_experiment.yaml").read_text(encoding="utf-8"))
    payload["satellite_features_enabled"] = True
    with pytest.raises(SoilForecastingError):
        validate_experiment_config(payload)
    payload = yaml.safe_load(Path("configs/soil_forecasting_experiment.yaml").read_text(encoding="utf-8"))
    payload["feature_sets"]["D"]["enabled"] = True
    with pytest.raises(SoilForecastingError):
        validate_experiment_config(payload)
    payload = yaml.safe_load(Path("configs/soil_forecasting_experiment.yaml").read_text(encoding="utf-8"))
    payload["missing_data"]["impute"] = True
    with pytest.raises(SoilForecastingError):
        validate_experiment_config(payload)


def test_evaluate_test_requires_freeze(tmp_path, monkeypatch):
    config = load_experiment_config("configs/soil_forecasting_experiment.yaml")
    monkeypatch.setattr(
        "ml.soil_forecasting.pipeline.output_directory",
        lambda _config, root=None: tmp_path,
    )
    with pytest.raises(SoilForecastingError, match="frozen_experiment"):
        evaluate_test("configs/soil_forecasting_experiment.yaml")
    assert config["target"]["variable"] == "swvl1"


def test_cli_check():
    assert forecast_main(["check", "--config", "configs/soil_forecasting_experiment.yaml"]) == 0


def test_selected_predictors_are_catalogued():
    from ml.agricultural_ml.config import load_ml_config
    from ml.soil_forecasting.dataset import assert_documented_features, enabled_feature_sets

    config = load_experiment_config("configs/soil_forecasting_experiment.yaml")
    ml_config = load_ml_config("configs/agricultural_ml_dataset.yaml")
    columns = sorted({col for cols in enabled_feature_sets(config).values() for col in cols})
    assert "temp_mean_prev_7d_c" in columns
    assert "day_of_year_cos" in columns
    assert_documented_features(config, ml_config, columns)


def test_data_fingerprint_uses_features_table_not_weather(tmp_path):
    from ml.soil_forecasting.pipeline import _data_fingerprint

    features = tmp_path / "features_daily.csv"
    weather = tmp_path / "daily_weather.csv"
    features.write_text("a,b\n1,2\n", encoding="utf-8")
    weather.write_text("not-the-feature-table\n", encoding="utf-8")
    payload = _data_fingerprint(
        tmp_path,
        {"daily_weather": {"sha256": "weather-placeholder"}},
        {"_config_fingerprint": "cfg"},
    )
    assert payload["features_daily_sha256"]["sha256"] != "weather-placeholder"
    assert payload["features_daily_sha256"]["size"] == features.stat().st_size
    assert payload["ml_tables"]["features_daily.csv"]["sha256"] == payload["features_daily_sha256"]["sha256"]


def test_compare_blocked_after_test_consulted(tmp_path, monkeypatch):
    from ml.ingestion.manifest import write_json_atomic
    from ml.soil_forecasting.pipeline import compare_models

    write_json_atomic(tmp_path / "frozen_experiment.json", {
        "config_fingerprint": "any",
        "test_consulted": True,
    })
    monkeypatch.setattr(
        "ml.soil_forecasting.pipeline.output_directory",
        lambda _config, root=None: tmp_path,
    )
    with pytest.raises(SoilForecastingError, match="holdout"):
        compare_models("configs/soil_forecasting_experiment.yaml")


def test_changed_config_invalidates_freeze(tmp_path, monkeypatch):
    from ml.ingestion.manifest import write_json_atomic
    from ml.soil_forecasting import pipeline as pipe

    write_json_atomic(tmp_path / "frozen_experiment.json", {
        "config_fingerprint": "not-the-current-fingerprint",
        "test_consulted": False,
    })
    monkeypatch.setattr(pipe, "output_directory", lambda _config, root=None: tmp_path)
    with pytest.raises(SoilForecastingError, match="fingerprint"):
        evaluate_test("configs/soil_forecasting_experiment.yaml")
