---
feature_id: ml.gradient_boosting_soil_forecast
name: Gradient-boosting soil-moisture model
category: ml
status: implemented
mathematical_method: 'HistGradientBoostingRegressor with a small validation-only grid'
input_datasets:
- plovdiv_agricultural_ml_2023_2025
source_code:
- ml/soil_forecasting/pipeline.py
- ml/soil_forecasting/models.py
- ml/soil_forecasting/evaluate.py
- ml/soil_forecasting/dataset.py
- scripts/soil_forecasting_experiment.py
configuration:
- configs/soil_forecasting_experiment.yaml
outputs:
- data/processed/ml/experiments/plovdiv_soil_forecast_baselines_v1/
tests:
- tests/test_soil_forecasting_experiment.py
documentation: docs/features/ml/gradient_boosting_soil_forecast.md
last_verified: '2026-10-22T18:47:21Z'
related_bugs: []
---

## 1. Feature ID and name

`ml.gradient_boosting_soil_forecast` — Gradient-boosting soil-moisture model.

## 2. Status and version

Status: `implemented`. Soil-forecasting pipeline 4.1.0. Research on modeled ERA5-Land swvl1 only.

## 3. Purpose

Provide a modest nonlinear baseline on the same predictors as Ridge.

## 4. Scientific background

Nonlinear rainfall–moisture responses may exist, but one year of training overfits easily.

## 5. Mathematical formula or algorithm

Grid: max_depth 2–3, learning_rate 0.05–0.1, max_iter 50–100, seed 42, early_stopping false. Selected on validation MAE.

## 6. Explanation of every variable and unit

Same feature sets B/C. y in m³/m³.

## 7. Worked numerical example

Validation C: h=1 skill +0.042; h=3 +0.034; h=7 +0.063. Test C skills all ≤ 0 except none positive for C (h=1 −0.090, h=3 −0.117, h=7 −0.024). Feature set B won validation at h=3 and h=7 but was not the frozen primary (C).

## 8. Source datasets and provenance

Training complete-case rows; random_seed 42.

## 9. Input requirements

Fit training only; select on validation.

## 10. Processing steps

boosting_estimator → fit_sklearn.

## 11. Implementation paths and functions

`ml.soil_forecasting.models.boosting_estimator`.

Source files:

- [`ml/soil_forecasting/`](../../../ml/soil_forecasting/)
- [`scripts/soil_forecasting_experiment.py`](../../../scripts/soil_forecasting_experiment.py)
- [`configs/soil_forecasting_experiment.yaml`](../../../configs/soil_forecasting_experiment.yaml)

## 12. Configuration parameters

models.gradient_boosting.grid.

## 13. Outputs and units

joblib artifacts under models/gb_*.joblib.

## 14. Validation criteria

Deterministic seed; no test in grid search.

## 15. Missing-value handling

Complete-case, no imputation.

## 16. Temporal leakage considerations

Same cutoff as Ridge.

## 17. Tests and expected assertions

[`tests/test_soil_forecasting_experiment.py`](../../../tests/test_soil_forecasting_experiment.py)

Included in experiment tests via CLI check and freeze fingerprint test.

## 18. Scientific limitations

Did not beat persistence on the 2025 holdout for primary feature set C.

## 19. Related feature dependencies

- [`ml.ridge_soil_moisture_forecast`](ridge_soil_moisture_forecast.md)

- [`docs/ml/soil_forecasting_model_baselines.md`](../../ml/soil_forecasting_model_baselines.md)
- [`ml.forecast_evaluation_contracts`](forecast_evaluation_contracts.md)

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T18:47:21Z`
