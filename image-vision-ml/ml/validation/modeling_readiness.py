"""Task-specific modeling readiness with structured exclusion reasons.

``suitable_for_modeling`` on integrated observations remains the supervised
soil-forecasting gate and is not computed here.
"""

from __future__ import annotations

from typing import Any

from ml.ingestion.config import DEFAULT_READINESS

TASK_EXPLORATORY_NDVI = "exploratory_ndvi_analysis"
TASK_WEATHER_NDVI = "weather_ndvi_relationship_analysis"
TASK_VEGETATION = "vegetation_forecasting"
TASK_SOIL = "supervised_soil_forecasting"
TASK_SOIL_HISTORICAL = "soil_moisture_historical_analysis"
TASK_WETNESS = "rainfall_derived_wetness_analysis"
TASK_MODELED_SOIL_FORECAST = "modeled_soil_moisture_forecasting_research"
TASK_INDEPENDENT_FIELD = "independently_validated_field_soil_moisture_forecasting"
TASKS = (
    TASK_EXPLORATORY_NDVI,
    TASK_WEATHER_NDVI,
    TASK_VEGETATION,
    TASK_SOIL_HISTORICAL,
    TASK_WETNESS,
    TASK_MODELED_SOIL_FORECAST,
    TASK_INDEPENDENT_FIELD,
    TASK_SOIL,
)

STATUS_READY = "ready"
STATUS_LIMITED = "limited"
STATUS_NOT_READY = "not_ready"


