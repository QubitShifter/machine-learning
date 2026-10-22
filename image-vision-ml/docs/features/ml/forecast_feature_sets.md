---
feature_id: ml.forecast_feature_sets
name: Forecast feature-set experiments A/B/C
category: ml
status: implemented
mathematical_method: 'A persistence state; B soil+calendar; C soil+weather; D satellite disabled'
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
documentation: docs/features/ml/forecast_feature_sets.md
last_verified: '2026-10-22T18:47:21Z'
related_bugs: []
---

## 1. Feature ID and name

`ml.forecast_feature_sets` — Forecast feature-set experiments A/B/C.

## 2. Status and version

Status: `implemented`. Soil-forecasting pipeline 4.1.0. Research on modeled ERA5-Land swvl1 only.

## 3. Purpose

Compare whether weather history improves on soil persistence and seasonality using matched rows.

## 4. Scientific background

The scientific question is incremental value of rainfall/API/temperature/evaporation beyond θ history. Satellite timestamps are synthesized midnight and excluded.

## 5. Mathematical formula or algorithm

Primary comparison uses complete-case feature set C so B and C share the same evaluation rows when C is complete (C is a superset).

## 6. Explanation of every variable and unit

Documented columns only. temp_mean_prev_7d_c and day_of_year_cos were added to the catalog in Phase 4.1 before use.

## 7. Worked numerical example

Validation: Ridge C slightly beat Ridge B at h=1 (0.02411 vs 0.02439 MAE). Boosting B beat C at h=3 and h=7 on validation; test still froze C as the pre-registered primary set.

## 8. Source datasets and provenance

Phase 4.0 feature table plus catalog.py.

## 9. Input requirements

Each selected column must exist in the table and catalog.

## 10. Processing steps

assert_documented_features during check.

## 11. Implementation paths and functions

`ml.soil_forecasting.dataset.enabled_feature_sets`.

Source files:

- [`ml/soil_forecasting/`](../../../ml/soil_forecasting/)
- [`scripts/soil_forecasting_experiment.py`](../../../scripts/soil_forecasting_experiment.py)
- [`configs/soil_forecasting_experiment.yaml`](../../../configs/soil_forecasting_experiment.yaml)

## 12. Configuration parameters

feature_sets in the experiment YAML; satellite_features_enabled false.

## 13. Outputs and units

feature_selection.json.

## 14. Validation criteria

Config rejects enabling D or satellite_features_enabled.

## 15. Missing-value handling

Incomplete windows drop the row; zeros are measured dry days only.

## 16. Temporal leakage considerations

No future weather. No satellite until timestamps are verified.

## 17. Tests and expected assertions

[`tests/test_soil_forecasting_experiment.py`](../../../tests/test_soil_forecasting_experiment.py)

test_config_rejects_satellite_and_imputation; test_selected_predictors_are_catalogued.

## 18. Scientific limitations

Matched-row comparison is required; do not compare A vs C sample sizes as if they were the same experiment.

## 19. Related feature dependencies

- [`ml.api_issue_time_alignment`](api_issue_time_alignment.md)
- [`ml.satellite_recency_features`](satellite_recency_features.md)

- [`docs/ml/soil_forecasting_model_baselines.md`](../../ml/soil_forecasting_model_baselines.md)
- [`ml.forecast_evaluation_contracts`](forecast_evaluation_contracts.md)

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T18:47:21Z`
