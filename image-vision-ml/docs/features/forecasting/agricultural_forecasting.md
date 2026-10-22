---
feature_id: forecasting.agricultural_forecasting
name: Agricultural forecasting
category: forecasting
status: planned
mathematical_method: Not implemented. No trained forecast model exists in this task
  scope.
input_datasets:
- None
source_code: []
configuration: []
outputs:
- none
tests: []
documentation: docs/features/forecasting/agricultural_forecasting.md
last_verified: '2026-10-22T07:34:24Z'
related_bugs: []
---

## 1. Feature ID and name

`forecasting.agricultural_forecasting` — Agricultural forecasting.

## 2. Status and version

Status: `planned`. Satellite processing version 1.1.0 and integration version 3.2.0 apply where those modules are used. Pixel-exclusion accounting version is 1.0.0.

## 3. Purpose

Eventually predict crop and water-stress outcomes. Operational agricultural forecasting remains unimplemented. Phase 4.1 trains research baselines on ERA5-Land modeled soil moisture under [`ml.soil_forecast_experiment`](../ml/soil_forecast_experiment.md); those results are not operational forecasts, irrigation advice, or field-validated skill.

## 4. Scientific background

Forecasting requires a specified target, a time-respecting split, and independent labels.

## 5. Mathematical formula or algorithm

No model loss, architecture, or prediction equation is implemented.

## 6. Explanation of every variable and unit

n/a

## 7. Worked numerical example

n/a

## 8. Source datasets and provenance

n/a

## 9. Input requirements

Would require modeling-ready rows, which currently do not exist for soil forecasting.

## 10. Processing steps

Planned only. This task explicitly forbids training.

## 11. Implementation paths and functions

No training pipeline invoked.

Source files:
- `*(none — planned)*`

## 12. Configuration parameters

none

No configuration file.

## 13. Outputs and units

none

## 14. Validation criteria

suitable_for_modeling remains 0.

## 15. Missing-value handling

n/a

## 16. Temporal leakage considerations

Any future model must keep WINDOW_RULE.

## 17. Tests and expected assertions

No forecast tests because there is no forecast implementation.

No dedicated implementation tests (planned feature).

## 18. Scientific limitations

Planned. NDVI time series is not a yield forecast.

## 19. Related feature dependencies

- [`integration.modeling_eligibility`](../integration/modeling_eligibility.md)
- [`ml.agricultural_research_dataset`](../ml/agricultural_research_dataset.md)
- [`ml.forecast_evaluation_contracts`](../ml/forecast_evaluation_contracts.md)
- [`ml.soil_forecast_experiment`](../ml/soil_forecast_experiment.md)

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T07:34:24Z`
