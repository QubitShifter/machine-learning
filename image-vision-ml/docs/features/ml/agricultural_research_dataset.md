---
feature_id: ml.agricultural_research_dataset
name: Historical agricultural ML research dataset
category: ml
status: implemented
mathematical_method: 'one issue-date row of leakage-safe features; long target table by horizon and depth'
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
documentation: docs/features/ml/agricultural_research_dataset.md
last_verified: '2026-10-22T17:14:17Z'
related_bugs: []
---

## 1. Feature ID and name

`ml.agricultural_research_dataset` — Historical agricultural ML research dataset.

## 2. Status and version

Status: `implemented`. Agricultural ML pipeline version 4.0.0. No trained forecasting model.

## 3. Purpose

Build a reproducible daily research table for later baseline scoring of modeled ERA5-Land soil moisture. Do not train models.

## 4. Scientific background

Supervised forecasting needs aligned weather, soil and optional satellite context at an explicit issue time. The 2023–2025 Plovdiv archives are complete daily ERA5-Land series and a sparse Sentinel-2 series. A research dataset is not an operational forecast archive.

## 5. Mathematical formula or algorithm

Issue time \(t_D=\) 00:00 UTC on day \(D\). Features use completed days \(D-N\ldots D-1\). Targets are daily means on \(D+h\) for \(h\in\{1,3,7\}\). Dataset ID `plovdiv_agricultural_ml_2023_2025`, version 4.0.0.

## 6. Explanation of every variable and unit

dataset_id; aoi_id; issue_date_utc; feature columns in m³/m³ or mm; target_source_kind=modeled_reanalysis; operational_availability_verified=false.

## 7. Worked numerical example

CLI build on local archives produced 1096 feature rows (2023-01-01 through 2025-12-31), 16440 target rows (1096×3×5), 55 missing end-of-archive targets, leakage_status=passed.

## 8. Source datasets and provenance

Weather `plovdiv_weather_2023_2025` (1096 complete days), soil `plovdiv_soil_2023_2025` (1096 complete days, four layers), satellite `plovdiv_2023_2025` (15 valid scenes). Same ERA5-Land cell 42.1°N, 24.7°E.

## 9. Input requirements

Existing daily_weather.csv and daily_soil.csv. No network. Soil quality suitable_for_modeling must remain false.

## 10. Processing steps

`scripts.agricultural_ml_dataset check|build|validate|audit-leakage|splits|report`. Atomic JSON writes. CSV always; Parquet optional if pyarrow exists (skipped in this environment).

## 11. Implementation paths and functions

`ml.agricultural_ml.pipeline.build_dataset`, `check_config`, `validate_dataset`.

Source files:

- [`ml/agricultural_ml/`](../../../ml/agricultural_ml/)
- [`scripts/agricultural_ml_dataset.py`](../../../scripts/agricultural_ml_dataset.py)
- [`configs/agricultural_ml_dataset.yaml`](../../../configs/agricultural_ml_dataset.yaml)

## 12. Configuration parameters

`configs/agricultural_ml_dataset.yaml`: period, sources, windows, horizons, splits, satellite max_age_days, output directory.

## 13. Outputs and units

`features_daily.csv`, `targets.csv`, `split_membership.csv`, `modeling_samples.csv` (experiment A, satellite columns dropped), catalogs, fingerprints, leakage, readiness, diagnostics, summary, manifest under `data/processed/ml/plovdiv_agricultural_ml_2023_2025/`.

## 14. Validation criteria

fail_on_critical_leakage; source files present; suitable_for_modeling false in outputs.

## 15. Missing-value handling

Incomplete windows and future targets stay null. Zero millimetres is a measured dry day, never a fill.

## 16. Temporal leakage considerations

Primary table has one row per issue date, not per horizon. Targets live in targets.csv. Wide target_* columns exist only on modeling_samples.csv.

## 17. Tests and expected assertions

[`tests/test_agricultural_ml_dataset.py`](../../../tests/test_agricultural_ml_dataset.py)

CLI check/dry-run; 1096-row rebuild is deterministic given local CSVs.

## 18. Scientific limitations

Three years, one coarse grid cell, modeled soil water, unverified publication times. Not field-scale and not operationally deployable.

## 19. Related feature dependencies

- [`ml.issue_time_cutoff`](issue_time_cutoff.md)
- [`weather.historical_rolling_features`](../weather/historical_rolling_features.md)
- [`soil.era5_land_volumetric_moisture`](../soil/era5_land_volumetric_moisture.md)

- [`docs/ml/agricultural_forecasting_mathematics.md`](../../ml/agricultural_forecasting_mathematics.md)
- [`docs/ml/scientific_decision_log.md`](../../ml/scientific_decision_log.md)

## 20. Related bug/fix IDs

None created for Phase 4.0. Leakage risks were prevented by construction rather than discovered as production defects.

## 21. Last reviewed timestamp in UTC

`2026-10-22T17:14:17Z`
