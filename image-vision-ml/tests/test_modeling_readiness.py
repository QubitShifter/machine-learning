from ml.validation.modeling_readiness import (
    TASK_EXPLORATORY_NDVI,
    TASK_SOIL,
    TASK_VEGETATION,
    TASK_WEATHER_NDVI,
    assess_task_readiness,
    reasons_for_task,
)


def _quality(**overrides):
    payload = {
        "validated_observations": 15,
        "observations_by_year": {"2023": 5, "2024": 6, "2025": 4},
        "longest_observation_gap_days": 210,
        "spatial_grid_consistency": True,
        "ndvi_validity": True,
        "calibration_consistency": False,
        "ground_truth_soil_moisture_available": False,
        "coverage": {
            "summary": {
                "validated_observations": 15,
                "observations_by_year": {"2023": 5, "2024": 6, "2025": 4},
                "longest_observation_gap_days": 210,
                "months_with_validated_observation": 15,
                "months_in_period": 36,
            }
        },
    }
    payload.update(overrides)
    return payload


def test_exploratory_ndvi_ready_without_soil_labels():
    report = assess_task_readiness(quality=_quality())
    exploratory = report["by_task"][TASK_EXPLORATORY_NDVI]
    assert exploratory["status"] == "ready"
    soil = report["by_task"][TASK_SOIL]
    assert soil["status"] == "not_ready"
    assert "missing_ground_truth_soil_moisture" in soil["reasons"]
    assert "unresolved_calibration_consistency" in soil["reasons"]
    assert "incomplete_monthly_satellite_coverage" in soil["reasons"]


def test_vegetation_forecasting_is_limited_not_ready():
    report = assess_task_readiness(quality=_quality())
    vegetation = report["by_task"][TASK_VEGETATION]
    assert vegetation["status"] == "limited"
    assert "unresolved_calibration_consistency" in vegetation["reasons"]
    assert "longest_observation_gap_exceeds_forecast_threshold" in (
        vegetation["reasons"] + vegetation["warnings"]
    )


def test_weather_ndvi_uses_complete_pairs_not_soil_gate():
    report = assess_task_readiness(
        quality=_quality(),
        integration_metrics={
            "complete_window_count": 15,
            "observation_count": 15,
            "weather_integration_readiness": "ready",
        },
    )
    weather = report["by_task"][TASK_WEATHER_NDVI]
    assert weather["status"] == "ready"
    assert report["by_task"][TASK_SOIL]["status"] == "not_ready"


def test_exclusion_reasons_are_structured():
    report = assess_task_readiness(quality=_quality())
    reasons = reasons_for_task(report, TASK_SOIL)
    assert reasons == report["by_task"][TASK_SOIL]["reasons"]
    assert "missing_ground_truth_soil_moisture" in reasons


def test_thresholds_are_configurable():
    report = assess_task_readiness(
        quality=_quality(
            validated_observations=4,
            observations_by_year={"2023": 4},
            coverage={
                "summary": {
                    "validated_observations": 4,
                    "observations_by_year": {"2023": 4},
                    "longest_observation_gap_days": 40,
                    "months_with_validated_observation": 4,
                    "months_in_period": 12,
                }
            },
        ),
        thresholds={"exploratory_ndvi_min_observations": 10},
    )
    assert report["by_task"][TASK_EXPLORATORY_NDVI]["status"] == "not_ready"
    assert "insufficient_validated_ndvi_observations" in report["by_task"][TASK_EXPLORATORY_NDVI]["reasons"]
