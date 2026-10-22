---
feature_id: ml.historical_soil_weather_features
name: Historical soil and weather features
category: ml
status: implemented
mathematical_method: 'complete-window means/sums/slopes on D-N…D-1; incomplete windows null'
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
documentation: docs/features/ml/historical_soil_weather_features.md
last_verified: '2026-10-22T17:14:17Z'
related_bugs: []
---

## 1. Feature ID and name

`ml.historical_soil_weather_features` — Historical soil and weather features.

## 2. Status and version

Status: `implemented`. Agricultural ML pipeline version 4.0.0. No trained forecasting model.

## 3. Purpose

Attach leakage-safe soil-moisture history and weather history to each research issue date.

## 4. Scientific background

Soil moisture has memory. Rainfall, temperature, humidity, wind and evaporation over recent completed days are physically relevant drivers. ERA5 evaporation is not crop ET.

## 5. Mathematical formula or algorithm

\(\bar\theta^{(N)}_D=(1/N)\sum_{i=1}^{N}\theta_{D-i}\). \(\Delta\theta_{\mathrm{prev1}}=\theta_{D-1}-\theta_{D-2}\). Slope \((\theta_{D-1}-\theta_{D-N})/(N-1)\) for N in {3,7,14}. Precipitation sums and evaporation sums over the same windows. Calendar sin/cos from the issue date.

## 6. Explanation of every variable and unit

Soil: m³/m³. Precipitation and evaporation: mm. Temperature: °C. RH: percent. Wind: m s⁻¹. Windows 1, 3, 7, 14, 30 days.

## 7. Worked numerical example

Fixture precipitation = day-of-month. Issue 10 April 2024: precip_prev_7d_mm=42; precip_prev_1d_mm=9; swvl1_prev1=0.09; delta_prev1=0.01. January 2023 30-day rainfall is null, not 0.

## 8. Source datasets and provenance

daily_soil.csv and daily_weather.csv. Static texture/SOC/elevation remain unavailable nulls.

## 9. Input requirements

Complete valid days with 24 hourly weather records and complete_day soil rows.

## 10. Processing steps

`build_daily_features` → `soil_history_features` + `weather_history_features` + `calendar_features` + null static contracts.

## 11. Implementation paths and functions

`ml.agricultural_ml.features`. Reuses `prior_window_dates`.

Source files:

- [`ml/agricultural_ml/`](../../../ml/agricultural_ml/)
- [`scripts/agricultural_ml_dataset.py`](../../../scripts/agricultural_ml_dataset.py)
- [`configs/agricultural_ml_dataset.yaml`](../../../configs/agricultural_ml_dataset.yaml)

## 12. Configuration parameters

feature_windows_days: [1,3,7,14,30]; minimum_history_days: 30; dry_day_precipitation_mm: 1.0.

## 13. Outputs and units

features_daily.csv (168 columns in the generated Plovdiv table) and feature_catalog.json.

## 14. Validation criteria

Window end dates equal D-1. Incomplete windows set window_Nd_complete false and values null.

## 15. Missing-value handling

Null unless every required day is complete. Never fill with zero.

## 16. Temporal leakage considerations

Windows exclude D and D+1. Features must not contain target_* value columns.

## 17. Tests and expected assertions

[`tests/test_agricultural_ml_dataset.py`](../../../tests/test_agricultural_ml_dataset.py)

April-10 rolling-window fixture; incomplete-history null test.

## 18. Scientific limitations

Single ERA5-Land cell (~4.85 km from AOI centre). P−E is not a closed water balance. No irrigation term.

## 19. Related feature dependencies

- [`soil.root_zone_profile_mean`](../soil/root_zone_profile_mean.md)
- [`weather.precipitation_aggregation`](../weather/precipitation_aggregation.md)
- [`weather.evaporation`](../weather/evaporation.md)

- [`docs/ml/agricultural_forecasting_mathematics.md`](../../ml/agricultural_forecasting_mathematics.md)
- [`docs/ml/scientific_decision_log.md`](../../ml/scientific_decision_log.md)

## 20. Related bug/fix IDs

None created for Phase 4.0. Leakage risks were prevented by construction rather than discovered as production defects.

## 21. Last reviewed timestamp in UTC

`2026-10-22T17:14:17Z`
