---
feature_id: integration.modeling_eligibility
name: Modeling eligibility
category: integration
status: implemented
mathematical_method: Task-specific readiness; suitable_for_modeling is supervised
  soil forecasting only
input_datasets:
- Coverage diagnostics
- integration metrics
- quality reports
source_code:
- ml/validation/modeling_readiness.py
- ml/validation/dataset_quality.py
configuration:
- configs/satellite_multiyear.yaml
outputs:
- task_readiness.json
- suitable_for_modeling flag
tests:
- tests/test_modeling_readiness.py
- tests/test_dataset_quality.py
documentation: docs/features/integration/modeling_eligibility.md
last_verified: '2026-10-22T08:49:05Z'
related_bugs:
- BUG-0006
---

## 1. Feature ID and name

`integration.modeling_eligibility` — Modeling eligibility.

## 2. Status and version

Status: `implemented`. Satellite processing version 1.1.0 and integration version 3.2.0 apply where those modules are used. Pixel-exclusion accounting version is 1.0.0.

## 3. Purpose

Separate exploratory NDVI analysis, weather–NDVI relationship work, vegetation forecasting research, and supervised soil-moisture forecasting.

## 4. Scientific background

A validated NDVI archive is not a labelled soil-moisture dataset.

## 5. Mathematical formula or algorithm

suitable_for_modeling = integrated_complete AND weather ready AND satellite supervised_soil_forecasting ready. Ground-truth soil moisture is currently unavailable ⇒ soil task not_ready.

## 6. Explanation of every variable and unit

Tasks: exploratory_ndvi_analysis, weather_ndvi_relationship_analysis, vegetation_forecasting, soil_moisture_historical_analysis, rainfall_derived_wetness_analysis, modeled_soil_moisture_forecasting_research, independently_validated_field_soil_moisture_forecasting, supervised_soil_forecasting. ERA5-Land modeled soil water may make historical analysis ready; it does not make supervised_soil_forecasting or suitable_for_modeling true.

## 7. Worked numerical example

15 complete integration windows with 0 soil labels ⇒ 0 modeling-ready rows.

## 8. Source datasets and provenance

Derived from existing quality/integration artefacts.

## 9. Input requirements

Quality summary, coverage, integration_quality metrics.

## 10. Processing steps

assess_task_readiness; do not weaken suitable_for_modeling.

## 11. Implementation paths and functions

`assess_task_readiness`, `assess_training_readiness`.

Source files:
- `ml/validation/modeling_readiness.py`
- `ml/validation/dataset_quality.py`

## 12. Configuration parameters

DEFAULT_READINESS in ml/ingestion/config.py.

- `configs/satellite_multiyear.yaml`

## 13. Outputs and units

status strings ready|limited|not_ready; structured exclusion reasons.

## 14. Validation criteria

Soil forecasting remains not_ready without labels.

## 15. Missing-value handling

Missing labels are exclusion reasons, not imputed targets.

## 16. Temporal leakage considerations

Readiness checks do not create training tensors.

## 17. Tests and expected assertions

tests/test_modeling_readiness.py.

- `tests/test_modeling_readiness.py`
- `tests/test_dataset_quality.py`

## 18. Scientific limitations

Operational thresholds for scene counts/years are project-specific.

## 19. Related feature dependencies

- [`satellite.temporal_coverage`](../satellite/temporal_coverage.md)
- [`integration.satellite_weather`](satellite_weather.md)

## 20. Related bug/fix IDs

[`BUG-0006`](../../bugs/BUG-0006.md)

## 21. Last reviewed timestamp in UTC

`2026-10-22T08:49:05Z`
