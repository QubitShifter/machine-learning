---
feature_id: ml.training_year_seasonal_forecast
name: Training-year seasonal soil-moisture reference
category: ml
status: implemented
mathematical_method: 'hat theta_{D+h} = mean of training targets in month(D+h)'
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
documentation: docs/features/ml/training_year_seasonal_forecast.md
last_verified: '2026-10-22T18:47:21Z'
related_bugs: []
---

## 1. Feature ID and name

`ml.training_year_seasonal_forecast` — Training-year seasonal soil-moisture reference.

## 2. Status and version

Status: `implemented`. Soil-forecasting pipeline 4.1.0. Research on modeled ERA5-Land swvl1 only.

## 3. Purpose

Predict the target calendar-month mean estimated from 2023 training labels only.

## 4. Scientific background

Seasonal soil-moisture cycles are strong. A monthly mean from one year is a weak climatology, labeled training_year_seasonal_reference.

## 5. Mathematical formula or algorithm

\(\mu_{train,m}\) from training absolute_target grouped by month of target_date. February 29 uses February if present, else null.

## 6. Explanation of every variable and unit

m³/m³. Fitted on training only.

## 7. Worked numerical example

Validation h=1 MAE=0.04962, skill −0.94 vs persistence. Test h=1 MAE=0.05164, skill −1.63. Worse than persistence at every horizon.

## 8. Source datasets and provenance

Training-partition targets for swvl1.

## 9. Input requirements

Eligible non-purged training targets.

## 10. Processing steps

fit_seasonal_monthly then seasonal_predict.

## 11. Implementation paths and functions

`ml.soil_forecasting.models`.

Source files:

- [`ml/soil_forecasting/`](../../../ml/soil_forecasting/)
- [`scripts/soil_forecasting_experiment.py`](../../../scripts/soil_forecasting_experiment.py)
- [`configs/soil_forecasting_experiment.yaml`](../../../configs/soil_forecasting_experiment.yaml)

## 12. Configuration parameters

models.seasonal.method=training_year_monthly_mean.

## 13. Outputs and units

models/seasonal_h{{1,3,7}}.json.

## 14. Validation criteria

Must not use 2024 or 2025 labels.

## 15. Missing-value handling

Missing month → null prediction.

## 16. Temporal leakage considerations

Using validation months to build the reference would leak.

## 17. Tests and expected assertions

[`tests/test_soil_forecasting_experiment.py`](../../../tests/test_soil_forecasting_experiment.py)

test_seasonal_uses_training_months_and_target_month.

## 18. Scientific limitations

One year is not a climatology. Seasonal baseline lost to persistence here.

## 19. Related feature dependencies

- [`ml.persistence_soil_forecast`](persistence_soil_forecast.md)

- [`docs/ml/soil_forecasting_model_baselines.md`](../../ml/soil_forecasting_model_baselines.md)
- [`ml.forecast_evaluation_contracts`](forecast_evaluation_contracts.md)

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T18:47:21Z`
