---
feature_id: ml.soil_moisture_target_construction
name: Soil-moisture target construction
category: ml
status: implemented
mathematical_method: 'y_{D,h}=mean θ on UTC day D+h; Δθ=y_{D,h}-θ_{D-1}'
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
documentation: docs/features/ml/soil_moisture_target_construction.md
last_verified: '2026-10-22T17:14:17Z'
related_bugs: []
---

## 1. Feature ID and name

`ml.soil_moisture_target_construction` — Soil-moisture target construction.

## 2. Status and version

Status: `implemented`. Agricultural ML pipeline version 4.0.0. No trained forecasting model.

## 3. Purpose

Define leakage-safe absolute and change targets for four layers and the 0–100 cm profile at horizons 1, 3 and 7 days.

## 4. Scientific background

The predictand is a future daily mean state, not an instantaneous midnight value. Change uses the last complete historical day as baseline so the model is not asked to predict a quantity that includes θ_D.

## 5. Mathematical formula or algorithm

For each variable in {swvl1, swvl2, swvl3, swvl4, θ_{0-100}} and h in {1,3,7}: absolute target = daily mean on D+h; change = absolute − value on D−1. Persistence prediction = θ_{D-1}. Missing if D+h is outside the archive.

## 6. Explanation of every variable and unit

Unit m³/m³. target_kind=daily_mean_state. target_source_kind=modeled_reanalysis. is_ground_truth=false.

## 7. Worked numerical example

Issue 2024-04-10, h=1, fixture θ=0.01×day: target_date=2024-04-11, absolute=0.11, baseline date=2024-04-09, change=0.02. Issue 2025-12-30 h=7 is null with future_target_outside_dataset_period. Real archive: 16385 available, 55 missing.

## 8. Source datasets and provenance

daily_soil.csv from plovdiv_soil_2023_2025. Layer depths from SOIL_LAYERS; profile weights unchanged.

## 9. Input requirements

Complete target day. No interpolation across missing future days.

## 10. Processing steps

`build_targets` writes a long table; `wide_targets` is only for modeling_samples.csv.

## 11. Implementation paths and functions

`ml.agricultural_ml.targets`.

Source files:

- [`ml/agricultural_ml/`](../../../ml/agricultural_ml/)
- [`scripts/agricultural_ml_dataset.py`](../../../scripts/agricultural_ml_dataset.py)
- [`configs/agricultural_ml_dataset.yaml`](../../../configs/agricultural_ml_dataset.yaml)

## 12. Configuration parameters

targets.variables, targets.horizons_days=[1,3,7], change_baseline=last_complete_historical_day.

## 13. Outputs and units

targets.csv and target_catalog.json. Column names target_{var}_h{h} and target_{var}_delta_h{h} in the wide export.

## 14. Validation criteria

target_period_start > issue_time; baseline date = D-1; missing remain missing.

## 15. Missing-value handling

Null + missing_reason. Never 0-fill missing soil.

## 16. Temporal leakage considerations

Targets must not appear as feature columns. End-of-series nulls are not leakage.

## 17. Tests and expected assertions

[`tests/test_agricultural_ml_dataset.py`](../../../tests/test_agricultural_ml_dataset.py)

test_targets_h1_h3_h7_and_change_baseline; test_missing_end_of_series_targets_stay_null.

## 18. Scientific limitations

Modeled reanalysis labels. Not independent sensors. Not crop-specific available water.

## 19. Related feature dependencies

- [`soil.era5_land_volumetric_moisture`](../soil/era5_land_volumetric_moisture.md)
- [`soil.root_zone_profile_mean`](../soil/root_zone_profile_mean.md)

- [`docs/ml/agricultural_forecasting_mathematics.md`](../../ml/agricultural_forecasting_mathematics.md)
- [`docs/ml/scientific_decision_log.md`](../../ml/scientific_decision_log.md)

## 20. Related bug/fix IDs

None created for Phase 4.0. Leakage risks were prevented by construction rather than discovered as production defects.

## 21. Last reviewed timestamp in UTC

`2026-10-22T17:14:17Z`
