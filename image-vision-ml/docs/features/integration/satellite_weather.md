---
feature_id: integration.satellite_weather
name: "Satellite\u2013weather integration"
category: integration
status: implemented
mathematical_method: Join validated NDVI scenes to leakage-safe weather windows on
  UTC date D
input_datasets:
- Processed Sentinel-2 NDVI scenes
- ERA5-Land daily weather
source_code:
- ml/integration/satellite_weather.py
- ml/integration/validate.py
- ml/ingestion/pipeline.py
configuration:
- configs/satellite_multiyear.yaml
- configs/weather_era5_land.yaml
outputs:
- integration CSV/JSON
- integration_quality.json
tests:
- tests/test_satellite_weather.py
- tests/test_integration_integrity.py
- backend/tests/test_integration_api.py
documentation: docs/features/integration/satellite_weather.md
last_verified: '2026-10-22T07:34:24Z'
related_bugs:
- BUG-0007
---

## 1. Feature ID and name

`integration.satellite_weather` — Satellite–weather integration.

## 2. Status and version

Status: `implemented`. Satellite processing version 1.1.0 and integration version 3.2.0 apply where those modules are used. Pixel-exclusion accounting version is 1.0.0.

## 3. Purpose

Build one observation row per satellite scene with NDVI summaries and prior weather, without fabricating values.

## 4. Scientific background

INTEGRATION_VERSION 3.2.0. Weather is one native ERA5-Land cell; NDVI is 10 m AOI statistics. They are not resampled onto each other.

## 5. Mathematical formula or algorithm

Row keys: scene_id, date D, ndvi_mean, valid_ndvi_pct, plus P_prev_N and completeness flags. suitable_for_modeling requires integrated_complete AND weather ready AND satellite supervised_soil_forecasting ready.

## 6. Explanation of every variable and unit

See integration/features.py catalog. INTEGRATION_VERSION=3.2.0.

## 7. Worked numerical example

A valid June scene with complete 7/14/30-day windows is integrated_complete; it is still not suitable_for_modeling without soil labels.

## 8. Source datasets and provenance

Processed satellite dataset + processed weather dataset.

## 9. Input requirements

Validated (or configured) satellite quality rows and daily weather.

## 10. Processing steps

Load scenes; attach weather features; validate windows; write outputs.

## 11. Implementation paths and functions

`integrate_satellite_weather` (module satellite_weather.py), `ml.integration.validate`.

Source files:
- `ml/integration/satellite_weather.py`
- `ml/integration/validate.py`
- `ml/ingestion/pipeline.py`

## 12. Configuration parameters

quality.include_partial_coverage_in_full_series=false.

- `configs/satellite_multiyear.yaml`
- `configs/weather_era5_land.yaml`

## 13. Outputs and units

Tabular rows; flags; ndvi unitless; weather mm/°C/%/m/s.

## 14. Validation criteria

integration_quality.json issue list; no future dates in windows.

## 15. Missing-value handling

Incomplete weather stays in the table with nulls.

## 16. Temporal leakage considerations

Enforced by prior_window_dates.

## 17. Tests and expected assertions

Integrity tests recompute precipitation windows.

- `tests/test_satellite_weather.py`
- `tests/test_integration_integrity.py`
- `backend/tests/test_integration_api.py`

## 18. Scientific limitations

Spatial mismatch (~5 km weather cell vs 10 m NDVI) is structural.

## 19. Related feature dependencies

- [`weather.historical_rolling_features`](../weather/historical_rolling_features.md)
- [`integration.temporal_leakage_prevention`](temporal_leakage_prevention.md)
- [`integration.modeling_eligibility`](modeling_eligibility.md)

## 20. Related bug/fix IDs

[`BUG-0007`](../../bugs/BUG-0007.md)

## 21. Last reviewed timestamp in UTC

`2026-10-22T07:34:24Z`
