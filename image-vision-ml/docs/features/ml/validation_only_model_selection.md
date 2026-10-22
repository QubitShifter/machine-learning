---
feature_id: ml.validation_only_model_selection
name: Validation-only hyperparameter selection
category: ml
status: implemented
mathematical_method: 'minimize 2024 MAE; never use 2025 during development'
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
documentation: docs/features/ml/validation_only_model_selection.md
last_verified: '2026-10-22T18:47:21Z'
related_bugs: []
---

## 1. Feature ID and name

`ml.validation_only_model_selection` — Validation-only hyperparameter selection.

## 2. Status and version

Status: `implemented`. Soil-forecasting pipeline 4.1.0. Research on modeled ERA5-Land swvl1 only.

## 3. Purpose

Choose Ridge alpha and boosting hyperparameters without consulting the test year.

## 4. Scientific background

Repeated test peeks destroy the holdout. Selection criterion is declared in YAML before test evaluation.

## 5. Mathematical formula or algorithm

For each family and horizon, keep the primary feature-set C candidate with lowest validation MAE. Freeze into frozen_experiment.json with config fingerprint.

## 6. Explanation of every variable and unit

criterion validation_mae; primary_feature_set C; fitted_on training_partition_only.

## 7. Worked numerical example

Frozen at 2026-10-22T18:38:09Z. Ridge α=1 (h=1) and α=100 (h=3,7). Boosting grids as recorded in frozen_experiment.json.

## 8. Source datasets and provenance

validation_metrics.csv.

## 9. Input requirements

train must have written candidates; test files must not be read.

## 10. Processing steps

compare_models writes freeze; evaluate-test refuses without it.

## 11. Implementation paths and functions

`ml.soil_forecasting.pipeline.compare_models`.

Source files:

- [`ml/soil_forecasting/`](../../../ml/soil_forecasting/)
- [`scripts/soil_forecasting_experiment.py`](../../../scripts/soil_forecasting_experiment.py)
- [`configs/soil_forecasting_experiment.yaml`](../../../configs/soil_forecasting_experiment.yaml)

## 12. Configuration parameters

selection.criterion; selection.primary_feature_set.

## 13. Outputs and units

frozen_experiment.json; model_comparison.csv.

## 14. Validation criteria

Fingerprint mismatch aborts test evaluation.

## 15. Missing-value handling

Not applicable.

## 16. Temporal leakage considerations

Test partition is not used to pick alpha.

## 17. Tests and expected assertions

[`tests/test_soil_forecasting_experiment.py`](../../../tests/test_soil_forecasting_experiment.py)

test_changed_config_invalidates_freeze; test_evaluate_test_requires_freeze.

## 18. Scientific limitations

One validation year can prefer models that fail on the next year, as observed at h=1 and h=3 on 2025.

## 19. Related feature dependencies

- [`ml.final_holdout_evaluation`](final_holdout_evaluation.md)

- [`docs/ml/soil_forecasting_model_baselines.md`](../../ml/soil_forecasting_model_baselines.md)
- [`ml.forecast_evaluation_contracts`](forecast_evaluation_contracts.md)

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T18:47:21Z`
