---
feature_id: ml.persistence_soil_forecast
name: Persistence soil-moisture baseline
category: ml
status: implemented
mathematical_method: 'hat theta_{D+h} = theta_{D-1}'
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
documentation: docs/features/ml/persistence_soil_forecast.md
last_verified: '2026-10-22T18:47:21Z'
related_bugs: []
---

## 1. Feature ID and name

`ml.persistence_soil_forecast` — Persistence soil-moisture baseline.

## 2. Status and version

Status: `implemented`. Soil-forecasting pipeline 4.1.0. Research on modeled ERA5-Land swvl1 only.

## 3. Purpose

Provide the essential benchmark that later models must beat on matched rows.

## 4. Scientific background

Near-surface soil moisture is strongly autocorrelated. A useful ML model must outperform last observed state.

## 5. Mathematical formula or algorithm

\(\hat\theta_{D+h}=\theta_{D-1}\) using feature swvl1_prev1. Derived change is 0.

## 6. Explanation of every variable and unit

Unit m³/m³. No training.

## 7. Worked numerical example

Validation 2024 h=1 MAE=0.02554 m³/m³ (n=365). Test 2025 h=1 MAE=0.01965 (n=364). MAE increases with horizon.

## 8. Source datasets and provenance

swvl1_prev1 from features_daily.csv.

## 9. Input requirements

Non-null D−1 moisture and available target.

## 10. Processing steps

persistence_predict.

## 11. Implementation paths and functions

`ml.soil_forecasting.models.persistence_predict`.

Source files:

- [`ml/soil_forecasting/`](../../../ml/soil_forecasting/)
- [`scripts/soil_forecasting_experiment.py`](../../../scripts/soil_forecasting_experiment.py)
- [`configs/soil_forecasting_experiment.yaml`](../../../configs/soil_forecasting_experiment.yaml)

## 12. Configuration parameters

target.persistence_feature: swvl1_prev1.

## 13. Outputs and units

prediction columns in validation/test prediction CSVs.

## 14. Validation criteria

Must use D−1, never θ_D or the target.

## 15. Missing-value handling

Rows with missing swvl1_prev1 are excluded from matched evaluation.

## 16. Temporal leakage considerations

Same-day moisture as a forecast is leakage.

## 17. Tests and expected assertions

[`tests/test_soil_forecasting_experiment.py`](../../../tests/test_soil_forecasting_experiment.py)

test_persistence_uses_d_minus_1_not_issue_day.

## 18. Scientific limitations

Persistence is hard to beat at h=1. Direction accuracy is near zero because derived change is identically 0.

## 19. Related feature dependencies

- [`ml.soil_moisture_target_construction`](soil_moisture_target_construction.md)

- [`docs/ml/soil_forecasting_model_baselines.md`](../../ml/soil_forecasting_model_baselines.md)
- [`ml.forecast_evaluation_contracts`](forecast_evaluation_contracts.md)

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T18:47:21Z`
