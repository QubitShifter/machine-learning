import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from ml.agricultural_ml.baselines import baseline_catalog
from ml.agricultural_ml.config import load_ml_config
from ml.agricultural_ml.features import build_daily_features, empty_satellite_features
from ml.agricultural_ml.leakage import (
    fixture_future_rainfall_check,
    run_leakage_audit,
)
from ml.agricultural_ml.metrics import mae, mbe, r_squared, rmse, skill_versus_persistence, wetting_drying_direction_accuracy
from ml.agricultural_ml.readiness import assess_agricultural_ml_readiness
from ml.agricultural_ml.satellite import load_eligible_satellite_observations, satellite_features_for_issue
from ml.agricultural_ml.splits import assign_split, split_windows
from ml.agricultural_ml.targets import build_targets
from ml.agricultural_ml.time_semantics import (
    calendar_features,
    last_observation_date,
    target_date,
    target_period,
    year_length_days,
)
from ml.integration.satellite_weather import prior_window_dates
from scripts.agricultural_ml_dataset import main as ml_main


def _weather(day: date, precip: float, temp: float = 10.0) -> dict:
    return {
        "date_utc": day.isoformat(),
        "quality_status": "valid",
        "hourly_records_available": 24,
        "boundary_00utc_available": True,
        "precipitation_total_mm": precip,
        "temperature_mean_c": temp,
        "temperature_min_c": temp - 2,
        "temperature_max_c": temp + 2,
        "relative_humidity_mean_pct": 50.0,
        "wind_speed_mean_ms": 2.0,
        "evaporation_total_mm": 1.0,
    }


def _soil(day: date, theta: float) -> dict:
    return {
        "date_utc": day.isoformat(),
        "complete_day": True,
        "quality_status": "valid",
        "swvl1_mean": theta,
        "swvl2_mean": theta + 0.01,
        "swvl3_mean": theta + 0.02,
        "swvl4_mean": theta + 0.03,
        "theta_root_zone_0_100": theta + 0.015,
        "observation_kind": "modeled_volumetric_soil_moisture",
        "is_ground_truth": False,
        "is_measured_soil_moisture": False,
    }


def _config() -> dict:
    return yaml.safe_load(Path("configs/agricultural_ml_dataset.yaml").read_text(encoding="utf-8"))


def _april_series():
    start = date(2024, 3, 1)
    weather = []
    soil = []
    for offset in range(50):
        day = start + timedelta(days=offset)
        weather.append(_weather(day, float(day.day), temp=5 + day.day / 10))
        soil.append(_soil(day, 0.01 * day.day))
    return weather, soil


def test_issue_cutoff_excludes_d_and_d_plus_one():
    issue = date(2024, 4, 10)
    assert last_observation_date(issue) == date(2024, 4, 9)
    window = prior_window_dates(issue, 7)
    assert window[0] == date(2024, 4, 3)
    assert window[-1] == date(2024, 4, 9)
    assert date(2024, 4, 10) not in window
    assert date(2024, 4, 11) not in window


def test_leap_year_calendar_encoding():
    leap = calendar_features(date(2024, 3, 1))
    common = calendar_features(date(2023, 3, 1))
    assert year_length_days(2024) == 366
    assert year_length_days(2023) == 365
    assert leap["day_of_year"] == 61
    assert common["day_of_year"] == 60
    assert leap["leap_year"] is True
    assert abs(leap["day_of_year_sin"] ** 2 + leap["day_of_year_cos"] ** 2 - 1) < 1e-12


def test_year_transition_window():
    issue = date(2024, 1, 1)
    window = prior_window_dates(issue, 7)
    assert window == [
        date(2023, 12, 25), date(2023, 12, 26), date(2023, 12, 27),
        date(2023, 12, 28), date(2023, 12, 29), date(2023, 12, 30),
        date(2023, 12, 31),
    ]