def assess_task_readiness(
    *,
    quality: dict[str, Any],
    integration_metrics: dict[str, Any] | None = None,
    thresholds: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Dataset-level readiness for analysis and forecasting tasks."""
    limits = {**DEFAULT_READINESS, **(thresholds or {})}
    coverage = (quality.get("coverage") or {}).get("summary") or {}
    validated = int(coverage.get("validated_observations") or quality.get("validated_observations") or 0)
    years = (coverage.get("observations_by_year") or quality.get("observations_by_year") or {})
    year_count = len(years)
    max_gap = coverage.get("longest_observation_gap_days")
    if max_gap is None:
        max_gap = quality.get("longest_observation_gap_days")
    grid_ok = _grid_ok(quality.get("spatial_grid_consistency", True))
    ndvi_ok = bool(quality.get("ndvi_validity", True))
    calibration_ok = bool(quality.get("calibration_consistency", False))
    labels = bool(quality.get("ground_truth_soil_moisture_available", False))
    modeled_soil_days = int(quality.get("modeled_soil_complete_days") or 0)
    wetness_available = bool(quality.get("wetness_features_available", False))
    forecast_archive = bool(quality.get("forecast_archive_available", False))
    same_grid = quality.get("soil_weather_same_grid_cell")
    represented_months = int(
        coverage.get("months_with_validated_observation")
        or quality.get("months_with_validated_observation")
        or 0
    )
    months_in_period = int(coverage.get("months_in_period") or 0)
    complete_pairs = int((integration_metrics or {}).get("complete_window_count") or 0)
    weather_ready = str(
        (integration_metrics or {}).get("weather_integration_readiness") or ""
    ).lower() == "ready"
    integration_loaded = integration_metrics is not None

    assessments = [
        _exploratory_ndvi(
            validated=validated,
            grid_ok=grid_ok,
            ndvi_ok=ndvi_ok,
            min_obs=int(limits["exploratory_ndvi_min_observations"]),
        ),
        _weather_ndvi(
            validated=validated,
            ndvi_ok=ndvi_ok,
            complete_pairs=complete_pairs,
            weather_ready=weather_ready,
            integration_loaded=integration_loaded,
            min_pairs=int(limits["weather_ndvi_min_complete_pairs"]),
        ),
        _vegetation(
            validated=validated,
            year_count=year_count,
            max_gap=max_gap,
            grid_ok=grid_ok,
            ndvi_ok=ndvi_ok,
            calibration_ok=calibration_ok,
            represented_months=represented_months,
            months_in_period=months_in_period,
            limits=limits,
        ),
        _soil_historical(
            modeled_days=modeled_soil_days,
            same_grid=same_grid,
        ),
        _wetness(
            wetness_available=wetness_available,
            weather_ready=weather_ready,
        ),
        _modeled_soil_forecast(
            modeled_days=modeled_soil_days,
            forecast_archive=forecast_archive,
            labels=labels,
        ),
        _independent_field(labels=labels),
        _soil(
            labels=labels,
            validated=validated,
            year_count=year_count,
            calibration_ok=calibration_ok,
            months_in_period=months_in_period,
            represented_months=represented_months,
        ),
    ]
    return {
        "tasks": assessments,
        "by_task": {item["task"]: item for item in assessments},
        "thresholds": dict(limits),
        "threshold_justification": (
            "Operational Image Vision ML gates for this AOI and archive, "
            "not universal remote-sensing standards. Vegetation forecasting "
            "requires independent dates, multi-year seasons, and a bounded "
            "maximum gap; exploratory NDVI only requires a small valid sample "
            "on a consistent grid. Supervised soil forecasting and independent "
            "field forecasting require measured soil-moisture labels. ERA5-Land "
            "soil water does not satisfy that gate."
        ),
        "suitable_for_modeling_meaning": (
            "Observation-level suitable_for_modeling remains supervised "
            "soil-forecasting eligibility and is unchanged by this assessment."
        ),
    }


def _grid_ok(value: Any) -> bool:
    if isinstance(value, dict):
        return bool(value.get("consistent", False))
    return bool(value)


def reasons_for_task(report: dict[str, Any], task: str) -> list[str]:
    item = (report.get("by_task") or {}).get(task) or {}
    return list(item.get("reasons") or [])


def _result(
    task: str,
    status: str,
    *,
    reasons: list[str],
    warnings: list[str],
    metrics: dict[str, Any],
    explanation: str,
    next_steps: list[str],
) -> dict[str, Any]:
    return {
        "task": task,
        "status": status,
        "reasons": reasons,
        "warnings": warnings,
        "blocking_conditions": reasons if status == STATUS_NOT_READY else [],
        "metrics": metrics,
        "explanation": explanation,
        "recommended_next_steps": next_steps,
    }


def _exploratory_ndvi(
    *,
    validated: int,
    grid_ok: bool,
    ndvi_ok: bool,
    min_obs: int,
) -> dict[str, Any]:
    reasons = []
    warnings = []
    if validated < min_obs:
        reasons.append("insufficient_validated_ndvi_observations")
    if not grid_ok:
        reasons.append("inconsistent_spatial_grid")
    if not ndvi_ok:
        reasons.append("invalid_ndvi_range")
    if validated < 12:
        warnings.append("sparse_temporal_sample_limits_trend_interpretation")
    status = STATUS_READY if not reasons else STATUS_NOT_READY
    return _result(
        TASK_EXPLORATORY_NDVI,
        status,
        reasons=reasons,
        warnings=warnings,
        metrics={"validated_observations": validated, "min_observations": min_obs},
        explanation=(
            "Exploratory NDVI analysis can proceed on validated scenes with a "
            "shared AOI grid. It is not a forecasting claim."
            if status == STATUS_READY
            else "Too few valid NDVI observations, or the spatial/NDVI checks failed."
        ),
        next_steps=(
            ["inspect_monthly_coverage", "compare_ndvi_with_seasonal_context"]
            if status == STATUS_READY
            else ["ingest_additional_validated_scenes"]
        ),
    )


def _weather_ndvi(
    *,
    validated: int,
    ndvi_ok: bool,
    complete_pairs: int,
    weather_ready: bool,
    integration_loaded: bool,
    min_pairs: int,
) -> dict[str, Any]:
    reasons = []
    warnings = []
    if not integration_loaded:
        reasons.append("integration_quality_not_loaded")
    elif not weather_ready:
        reasons.append("weather_integration_not_ready")
    if complete_pairs < min_pairs:
        reasons.append("insufficient_complete_satellite_weather_pairs")
    if not ndvi_ok:
        reasons.append("invalid_ndvi_range")
    if complete_pairs and complete_pairs < 12:
        warnings.append("pair_count_supports_exploratory_correlation_not_forecasting")
    status = STATUS_READY if not reasons else (
        STATUS_LIMITED if integration_loaded and complete_pairs >= 3 and ndvi_ok else STATUS_NOT_READY
    )
    if status == STATUS_LIMITED:
        reasons = [item for item in reasons if item != "insufficient_complete_satellite_weather_pairs"]
        warnings.append("insufficient_complete_satellite_weather_pairs_for_stable_relationship")
    return _result(
        TASK_WEATHER_NDVI,
        status,
        reasons=reasons if status == STATUS_NOT_READY else [],
        warnings=warnings,
        metrics={
            "validated_observations": validated,
            "complete_integrated_pairs": complete_pairs,
            "min_complete_pairs": min_pairs,
        },
        explanation=(
            "Leakage-safe weather windows can be compared with validated NDVI "
            "on complete observation dates."
            if status != STATUS_NOT_READY
            else "Weather–NDVI pairing is incomplete or weather integration is not ready."
        ),
        next_steps=(
            ["use_complete_integrated_observations_only", "do_not_treat_null_weather_as_zero"]
            if status != STATUS_NOT_READY
            else ["run_weather_dataset_integrate_after_satellite_validation"]
        ),
    )


def _vegetation(
    *,
    validated: int,
    year_count: int,
    max_gap: Any,
    grid_ok: bool,
    ndvi_ok: bool,
    calibration_ok: bool,
    represented_months: int,
    months_in_period: int,
    limits: dict[str, Any],
) -> dict[str, Any]:
    reasons = []
    warnings = []
    min_obs = int(limits["vegetation_forecast_min_observations"])
    min_years = int(limits["vegetation_forecast_min_years"])
    max_gap_limit = int(limits["vegetation_forecast_max_gap_days"])
    limited_obs = int(limits["vegetation_limited_min_observations"])
    limited_years = int(limits["vegetation_limited_min_years"])
    gap = None if max_gap is None else int(max_gap)
    if not grid_ok:
        reasons.append("inconsistent_spatial_grid")
    if not ndvi_ok:
        reasons.append("invalid_ndvi_range")
    if not calibration_ok:
        reasons.append("unresolved_calibration_consistency")
    if validated < limited_obs or year_count < limited_years:
        reasons.append("insufficient_temporal_satellite_coverage")
    if gap is not None and gap > max_gap_limit:
        warnings.append("longest_observation_gap_exceeds_forecast_threshold")
    if months_in_period and represented_months < months_in_period:
        warnings.append("missing_months_in_study_period")

    forecast_ok = (
        not reasons
        and validated >= min_obs
        and year_count >= min_years
        and (gap is None or gap <= max_gap_limit)
        and calibration_ok
    )
    limited_ok = (
        validated >= limited_obs
        and year_count >= limited_years
        and grid_ok
        and ndvi_ok
    )
    if forecast_ok:
        status = STATUS_READY
        remaining_reasons: list[str] = []
    elif limited_ok:
        status = STATUS_LIMITED
        remaining_reasons = [
            item for item in reasons if item != "insufficient_temporal_satellite_coverage"
        ]
        if validated < min_obs or year_count < min_years:
            remaining_reasons.append("below_validated_forecasting_density")
        if gap is not None and gap > max_gap_limit:
            remaining_reasons.append("longest_observation_gap_exceeds_forecast_threshold")
        reasons = remaining_reasons
    else:
        status = STATUS_NOT_READY

    return _result(
        TASK_VEGETATION,
        status,
        reasons=reasons if status != STATUS_READY else [],
        warnings=warnings,
        metrics={
            "validated_observations": validated,
            "represented_years": year_count,
            "longest_observation_gap_days": gap,
            "months_with_validated_observation": represented_months,
            "forecast_min_observations": min_obs,
            "forecast_min_years": min_years,
            "forecast_max_gap_days": max_gap_limit,
        },
        explanation=(
            "Vegetation forecasting is exploratory-limited: independent dates exist "
            "across years, but coverage, gaps, or calibration prevent a reliable "
            "validated forecasting dataset."
            if status == STATUS_LIMITED
            else "Coverage, calibration, and NDVI checks meet the project forecast gates."
            if status == STATUS_READY
            else "Validated NDVI time series is too sparse or scientifically inconsistent for forecasting."
        ),
        next_steps=[
            "preview_candidate_scenes_for_missing_months",
            "resolve_calibration_review_before_training",
            "do_not_train_until_time_aware_evaluation_is_defined",
        ],
    )


def _soil_historical(
    *,
    modeled_days: int,
    same_grid: Any,
) -> dict[str, Any]:
    reasons = []
    warnings = []
    if modeled_days < 1:
        reasons.append("modeled_soil_water_not_processed")
    if same_grid is False:
        warnings.append("soil_and_weather_grid_cells_differ")
    status = STATUS_READY if not reasons else STATUS_NOT_READY
    return _result(
        TASK_SOIL_HISTORICAL,
        status,
        reasons=reasons,
        warnings=warnings,
        metrics={"modeled_soil_complete_days": modeled_days, "same_grid_cell": same_grid},
        explanation=(
            "Historical analysis of modeled ERA5-Land volumetric soil water "
            "can proceed. This is not independent field validation."
            if status == STATUS_READY
            else "No complete modeled soil-water days are available yet."
        ),
        next_steps=(
            ["inspect_layer_and_root_zone_series", "do_not_treat_as_ground_truth"]
            if status == STATUS_READY
            else ["run_soil_dataset_process_on_downloaded_or_fixture_months"]
        ),
    )


def _wetness(
    *,
    wetness_available: bool,
    weather_ready: bool,
) -> dict[str, Any]:
    reasons = []
    if not wetness_available and not weather_ready:
        reasons.append("wetness_features_not_generated")
    status = STATUS_READY if wetness_available or weather_ready else STATUS_NOT_READY
    if weather_ready and not wetness_available:
        status = STATUS_LIMITED
    return _result(
        TASK_WETNESS,
        status,
        reasons=reasons if status == STATUS_NOT_READY else [],
        warnings=[] if wetness_available else ["wetness_csv_not_written_use_weather_archive"],
        metrics={
            "wetness_features_available": wetness_available,
            "weather_integration_ready": weather_ready,
        },
        explanation=(
            "Rainfall-history and weather-derived wetness proxies can be analysed. "
            "They are not measured soil moisture."
            if status != STATUS_NOT_READY
            else "Weather archive or wetness indicators are not available."
        ),
        next_steps=["generate_wetness_indicators", "keep_null_precipitation_as_null"],
    )


def _modeled_soil_forecast(
    *,
    modeled_days: int,
    forecast_archive: bool,
    labels: bool,
) -> dict[str, Any]:
    reasons = []
    warnings = ["do_not_present_as_operational_skill_without_forecast_archive"]
    if modeled_days < 30:
        reasons.append("insufficient_modeled_soil_target_days")
    if not forecast_archive:
        reasons.append("archived_operational_forecasts_not_ingested")
    if labels:
        warnings.append("measured_labels_present_but_this_task_uses_modeled_targets")
    status = STATUS_LIMITED if modeled_days >= 30 else STATUS_NOT_READY
    if status == STATUS_LIMITED:
        reasons = [item for item in reasons if item != "insufficient_modeled_soil_target_days"]
    return _result(
        TASK_MODELED_SOIL_FORECAST,
        status,
        reasons=reasons if status == STATUS_NOT_READY else reasons,
        warnings=warnings,
        metrics={
            "modeled_soil_complete_days": modeled_days,
            "forecast_archive_available": forecast_archive,
        },
        explanation=(
            "Research on modeled soil-water targets may use historical weather, "
            "but ECMWF Open Data is not a 2023-2025 forecast archive. "
            "Perfect-weather experiments are not operational skill."
            if status != STATUS_NOT_READY
            else "Modeled soil-water targets or forecast contracts are insufficient for research experiments."
        ),
        next_steps=[
            "keep_operational_and_perfect_weather_modes_separate",
            "do_not_train_until_time_aware_evaluation_is_defined",
        ],
    )


def _independent_field(*, labels: bool) -> dict[str, Any]:
    reasons = []
    if not labels:
        reasons.append("missing_ground_truth_soil_moisture")
    return _result(
        TASK_INDEPENDENT_FIELD,
        STATUS_NOT_READY if reasons else STATUS_READY,
        reasons=reasons,
        warnings=[],
        metrics={"ground_truth_soil_moisture_available": labels},
        explanation=(
            "Independently validated field soil-moisture forecasting requires "
            "in-situ or otherwise measured labels. ERA5-Land soil water does not qualify."
        ),
        next_steps=["collect_independent_soil_moisture_labels_if_this_task_is_required"],
    )


def _soil(
    *,
    labels: bool,
    validated: int,
    year_count: int,
    calibration_ok: bool,
    months_in_period: int,
    represented_months: int,
) -> dict[str, Any]:
    reasons = []
    if not labels:
        reasons.append("missing_ground_truth_soil_moisture")
    if validated < 12 or year_count < 3:
        reasons.append("insufficient_temporal_satellite_coverage")
    if not calibration_ok:
        reasons.append("unresolved_calibration_consistency")
    if months_in_period and represented_months < months_in_period:
        reasons.append("incomplete_monthly_satellite_coverage")
    return _result(
        TASK_SOIL,
        STATUS_NOT_READY if reasons else STATUS_READY,
        reasons=reasons,
        warnings=[],
        metrics={
            "ground_truth_soil_moisture_available": labels,
            "validated_observations": validated,
            "represented_years": year_count,
        },
        explanation=(
            "Supervised soil forecasting is not ready. NDVI is not a substitute "
            "for measured soil moisture. Observation-level suitable_for_modeling "
            "uses this same gate."
        ),
        next_steps=[
            "do_not_infer_soil_moisture_from_ndvi",
            "collect_independent_soil_moisture_labels_if_this_task_is_required",
        ],
    )
