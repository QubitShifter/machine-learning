"""Research readiness for modeled ERA5-Land targets.

Does not modify observation-level suitable_for_modeling.
"""

from __future__ import annotations

from typing import Any

STATUS_READY = "ready"
STATUS_LIMITED = "limited"
STATUS_NOT_READY = "not_ready"
STATUS_REVIEW = "requires_review"


def _dimension(name: str, status: str, reasons: list[str], notes: str) -> dict[str, Any]:
    return {"name": name, "status": status, "reasons": reasons, "notes": notes}


def assess_agricultural_ml_readiness(
    *,
    feature_rows: list[dict[str, Any]],
    target_rows: list[dict[str, Any]],
    split_rows: list[dict[str, Any]],
    leakage: dict[str, Any],
    satellite_eligible: int,
    operational_verified: bool,
    suitable_for_modeling: bool,
    ground_truth: bool,
) -> dict[str, Any]:
    n_features = len(feature_rows)
    complete_history = sum(1 for row in feature_rows if row.get("history_window_complete"))
    available_targets = sum(1 for row in target_rows if row.get("target_available"))
    satellite_present = sum(1 for row in feature_rows if row.get("satellite_available"))
    leakage_ok = leakage.get("status") == "passed"
    purge_ok = not any(
        row.get("split") in {"training", "validation"} and row.get("target_crosses_next_split")
        for row in split_rows
    )

    source_integrity = _dimension(
        "source_data_integrity",
        STATUS_READY if n_features else STATUS_NOT_READY,
        [] if n_features else ["no_feature_rows"],
        "Weather and soil rows were aligned on the research issue calendar.",
    )
    history = _dimension(
        "historical_feature_completeness",
        STATUS_READY if complete_history >= 300 else (STATUS_LIMITED if complete_history else STATUS_NOT_READY),
        [] if complete_history else ["insufficient_complete_history_windows"],
        f"{complete_history} of {n_features} issue days have a complete {30}-day history.",
    )
    targets = _dimension(
        "target_completeness",
        STATUS_READY if available_targets else STATUS_NOT_READY,
        [] if available_targets else ["no_available_targets"],
        "End-of-archive horizons remain null; they are not filled.",
    )
    leakage_dim = _dimension(
        "temporal_leakage_status",
        STATUS_READY if leakage_ok else STATUS_NOT_READY,
        [] if leakage_ok else ["critical_leakage_checks_failed"],
        "Feature cutoff D−1, target D+h, and split purging were audited.",
    )
    split_dim = _dimension(
        "split_integrity",
        STATUS_READY if purge_ok else STATUS_NOT_READY,
        [] if purge_ok else ["unpurged_boundary_crossing"],
        "Chronological holdout with horizon-aware label purging.",
    )
    modeled = _dimension(
        "modeled_target_research_readiness",
        STATUS_LIMITED if leakage_ok and available_targets else STATUS_NOT_READY,
        [
            "targets_are_era5_land_reanalysis",
            "operational_publication_times_unverified",
            "three_years_are_not_robust_generalization",
        ],
        "Suitable for leakage-safe research on modeled soil-water targets, not field deployment.",
    )
    operational = _dimension(
        "operational_forecast_replay_readiness",
        STATUS_READY if operational_verified else STATUS_NOT_READY,
        [] if operational_verified else ["publication_timestamps_unknown"],
        "ERA5-Land historical cutoff is not an operational delivery time.",
    )
    field = _dimension(
        "independent_field_validation_readiness",
        STATUS_READY if ground_truth else STATUS_NOT_READY,
        [] if ground_truth else ["no_in_situ_soil_moisture_labels"],
        "No independent soil-sensor labels are present.",
    )
    satellite = _dimension(
        "satellite_enhanced_experiment_readiness",
        STATUS_LIMITED if satellite_eligible else STATUS_NOT_READY,
        ["sparse_validated_sentinel2_archive"] if satellite_eligible else ["no_eligible_satellite_scenes"],
        (
            f"{satellite_eligible} quality-gated scenes; {satellite_present} issue days carry a non-stale NDVI. "
            "Sparsity is not evidence of forecasting value."
        ),
    )

    if suitable_for_modeling:
        raise RuntimeError("Phase 4.0 must not set suitable_for_modeling true.")

    return {
        "suitable_for_modeling": False,
        "suitable_for_modeling_unchanged": True,
        "trained_model_present": False,
        "dimensions": [
            source_integrity,
            history,
            targets,
            leakage_dim,
            split_dim,
            modeled,
            operational,
            field,
            satellite,
        ],
        "summary": {
            "historical_research_readiness": modeled["status"],
            "modeled_target_research_readiness": modeled["status"],
            "independent_ground_truth_readiness": field["status"],
            "operational_forecast_readiness": operational["status"],
        },
    }