def test_prev7_rainfall_is_april_3_through_9():
    weather, soil = _april_series()
    config = _config()
    rows = build_daily_features(
        issue_dates=[date(2024, 4, 10)],
        weather_rows=weather,
        soil_rows=soil,
        config=config,
    )
    row = rows[0]
    expected = 3 + 4 + 5 + 6 + 7 + 8 + 9
    assert row["precip_prev_7d_mm"] == expected
    assert row["window_7d_start_utc"] == "2024-04-03"
    assert row["window_7d_end_utc"] == "2024-04-09"
    assert row["precip_prev_1d_mm"] == 9
    assert row["swvl1_prev1"] == pytest.approx(0.09)
    assert row["swvl1_delta_prev1"] == pytest.approx(0.09 - 0.08)


def test_api_uses_end_of_day_on_d_minus_1_not_issue_date():
    weather, soil = _april_series()
    config = _config()
    rows = build_daily_features(
        issue_dates=[date(2024, 4, 10)],
        weather_rows=weather,
        soil_rows=soil,
        config=config,
    )
    assert rows[0]["api_k090_mm_source_date_utc"] == "2024-04-09"
    later = build_daily_features(
        issue_dates=[date(2024, 4, 11)],
        weather_rows=weather,
        soil_rows=soil,
        config=config,
    )
    assert later[0]["api_k090_mm"] != rows[0]["api_k090_mm"]
    assert later[0]["api_k090_mm_source_date_utc"] == "2024-04-10"


def test_targets_h1_h3_h7_and_change_baseline():
    weather, soil = _april_series()
    config = _config()
    targets = build_targets(
        issue_dates=[date(2024, 4, 10)],
        soil_rows=soil,
        config=config,
        period_end=date(2025, 12, 31),
    )
    by_key = {(row["target_variable"], row["horizon_days"]): row for row in targets}
    h1 = by_key[("swvl1", 1)]
    h7 = by_key[("swvl1", 7)]
    assert h1["target_date_utc"] == "2024-04-11"
    assert h7["target_date_utc"] == "2024-04-17"
    assert h1["absolute_target"] == pytest.approx(0.11)
    assert h1["change_baseline_date_utc"] == "2024-04-09"
    assert h1["change_target"] == pytest.approx(0.11 - 0.09)
    start, end = target_period(date(2024, 4, 10), 1)
    assert start.isoformat().replace("+00:00", "Z") == "2024-04-11T00:00:00Z"
    assert end.isoformat().replace("+00:00", "Z") == "2024-04-12T00:00:00Z"
    assert target_date(date(2024, 4, 10), 3) == date(2024, 4, 13)


def test_missing_end_of_series_targets_stay_null():
    soil = [_soil(date(2025, 12, 31), 0.2)]
    config = _config()
    targets = build_targets(
        issue_dates=[date(2025, 12, 30)],
        soil_rows=soil,
        config=config,
        period_end=date(2025, 12, 31),
    )
    h1 = next(row for row in targets if row["horizon_days"] == 1 and row["target_variable"] == "swvl1")
    h7 = next(row for row in targets if row["horizon_days"] == 7 and row["target_variable"] == "swvl1")
    assert h1["absolute_target"] == pytest.approx(0.2)
    assert h7["absolute_target"] is None
    assert h7["missing_reason"] == "future_target_outside_dataset_period"


def test_horizon_aware_split_purge():
    windows = split_windows(_config())
    keep = assign_split(date(2023, 12, 24), 7, windows)
    purge = assign_split(date(2023, 12, 25), 7, windows)
    assert keep["split"] == "training"
    assert keep["excluded"] is False
    assert purge["split"] == "excluded_purge"
    assert purge["target_date_utc"] == "2024-01-01"
    val_purge = assign_split(date(2024, 12, 25), 7, windows)
    assert val_purge["split"] == "excluded_purge"
    context_ok = assign_split(date(2024, 1, 15), 1, windows)
    assert context_ok["split"] == "validation"


