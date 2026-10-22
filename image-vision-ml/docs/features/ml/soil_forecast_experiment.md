---
feature_id: ml.soil_forecast_experiment
name: Soil-moisture forecasting experiment runner
category: ml
status: implemented
mathematical_method: 'chronological train 2023 / validate 2024 / freeze / test 2025 on swvl1 h=1,3,7'
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
documentation: docs/features/ml/soil_forecast_experiment.md
last_verified: '2026-10-22T18:47:21Z'
related_bugs:
- BUG-0012
---

## 1. Feature ID and name

`ml.soil_forecast_experiment` — Soil-moisture forecasting experiment runner.

## 2. Status and version

Status: `implemented`. Soil-forecasting pipeline 4.1.0. Research on modeled ERA5-Land swvl1 only.

## 3. Purpose

Run a reproducible research experiment that trains and evaluates soil-moisture forecasts without operational deployment.

## 4. Scientific background

Phase 4.0 produced a leakage-safe table. Phase 4.1 asks whether learned models beat persistence on held-out years for modeled 0–7 cm moisture.

## 5. Mathematical formula or algorithm

CLI: check → prepare → train → validate → compare (freeze) → evaluate-test. evaluate-test does not refit. GET APIs are read-only.

## 6. Explanation of every variable and unit

experiment_id plovdiv_soil_forecast_baselines_v1; target swvl1 m³/m³; research_reanalysis; suitable_for_modeling remains false.

## 7. Worked numerical example

Training h=1 feature set C: 350 complete-case rows. Validation 365. Test 364. Leakage audit still passed before training.

## 8. Source datasets and provenance

Phase 4.0 features_daily.csv, targets.csv, split_membership.csv. Satellite timestamps excluded.

## 9. Input requirements

Phase 4.0 validate and leakage passed. sklearn available. Complete-case selected predictors documented in the catalog.

## 10. Processing steps

scripts.soil_forecasting_experiment. No CDS. No /predict endpoint.

## 11. Implementation paths and functions

`ml.soil_forecasting.pipeline`.

Source files:

- [`ml/soil_forecasting/`](../../../ml/soil_forecasting/)
- [`scripts/soil_forecasting_experiment.py`](../../../scripts/soil_forecasting_experiment.py)
- [`configs/soil_forecasting_experiment.yaml`](../../../configs/soil_forecasting_experiment.yaml)

## 12. Configuration parameters

configs/soil_forecasting_experiment.yaml.

## 13. Outputs and units

experiment directory under data/processed/ml/experiments/ including frozen_experiment.json and metrics CSVs.

## 14. Validation criteria

check aborts if leakage failed or satellite enabled or suitable_for_modeling true.

## 15. Missing-value handling

Complete-case; missing windows dropped, never filled with 0.

## 16. Temporal leakage considerations

Issue cutoff D−1 from Phase 4.0. Test labels unused until freeze.

## 17. Tests and expected assertions

[`tests/test_soil_forecasting_experiment.py`](../../../tests/test_soil_forecasting_experiment.py)

CLI check; fingerprint mismatch test; evaluate-test requires freeze.

## 18. Scientific limitations

One training year; serial dependence; shared ERA5 ancestry; not field-validated.

## 19. Related feature dependencies

- [`ml.agricultural_research_dataset`](agricultural_research_dataset.md)
- [`ml.horizon_aware_chronological_splits`](horizon_aware_chronological_splits.md)

- [`docs/ml/soil_forecasting_model_baselines.md`](../../ml/soil_forecasting_model_baselines.md)
- [`ml.forecast_evaluation_contracts`](forecast_evaluation_contracts.md)

## 20. Related bug/fix IDs

[`BUG-0012`](../../bugs/BUG-0012.md) — experiment fingerprint initially copied the weather checksum.

## 21. Last reviewed timestamp in UTC

`2026-10-22T18:47:21Z`
