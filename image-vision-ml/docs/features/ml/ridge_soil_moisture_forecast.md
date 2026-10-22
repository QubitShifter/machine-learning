---
feature_id: ml.ridge_soil_moisture_forecast
name: Ridge regression soil-moisture model
category: ml
status: implemented
mathematical_method: 'StandardScaler then Ridge; alpha selected on validation MAE'
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
documentation: docs/features/ml/ridge_soil_moisture_forecast.md
last_verified: '2026-10-22T18:47:21Z'
related_bugs: []
---

## 1. Feature ID and name

`ml.ridge_soil_moisture_forecast` — Ridge regression soil-moisture model.

## 2. Status and version

Status: `implemented`. Soil-forecasting pipeline 4.1.0. Research on modeled ERA5-Land swvl1 only.

## 3. Purpose

Fit a regularized linear model on documented historical soil and weather features.

## 4. Scientific background

Linear memory of θ_{D-1} plus rainfall/API/temperature/evaporation may improve short-range forecasts if those associations exist in ERA5-Land.

## 5. Mathematical formula or algorithm

\(\hat y=\beta_0+\sum \beta_j x_j\) with L2 penalty. Alphas {0.01,0.1,1,10,100}. Feature sets B and C. Selected C: h=1 α=1; h=3 and h=7 α=100.

## 6. Explanation of every variable and unit

Predictors documented in the catalog; unit of y is m³/m³.

## 7. Worked numerical example

Validation skill vs persistence: h=1 +0.056 (n=365); h=3 +0.055 (n=363); h=7 +0.101 (n=359). Test: h=1 −0.030; h=3 −0.038; h=7 +0.029. No clipping.

## 8. Source datasets and provenance

Training complete-case rows only.

## 9. Input requirements

Scaler and Ridge fitted on training; validation used only to pick alpha.

## 10. Processing steps

ridge_pipeline → fit_sklearn.

## 11. Implementation paths and functions

`ml.soil_forecasting.models.ridge_pipeline`.

Source files:

- [`ml/soil_forecasting/`](../../../ml/soil_forecasting/)
- [`scripts/soil_forecasting_experiment.py`](../../../scripts/soil_forecasting_experiment.py)
- [`configs/soil_forecasting_experiment.yaml`](../../../configs/soil_forecasting_experiment.yaml)

## 12. Configuration parameters

models.ridge.alphas; feature_sets [B, C].

## 13. Outputs and units

joblib artifacts models/ridge_h*_C_alpha*.joblib.

## 14. Validation criteria

Scaler mean must equal training mean, not validation/test.

## 15. Missing-value handling

Complete-case; no zero-fill of missing rain.

## 16. Temporal leakage considerations

Test labels never enter fitting or alpha search.

## 17. Tests and expected assertions

[`tests/test_soil_forecasting_experiment.py`](../../../tests/test_soil_forecasting_experiment.py)

test_ridge_scaler_fits_training_only.

## 18. Scientific limitations

Validation skill did not hold at h=1 and h=3 on 2025. Shared ERA5 ancestry can inflate validation associations.

## 19. Related feature dependencies

- [`ml.forecast_feature_sets`](forecast_feature_sets.md)

- [`docs/ml/soil_forecasting_model_baselines.md`](../../ml/soil_forecasting_model_baselines.md)
- [`ml.forecast_evaluation_contracts`](forecast_evaluation_contracts.md)

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T18:47:21Z`
