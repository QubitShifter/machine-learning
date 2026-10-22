---
feature_id: ml.final_holdout_evaluation
name: Final 2025 chronological holdout evaluation
category: ml
status: implemented
mathematical_method: 'score frozen models once on 2025; preserve the original record on repeats'
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
documentation: docs/features/ml/final_holdout_evaluation.md
last_verified: '2026-10-22T18:47:21Z'
related_bugs: []
---

## 1. Feature ID and name

`ml.final_holdout_evaluation` — Final 2025 chronological holdout evaluation.

## 2. Status and version

Status: `implemented`. Soil-forecasting pipeline 4.1.0. Research on modeled ERA5-Land swvl1 only.

## 3. Purpose

Provide a single held-out assessment after the configuration is frozen.

## 4. Scientific background

If test results motivate new models, that consultation must be recorded and a future independent holdout is required.

## 5. Mathematical formula or algorithm

evaluate-test loads frozen_experiment.json, predicts 2025, writes final_test_metrics.csv. Repeats copy originals into repeats/ and do not overwrite.

## 6. Explanation of every variable and unit

n, MAE, RMSE, MBE, R², skill vs persistence, change MAE (equal to absolute MAE).

## 7. Worked numerical example

First evaluation 2026-10-22T18:47:21Z. Repeat documented original_preserved=true. Persistence won h=1 and h=3; Ridge skill +0.029 at h=7 only.

## 8. Source datasets and provenance

Frozen artifacts plus joined_modeling_frame.csv.

## 9. Input requirements

Matching freeze fingerprint; no refit.

## 10. Processing steps

evaluate_test.

## 11. Implementation paths and functions

`ml.soil_forecasting.pipeline.evaluate_test`.

Source files:

- [`ml/soil_forecasting/`](../../../ml/soil_forecasting/)
- [`scripts/soil_forecasting_experiment.py`](../../../scripts/soil_forecasting_experiment.py)
- [`configs/soil_forecasting_experiment.yaml`](../../../configs/soil_forecasting_experiment.yaml)

## 12. Configuration parameters

splits.final_training_policy=training_partition_only.

## 13. Outputs and units

final_test_metrics.csv, final_test_predictions.csv, test_evaluation_log.json, physical_sanity_report.json.

## 14. Validation criteria

Does not retrain. Repeat preserves original.

## 15. Missing-value handling

Complete-case as in training.

## 16. Temporal leakage considerations

2025 labels unused before this command.

## 17. Tests and expected assertions

[`tests/test_soil_forecasting_experiment.py`](../../../tests/test_soil_forecasting_experiment.py)

Repeat CLI returned original_preserved true.

## 18. Scientific limitations

2025 is one year. Not robust generalization. Not operational skill.

## 19. Related feature dependencies

- [`ml.validation_only_model_selection`](validation_only_model_selection.md)

- [`docs/ml/soil_forecasting_model_baselines.md`](../../ml/soil_forecasting_model_baselines.md)
- [`ml.forecast_evaluation_contracts`](forecast_evaluation_contracts.md)

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T18:47:21Z`
