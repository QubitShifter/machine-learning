---
feature_id: ml.horizon_aware_chronological_splits
name: Horizon-aware chronological splits
category: ml
status: implemented
mathematical_method: 'issue-date holdout 2023/2024/2025 with purge if target_date ≥ next partition start'
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
documentation: docs/features/ml/horizon_aware_chronological_splits.md
last_verified: '2026-10-22T17:14:17Z'
related_bugs: []
---

## 1. Feature ID and name

`ml.horizon_aware_chronological_splits` — Horizon-aware chronological splits.

## 2. Status and version

Status: `implemented`. Agricultural ML pipeline version 4.0.0. No trained forecasting model.

## 3. Purpose

Assign train/validation/test without random mixing and without labels crossing the next partition.

## 4. Scientific background

Overlapping 7-day targets near 31 December would otherwise put January validation soil moisture into training.

## 5. Mathematical formula or algorithm

Partition by issue date. If purge_target_crossing and target_date ≥ start of next partition, split=excluded_purge. Expanding-window config exists but is disabled. Features may use earlier partitions as history.

## 6. Explanation of every variable and unit

split in {training, validation, test, excluded_purge}; horizon_days; target_date_utc; exclusion_reason.

## 7. Worked numerical example

Issue 2023-12-24 h=7 → target 2023-12-31 remains training. Issue 2023-12-25 h=7 → target 2024-01-01 purged. Generated: 110 purged rows (2 boundaries × (1+3+7) days × 5 variables). Training h=1 issue days=364; validation h=1=365; test h=1=365.

## 8. Source datasets and provenance

targets.csv issue dates and configured split windows.

## 9. Input requirements

Configured start/end per partition. 2024 is a leap year.

## 10. Processing steps

`assign_split`, `build_split_membership`.

## 11. Implementation paths and functions

`ml.agricultural_ml.splits`.

Source files:

- [`ml/agricultural_ml/`](../../../ml/agricultural_ml/)
- [`scripts/agricultural_ml_dataset.py`](../../../scripts/agricultural_ml_dataset.py)
- [`configs/agricultural_ml_dataset.yaml`](../../../configs/agricultural_ml_dataset.yaml)

## 12. Configuration parameters

splits.training/validation/test dates; purge_target_crossing=true; expanding_window.enabled=false.

## 13. Outputs and units

split_membership.csv and split_quality_report.json.

## 14. Validation criteria

No training/validation row with target_crosses_next_split left included. Audit split_target_crossover.

## 15. Missing-value handling

Purged rows are retained with reason, not deleted from disk.

## 16. Temporal leakage considerations

Purging labels is required; erasing legitimate previous-day features at January 1 is not.

## 17. Tests and expected assertions

[`tests/test_agricultural_ml_dataset.py`](../../../tests/test_agricultural_ml_dataset.py)

test_horizon_aware_split_purge; test_split_audit_flags_unpurged_training_label.

## 18. Scientific limitations

Three years are a starting design, not proof of generalization. No K-fold.

## 19. Related feature dependencies

- [`ml.soil_moisture_target_construction`](soil_moisture_target_construction.md)
- [`integration.modeling_eligibility`](../integration/modeling_eligibility.md)

- [`docs/ml/agricultural_forecasting_mathematics.md`](../../ml/agricultural_forecasting_mathematics.md)
- [`docs/ml/scientific_decision_log.md`](../../ml/scientific_decision_log.md)

## 20. Related bug/fix IDs

None created for Phase 4.0. Leakage risks were prevented by construction rather than discovered as production defects.

## 21. Last reviewed timestamp in UTC

`2026-10-22T17:14:17Z`