def test_satellite_rejects_issue_day_and_stale():
    issue = date(2024, 4, 10)
    same_day = [{
        "scene_id": "S2_same",
        "acquisition_date": issue,
        "acquisition_timestamp": datetime(2024, 4, 10, 9, 0, tzinfo=timezone.utc),
        "ndvi_mean": 0.4,
        "quality_status": "valid",
        "calibration_status": "verified",
    }]
    payload = satellite_features_for_issue(issue, same_day, max_age_days=14)
    assert payload["ndvi_last_valid_mean"] is None
    recent = [{
        "scene_id": "S2_ok",
        "acquisition_date": date(2024, 4, 3),
        "acquisition_timestamp": datetime(2024, 4, 3, 9, 0, tzinfo=timezone.utc),
        "ndvi_mean": 0.33,
        "ndvi_median": 0.3,
        "quality_status": "valid",
        "calibration_status": "verified",
    }]
    ok = satellite_features_for_issue(issue, recent, max_age_days=14)
    assert ok["satellite_available"] is True
    assert ok["ndvi_last_valid_mean"] == 0.33
    assert ok["satellite_age_days"] == 7
    stale = satellite_features_for_issue(issue, recent, max_age_days=5)
    assert stale["satellite_stale"] is True
    assert stale["ndvi_last_valid_mean"] is None


def test_leakage_audit_detects_future_rainfall_and_zero_fill():
    weather, soil = _april_series()
    config = _config()
    rows = build_daily_features(
        issue_dates=[date(2024, 4, 10)],
        weather_rows=weather,
        soil_rows=soil,
        config=config,
    )
    leaked = dict(rows[0])
    leaked["precip_prev_7d_mm"] = float(leaked["precip_prev_7d_mm"]) + 10.0  # April 10 rainfall
    check = fixture_future_rainfall_check(leaked, date(2024, 4, 10), leaked["precip_prev_7d_mm"])
    assert check["status"] == "failed"
    zeroed = dict(rows[0])
    zeroed["window_30d_complete"] = False
    zeroed["precip_prev_30d_mm"] = 0.0
    zeroed["history_window_complete"] = False
    report = run_leakage_audit(feature_rows=[zeroed], target_rows=[], split_rows=[])
    missing = next(item for item in report["checks"] if item["check_id"] == "missing_not_replaced_with_zero")
    assert missing["status"] == "failed"


def test_metrics_contracts_and_no_skill_on_zero_persistence():
    assert mae([1, 2, 3], [1, 3, 5]) == pytest.approx(1.0)
    assert rmse([0, 0], [3, 4]) == pytest.approx(12.5 ** 0.5)
    assert mbe([1, 1], [2, 0]) == pytest.approx(0.0)
    assert r_squared([1, 1, 1], [1, 1, 1]) == 1.0
    assert r_squared([1, 1, 1], [2, 2, 2]) is None
    assert skill_versus_persistence(0.5, 1.0) == pytest.approx(0.5)
    assert skill_versus_persistence(0.1, 0.0) is None
    assert wetting_drying_direction_accuracy([0.2, -0.2], [0.1, -0.3]) == 1.0
    catalog = baseline_catalog()
    assert catalog["fitted_in_phase_4_0"] is False


def test_empty_satellite_features_are_null_not_zero():
    payload = empty_satellite_features()
    assert payload["ndvi_last_valid_mean"] is None
    assert payload["satellite_missing"] is True


def test_cli_check_and_dry_run():
    assert ml_main(["check", "--config", "configs/agricultural_ml_dataset.yaml"]) == 0
    assert ml_main(["build", "--config", "configs/agricultural_ml_dataset.yaml", "--dry-run"]) == 0


def test_config_rejects_perfect_weather_default():
    payload = _config()
    payload["issue_time"]["research_mode"] = "perfect_weather_hindcast"
    with pytest.raises(Exception):
        from ml.agricultural_ml.config import validate_ml_config
        validate_ml_config(payload)


