---
feature_id: ml.forecast_evaluation_contracts
name: Forecast baseline and evaluation contracts
category: ml
status: implemented
mathematical_method: 'persistence θ̂_{D+h}=θ_{D-1}; MAE/RMSE/MBE/R²/skill; no fitting'
input_datasets:
- plovdiv_weather_2023_2025
- plovdiv_soil_2023_2025
- plovdiv_2023_2025
source_code:
- ml/agricultural_ml/pipeline.py
- ml/agricultural_ml/features.py
- ml/agricultural_ml/targets.py
- ml/agricultural_ml/time_semantics.py
- ml/agricultural_ml/splits.py
- ml/agricultural_ml/leakage.py
- ml/agricultural_ml/satellite.py
- ml/agricultural_ml/readiness.py
- ml/agricultural_ml/metrics.py
- ml/agricultural_ml/baselines.py
- scripts/agricultural_ml_dataset.py
configuration:
- configs/agricultural_ml_dataset.yaml
outputs:
- data/processed/ml/plovdiv_agricultural_ml_2023_2025/
tests:
- tests/test_agricultural_ml_dataset.py
documentation: docs/features/ml/forecast_evaluation_contracts.md
last_verified: '2026-10-22T17:14:17Z'
related_bugs: []
---

## 1. Feature ID and name

`ml.forecast_evaluation_contracts` — Forecast baseline and evaluation contracts.

## 2. Status and version

Status: `implemented`. Agricultural ML pipeline version 4.0.0. No trained forecasting model.

## 3. Purpose

Specify baselines and metrics before any model is trained, and test the metric functions on fixtures only.

## 4. Scientific background

A later ML model should beat persistence on held-out years. Seasonal climatology must be estimated from training labels only. Skill versus persistence is undefined when persistence MAE is 0 and the model is not perfect.

## 5. Mathematical formula or algorithm

Persistence: \(\hat\theta_{D+h}=\theta_{D-1}\). Seasonal: training-period day-of-year mean, never using 2025 labels for 2025. Rainfall-memory: \(f(\theta_{D-1},P_{\mathrm{prev7}},\mathrm{API}_{D-1},E_{\mathrm{prev7}},T_{\mathrm{prev7}})\) coefficients not fitted. Skill \(=1-\mathrm{MAE}_{model}/\mathrm{MAE}_{persistence}\). Wetting/drying direction uses tolerance around 0.

## 6. Explanation of every variable and unit

MAE, RMSE, MBE in m³/m³ (or mm for weather-only diagnostics). Skill dimensionless. Direction accuracy in [0,1].

## 7. Worked numerical example

mae([1,2,3],[1,3,5])=1. r² of a constant series with identical predictions is 1; with different predictions is null. skill(0.5,1.0)=0.5; skill(0.1,0.0) is null. baseline_catalog.fitted_in_phase_4_0 is false. No agricultural skill numbers were written to the dataset.

## 8. Source datasets and provenance

None. Contracts only. persistence_prediction is copied from the D−1 baseline on targets.csv for later scoring.

## 9. Input requirements

Paired observed/predicted sequences of equal length; nulls skipped.

## 10. Processing steps

`mae`, `rmse`, `mbe`, `r_squared`, `skill_versus_persistence`, `wetting_drying_direction_accuracy`. `baseline_catalog()`.

## 11. Implementation paths and functions

`ml.agricultural_ml.metrics`, `ml.agricultural_ml.baselines`.

Source files:

- [`ml/agricultural_ml/`](../../../ml/agricultural_ml/)
- [`scripts/agricultural_ml_dataset.py`](../../../scripts/agricultural_ml_dataset.py)
- [`configs/agricultural_ml_dataset.yaml`](../../../configs/agricultural_ml_dataset.yaml)

## 12. Configuration parameters

None beyond documenting future stratified evaluation (season, horizon, depth, wet/dry, rainfall events). Tiny subgroups must not be over-interpreted.

## 13. Outputs and units

baseline_contracts.json. Metric functions are not applied to the Plovdiv targets in Phase 4.0.

## 14. Validation criteria

Fixture assertions only. Constant-target and zero-persistence-error cases handled.

## 15. Missing-value handling

Null pairs skipped. Empty series return None.

## 16. Temporal leakage considerations

Scoring the full 2023–2025 table before splits, or using test labels in a seasonal baseline, would leak.

## 17. Tests and expected assertions

[`tests/test_agricultural_ml_dataset.py`](../../../tests/test_agricultural_ml_dataset.py)

test_metrics_contracts_and_no_skill_on_zero_persistence.

## 18. Scientific limitations

Future families (ridge, forest, boosting, AR, residual physical models) are names only. No extra ML libraries were installed for training.

## 19. Related feature dependencies

- [`forecasting.agricultural_forecasting`](../forecasting/agricultural_forecasting.md)
- [`forecasting.issue_valid_time_contracts`](../forecasting/issue_valid_time_contracts.md)

- [`docs/ml/agricultural_forecasting_mathematics.md`](../../ml/agricultural_forecasting_mathematics.md)
- [`docs/ml/scientific_decision_log.md`](../../ml/scientific_decision_log.md)

## 20. Related bug/fix IDs

None created for Phase 4.0. Leakage risks were prevented by construction rather than discovered as production defects.

## 21. Last reviewed timestamp in UTC

`2026-10-22T17:14:17Z`
