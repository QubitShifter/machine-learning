"""Forecast baseline contracts. No coefficients are fitted in Phase 4.0."""

from __future__ import annotations

from typing import Any


PERSISTENCE = {
    "baseline_id": "persistence_last_complete_day",
    "formula": "hat_theta_{D+h} = theta_{D-1}",
    "inputs": ["theta at last_observation_date_utc"],
    "training_required": False,
    "notes": "Same value for every horizon. Uses the latest completed historical day, not θ_D.",
}

SEASONAL = {
    "baseline_id": "training_period_day_of_year_mean",
    "formula": "hat_theta_{D+h} = mean(theta on the same day-of-year in the training partition only)",
    "inputs": ["training-split absolute targets"],
    "training_required": True,
    "notes": (
        "Must not use validation or test labels. Leap-year 29 February uses the "
        "training 29 February mean when present, otherwise remains null. An "
        "all-years climatology that includes 2025 is forbidden for 2025 evaluation."
    ),
}

RAINFALL_MEMORY = {
    "baseline_id": "rainfall_memory_linear",
    "formula": "hat_theta_{D+h} = f(theta_{D-1}, P_prev7, API_{D-1}, E_prev7, T_prev7)",
    "inputs": [
        "swvl*_prev1 or theta_root_zone_0_100_prev1",
        "precip_prev_7d_mm",
        "api_k090_mm",
        "evap_prev_7d_mm",
        "temp_mean_prev_7d_c",
    ],
    "training_required": True,
    "notes": (
        "Coefficients may be estimated in a later phase on the training partition "
        "only. This contract does not fit them."
    ),
}

FUTURE_MODEL_FAMILIES = (
    "ridge_regression",
    "random_forest",
    "gradient_boosting",
    "time_series_autoregression",
    "physically_informed_residual",
)


def baseline_catalog() -> dict[str, Any]:
    return {
        "fitted_in_phase_4_0": False,
        "persistence": PERSISTENCE,
        "seasonal": SEASONAL,
        "rainfall_memory": RAINFALL_MEMORY,
        "future_model_families": list(FUTURE_MODEL_FAMILIES),
        "evaluation_note": (
            "Persistence predictions are stored as change-baseline values for later "
            "scoring. Phase 4.0 does not report agricultural skill."
        ),
    }