def test_incomplete_history_is_null_not_zero():
    weather = [_weather(date(2023, 1, 1), 0.0), _weather(date(2023, 1, 2), 1.0)]
    soil = [_soil(date(2023, 1, 1), 0.2), _soil(date(2023, 1, 2), 0.21)]
    rows = build_daily_features(
        issue_dates=[date(2023, 1, 2)],
        weather_rows=weather,
        soil_rows=soil,
        config=_config(),
    )
    assert rows[0]["precip_prev_30d_mm"] is None
    assert rows[0]["window_30d_complete"] is False
    assert rows[0]["history_window_complete"] is False
    assert rows[0]["precip_prev_1d_mm"] == 0.0


def test_split_audit_flags_unpurged_training_label():
    split_rows = [{
        "issue_date_utc": "2023-12-25",
        "horizon_days": 7,
        "split": "training",
        "excluded": False,
        "target_crosses_next_split": True,
        "target_date_utc": "2024-01-01",
        "target_variable": "swvl1",
    }]
    report = run_leakage_audit(feature_rows=[], target_rows=[], split_rows=split_rows)
    check = next(item for item in report["checks"] if item["check_id"] == "split_target_crossover")
    assert check["status"] == "failed"


def test_operational_flag_is_rejected():
    row = {
        "issue_date_utc": "2024-04-10",
        "operational_availability_verified": True,
        "data_availability_mode": "research_reanalysis",
    }
    report = run_leakage_audit(feature_rows=[row], target_rows=[], split_rows=[])
    check = next(item for item in report["checks"] if item["check_id"] == "research_mode_not_operational")
    assert check["status"] == "failed"


def test_load_repo_config():
    config = load_ml_config("configs/agricultural_ml_dataset.yaml")
    assert config["dataset_id"] == "plovdiv_agricultural_ml_2023_2025"
    assert config["issue_time"]["operational_availability_verified"] is False


def test_rejected_and_review_scenes_are_not_loaded(monkeypatch, tmp_path: Path):
    quality = tmp_path / "plovdiv_2023_2025" / "quality"
    quality.mkdir(parents=True)
    (quality / "dataset_quality.json").write_text(
        json.dumps({
            "scenes": [
                {
                    "scene_id": "ok",
                    "acquisition_date": "2024-04-03",
                    "acquisition_datetime": "2024-04-03T09:00:00Z",
                    "quality_status": "valid",
                    "calibration_status": "verified",
                    "ndvi_mean": 0.4,
                },
                {
                    "scene_id": "review",
                    "acquisition_date": "2024-04-04",
                    "quality_status": "requires_review",
                    "calibration_status": "verified",
                    "ndvi_mean": 0.9,
                },
                {
                    "scene_id": "rejected",
                    "acquisition_date": "2024-04-05",
                    "quality_status": "rejected",
                    "calibration_status": "verified",
                    "ndvi_mean": 0.8,
                },
            ],
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "ml.agricultural_ml.satellite.default_processed_root",
        lambda: tmp_path,
    )
    observations = load_eligible_satellite_observations("plovdiv_2023_2025")
    assert [item["scene_id"] for item in observations] == ["ok"]


def test_readiness_keeps_suitable_for_modeling_false():
    report = assess_agricultural_ml_readiness(
        feature_rows=[{"history_window_complete": True, "satellite_available": False}],
        target_rows=[{"target_available": True}],
        split_rows=[],
        leakage={"status": "passed"},
        satellite_eligible=15,
        operational_verified=False,
        suitable_for_modeling=False,
        ground_truth=False,
    )
    assert report["suitable_for_modeling"] is False
    assert report["summary"]["operational_forecast_readiness"] == "not_ready"
    assert report["summary"]["independent_ground_truth_readiness"] == "not_ready"
    with pytest.raises(RuntimeError):
        assess_agricultural_ml_readiness(
            feature_rows=[],
            target_rows=[],
            split_rows=[],
            leakage={"status": "passed"},
            satellite_eligible=0,
            operational_verified=False,
            suitable_for_modeling=True,
            ground_truth=False,
        )
