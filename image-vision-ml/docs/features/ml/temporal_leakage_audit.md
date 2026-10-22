---
feature_id: ml.temporal_leakage_audit
name: Temporal leakage detection
category: ml
status: implemented
mathematical_method: 'automated invariants: t_source < t_issue; t_target start > t_issue; no split crossover'
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
documentation: docs/features/ml/temporal_leakage_audit.md
last_verified: '2026-10-22T17:14:17Z'
related_bugs: []
---

## 1. Feature ID and name

`ml.temporal_leakage_audit` — Temporal leakage detection.

## 2. Status and version

Status: `implemented`. Agricultural ML pipeline version 4.0.0. No trained forecasting model.

## 3. Purpose

Refuse to accept a research dataset that silently contains future rainfall, same-day soil, future satellite, or split-crossing labels.

## 4. Scientific background

Off-by-one window bugs and API date joins are common. Critical failures abort build.

## 5. Mathematical formula or algorithm

Checks: feature_time_invariant, target_time_invariant, target_feature_column_collision, split_target_crossover, satellite_availability, missing_not_replaced_with_zero, research_mode_not_operational. Fixture helper detects inflated prev-7 rainfall.

## 6. Explanation of every variable and unit

Each check: check_id, severity, status, affected_row_count, example dates, explanation, suggested correction.

## 7. Worked numerical example

Injecting April 10 rain into prev-7 for issue April 10 fails future_rainfall_excluded. Zero-filling an incomplete 30-day window fails missing_not_replaced_with_zero. operational_availability_verified=true fails research_mode_not_operational. Real 2023–2025 build: all seven checks passed, critical_failures=0.

## 8. Source datasets and provenance

Generated feature, target and split tables.

## 9. Input requirements

Build runs the audit before writing when fail_on_critical_leakage is true.

## 10. Processing steps

`run_leakage_audit` in `ml.agricultural_ml.leakage`. CLI `audit-leakage`.

## 11. Implementation paths and functions

`ml.agricultural_ml.leakage`.

Source files:

- [`ml/agricultural_ml/`](../../../ml/agricultural_ml/)
- [`scripts/agricultural_ml_dataset.py`](../../../scripts/agricultural_ml_dataset.py)
- [`configs/agricultural_ml_dataset.yaml`](../../../configs/agricultural_ml_dataset.yaml)

## 12. Configuration parameters

validation.fail_on_critical_leakage=true.

## 13. Outputs and units

temporal_leakage_report.json.

## 14. Validation criteria

status must be passed for validate_dataset.

## 15. Missing-value handling

Incomplete windows must be null, not 0. That is treated as leakage because it fabricates a dry month.

## 16. Temporal leakage considerations

This feature is the leakage control for Phase 4.0.

## 17. Tests and expected assertions

[`tests/test_agricultural_ml_dataset.py`](../../../tests/test_agricultural_ml_dataset.py)

Sentinel fixtures in tests/test_agricultural_ml_dataset.py.

## 18. Scientific limitations

Cannot detect every conceptual misuse (for example using diagnostics as fitted scalers in a later phase).

## 19. Related feature dependencies

- [`integration.temporal_leakage_prevention`](../integration/temporal_leakage_prevention.md)
- [`ml.issue_time_cutoff`](issue_time_cutoff.md)

- [`docs/ml/agricultural_forecasting_mathematics.md`](../../ml/agricultural_forecasting_mathematics.md)
- [`docs/ml/scientific_decision_log.md`](../../ml/scientific_decision_log.md)

## 20. Related bug/fix IDs

None created for Phase 4.0. Leakage risks were prevented by construction rather than discovered as production defects.

## 21. Last reviewed timestamp in UTC

`2026-10-22T17:14:17Z`
