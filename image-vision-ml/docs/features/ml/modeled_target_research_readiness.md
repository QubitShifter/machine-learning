---
feature_id: ml.modeled_target_research_readiness
name: Modeled-target research readiness
category: ml
status: implemented
mathematical_method: 'task-specific statuses separate from suitable_for_modeling'
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
documentation: docs/features/ml/modeled_target_research_readiness.md
last_verified: '2026-10-22T17:14:17Z'
related_bugs: []
---

## 1. Feature ID and name

`ml.modeled_target_research_readiness` — Modeled-target research readiness.

## 2. Status and version

Status: `implemented`. Agricultural ML pipeline version 4.0.0. No trained forecasting model.

## 3. Purpose

Report whether the research table is usable for ERA5-Land target experiments without claiming field or operational readiness.

## 4. Scientific background

Complete modeled soil data can coexist with absent sensors and unverified publication times. Collapsing those into one boolean would be scientifically false.

## 5. Mathematical formula or algorithm

Dimensions: source_data_integrity, historical_feature_completeness, target_completeness, temporal_leakage_status, split_integrity, modeled_target_research_readiness, operational_forecast_replay_readiness, independent_field_validation_readiness, satellite_enhanced_experiment_readiness. Statuses: ready, limited, not_ready, requires_review.

## 6. Explanation of every variable and unit

suitable_for_modeling remains false. trained_model_present=false. Raising suitable_for_modeling true in this assessor is a hard error.

## 7. Worked numerical example

Generated dataset: historical/modeled research readiness=limited (reanalysis targets, unverified publication, three years). Operational=not_ready. Ground truth=not_ready. Satellite experiment=limited (15 scenes). Leakage=passed. 1066/1096 issue days have complete 30-day history.

## 8. Source datasets and provenance

Feature/target/split tables plus source soil quality flags (read, not rewritten).

## 9. Input requirements

Does not modify soil or satellite quality_report.json.

## 10. Processing steps

`assess_agricultural_ml_readiness`. Refuses if suitable_for_modeling is true.

## 11. Implementation paths and functions

`ml.agricultural_ml.readiness`. API `GET /api/v1/ml/research-dataset`. Data Quality card.

Source files:

- [`ml/agricultural_ml/`](../../../ml/agricultural_ml/)
- [`scripts/agricultural_ml_dataset.py`](../../../scripts/agricultural_ml_dataset.py)
- [`configs/agricultural_ml_dataset.yaml`](../../../configs/agricultural_ml_dataset.yaml)

## 12. Configuration parameters

Readiness thresholds in code (complete_history ≥ 300 → ready/limited).

## 13. Outputs and units

modeling_readiness.json, dataset_quality.json (suitable_for_modeling false), UI summary labeled “Research dataset — no trained model yet.”

## 14. Validation criteria

test_readiness_keeps_suitable_for_modeling_false; backend test_ml_api.py.

## 15. Missing-value handling

Not applicable; statuses are explicit.

## 16. Temporal leakage considerations

Readiness is not skill and not a license to train operational models.

## 17. Tests and expected assertions

[`tests/test_agricultural_ml_dataset.py`](../../../tests/test_agricultural_ml_dataset.py)

test_readiness_keeps_suitable_for_modeling_false; API tests.

## 18. Scientific limitations

Limited research readiness is not deployment. Sparse satellite is not incremental skill.

## 19. Related feature dependencies

- [`integration.modeling_eligibility`](../integration/modeling_eligibility.md)
- [`soil.era5_land_volumetric_moisture`](../soil/era5_land_volumetric_moisture.md)

- [`docs/ml/agricultural_forecasting_mathematics.md`](../../ml/agricultural_forecasting_mathematics.md)
- [`docs/ml/scientific_decision_log.md`](../../ml/scientific_decision_log.md)

## 20. Related bug/fix IDs

None created for Phase 4.0. Leakage risks were prevented by construction rather than discovered as production defects.

## 21. Last reviewed timestamp in UTC

`2026-10-22T17:14:17Z`
