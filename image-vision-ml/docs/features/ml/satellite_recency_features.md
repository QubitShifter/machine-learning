---
feature_id: ml.satellite_recency_features
name: Quality-gated satellite recency features
category: ml
status: implemented
mathematical_method: 'latest valid scene with acquisition < t_D and age ≤ max_age_days; else null'
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
documentation: docs/features/ml/satellite_recency_features.md
last_verified: '2026-10-22T17:14:17Z'
related_bugs: []
---

## 1. Feature ID and name

`ml.satellite_recency_features` — Quality-gated satellite recency features.

## 2. Status and version

Status: `implemented`. Agricultural ML pipeline version 4.0.0. No trained forecasting model.

## 3. Purpose

Optionally attach the most recent scientifically usable NDVI context without fabricating daily vegetation.

## 4. Scientific background

Sentinel-2 over the AOI is irregular (15 valid scenes). Forward-filling NDVI would invent observations. Rejected and calibration-review scenes are excluded.

## 5. Mathematical formula or algorithm

Eligible if quality_status=valid, calibration_status=verified, acquisition < issue cutoff. Age=(issue_date − acquisition_date) in days. If age > max_age_days, NDVI fields null and satellite_stale=true. No P10/P90 invented when source percentiles are absent.

## 6. Explanation of every variable and unit

ndvi_last_valid_mean/median/std; age_days; scene_id; valid_pixel_fraction; calibration_status. Spatial support is 10 m Sentinel-2, not the ERA5 cell.

## 7. Worked numerical example

Scene acquired 2024-04-10 09:00 is ineligible at issue 2024-04-10T00:00:00Z. Scene 2024-04-03 is age 7 on 2024-04-10 and usable if max_age=14, stale if max_age=5. Generated table: 15 eligible scenes, 210 issue days with non-stale NDVI, 833 stale, 53 missing (before 2023-02-23).

## 8. Source datasets and provenance

dataset_quality.json scenes plus ndvi_timeseries.json. February/March 2025 calibration-review scenes remain unused.

## 9. Input requirements

Processed quality report. No catalog search or download.

## 10. Processing steps

`load_eligible_satellite_observations` then `satellite_features_for_issue`.

## 11. Implementation paths and functions

`ml.agricultural_ml.satellite`.

Source files:

- [`ml/agricultural_ml/`](../../../ml/agricultural_ml/)
- [`scripts/agricultural_ml_dataset.py`](../../../scripts/agricultural_ml_dataset.py)
- [`configs/agricultural_ml_dataset.yaml`](../../../configs/agricultural_ml_dataset.yaml)

## 12. Configuration parameters

satellite.max_age_days=14; alternative_max_age_days=30 (not asserted optimal); fill_unobserved_days=false; availability_assumption=acquisition_time_only_research.

## 13. Outputs and units

Optional columns on features_daily.csv. modeling_samples.csv is experiment A without those columns.

## 14. Validation criteria

No future acquisition; no NDVI without scene_id; rejected/review excluded.

## 15. Missing-value handling

Unobserved and stale days are null. Absence of satellite does not drop the weather–soil row.

## 16. Temporal leakage considerations

An image acquired on D is not available at D 00:00 UTC. Operational availability unverified.

## 17. Tests and expected assertions

[`tests/test_agricultural_ml_dataset.py`](../../../tests/test_agricultural_ml_dataset.py)

test_satellite_rejects_issue_day_and_stale; test_rejected_and_review_scenes_are_not_loaded.

## 18. Scientific limitations

Fifteen scenes cannot prove incremental forecasting value. Date-only timestamps use midnight UTC.

## 19. Related feature dependencies

- [`satellite.ndvi`](../satellite/ndvi.md)
- [`satellite.reflectance_calibration`](../satellite/reflectance_calibration.md)
- [`integration.satellite_weather`](../integration/satellite_weather.md)

- [`docs/ml/agricultural_forecasting_mathematics.md`](../../ml/agricultural_forecasting_mathematics.md)
- [`docs/ml/scientific_decision_log.md`](../../ml/scientific_decision_log.md)

## 20. Related bug/fix IDs

None created for Phase 4.0. Leakage risks were prevented by construction rather than discovered as production defects.

## 21. Last reviewed timestamp in UTC

`2026-10-22T17:14:17Z`
