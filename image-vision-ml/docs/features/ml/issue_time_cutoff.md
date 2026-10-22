---
feature_id: ml.issue_time_cutoff
name: Research issue-time cutoff
category: ml
status: implemented
mathematical_method: 't_D = 00:00 UTC on D; last complete observation D-1'
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
documentation: docs/features/ml/issue_time_cutoff.md
last_verified: '2026-10-22T17:14:17Z'
related_bugs: []
---

## 1. Feature ID and name

`ml.issue_time_cutoff` — Research issue-time cutoff.

## 2. Status and version

Status: `implemented`. Agricultural ML pipeline version 4.0.0. No trained forecasting model.

## 3. Purpose

Make observation time, validity time, issue time and target time explicit so historical features cannot include day D or later.

## 4. Scientific background

ERA5-Land daily means are complete only after the UTC day ends. Midnight on D is before that completion. Publication time is a separate unknown.

## 5. Mathematical formula or algorithm

\(t_D=\) 00:00 UTC on \(D\). Last observation date = \(D-1\). Feature cutoff = \(t_D\). Target period for horizon \(h\): \([D+h\ 00:00,\ D+h+1\ 00:00)\) UTC. Modes: research_reanalysis (default), operational_replay (not verified), perfect_weather_hindcast (not enabled).

## 6. Explanation of every variable and unit

issue_date_utc (date); issue_time_utc (UTC timestamp); last_observation_date_utc; feature_cutoff_time_utc; data_availability_mode; operational_availability_verified.

## 7. Worked numerical example

Issue 2024-04-10: last observation 2024-04-09; 7-day window 2024-04-03 through 2024-04-09; 10 April excluded. Leap-year calendar uses L=366; 2024-03-01 day_of_year=61.

## 8. Source datasets and provenance

No additional ingested product. Time is the UTC calendar of the existing daily tables.

## 9. Input requirements

Valid ISO dates in the configured period.

## 10. Processing steps

`issue_datetime_utc`, `last_observation_date`, `target_period`, `calendar_features` in `time_semantics.py`.

## 11. Implementation paths and functions

`ml.agricultural_ml.time_semantics`.

Source files:

- [`ml/agricultural_ml/`](../../../ml/agricultural_ml/)
- [`scripts/agricultural_ml_dataset.py`](../../../scripts/agricultural_ml_dataset.py)
- [`configs/agricultural_ml_dataset.yaml`](../../../configs/agricultural_ml_dataset.yaml)

## 12. Configuration parameters

issue_time.convention=beginning_of_utc_day; research_mode=research_reanalysis; operational_availability_verified=false.

## 13. Outputs and units

Time columns on every feature and target row.

## 14. Validation criteria

last_observation_date < issue_date; target_period_start > issue_time for h≥1.

## 15. Missing-value handling

Not applicable to timestamps; missing source days make features null.

## 16. Temporal leakage considerations

Same-day soil or rainfall at D is leakage. Future realized weather labeled operational is leakage.

## 17. Tests and expected assertions

[`tests/test_agricultural_ml_dataset.py`](../../../tests/test_agricultural_ml_dataset.py)

test_issue_cutoff_excludes_d_and_d_plus_one; leap-year and year-transition window tests.

## 18. Scientific limitations

Does not prove CDS/ERA5-Land availability at t_D. Date-only satellite times are conservative.

## 19. Related feature dependencies

- [`forecasting.issue_valid_time_contracts`](../forecasting/issue_valid_time_contracts.md)
- [`integration.temporal_leakage_prevention`](../integration/temporal_leakage_prevention.md)

- [`docs/ml/agricultural_forecasting_mathematics.md`](../../ml/agricultural_forecasting_mathematics.md)
- [`docs/ml/scientific_decision_log.md`](../../ml/scientific_decision_log.md)

## 20. Related bug/fix IDs

None created for Phase 4.0. Leakage risks were prevented by construction rather than discovered as production defects.

## 21. Last reviewed timestamp in UTC

`2026-10-22T17:14:17Z`
