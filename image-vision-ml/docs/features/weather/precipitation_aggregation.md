---
feature_id: weather.precipitation_aggregation
name: Precipitation aggregation
category: weather
status: implemented
mathematical_method: P_mm(D) = 1000 * tp(D+1 00:00 UTC); hourly increments only if
  that boundary exists
input_datasets:
- ERA5-Land total_precipitation
source_code:
- ml/preprocessing/weather.py
configuration:
- configs/weather_era5_land.yaml
outputs:
- precipitation_total_mm
- precipitation_method
tests:
- tests/test_weather.py
documentation: docs/features/weather/precipitation_aggregation.md
last_verified: '2026-10-22T07:34:24Z'
related_bugs:
- BUG-0001
- BUG-0003
---

## 1. Feature ID and name

`weather.precipitation_aggregation` — Precipitation aggregation.

## 2. Status and version

Status: `implemented`. Satellite processing version 1.1.0 and integration version 3.2.0 apply where those modules are used. Pixel-exclusion accounting version is 1.0.0.

## 3. Purpose

Convert ERA5-Land accumulated precipitation to daily UTC millimetre totals without zero-filling missing days.

## 4. Scientific background

ERA5-Land tp is a forecast-cycle accumulation in metres, positive downward. The official daily total for UTC day D is the 00:00 UTC value of day D+1.

## 5. Mathematical formula or algorithm

P_mm = 1000 * tp_{D+1,00UTC} when the boundary exists (method next_day_00utc). Hourly increments: at 01 UTC the stored value is the first-hour increment; later hours are differences; a reset (current < previous) starts a new cycle. Missing boundary ⇒ precipitation_total_mm is null (method missing_boundary), never 0.

## 6. Explanation of every variable and unit

tp: metres. METERS_TO_MM=1000. ROUNDING_MM=1e-6.

## 7. Worked numerical example

Boundary tp=0.006 m → 6.0 mm for the previous UTC day.

## 8. Source datasets and provenance

CDS ERA5-Land total_precipitation plus next-month/day boundary files.

## 9. Input requirements

Hourly tp and the next-day 00:00 record.

## 10. Processing steps

era5_land_daily_total_mm / _daily_flux; require_complete_days flags missing boundaries.

## 11. Implementation paths and functions

`era5_land_daily_total_mm`, `era5_land_hourly_increments`, `_daily_flux`.

Source files:
- `ml/preprocessing/weather.py`

## 12. Configuration parameters

downloads.include_next_day_boundary.

- `configs/weather_era5_land.yaml`

## 13. Outputs and units

precipitation_total_mm (mm), precipitation_method.

## 14. Validation criteria

Negative rainfall beyond rounding requires review. Missing boundary is not zero.

## 15. Missing-value handling

Null, never 0.

## 16. Temporal leakage considerations

Daily total for date D uses D+1 00:00, which is the close of day D, not future weather after a later satellite overpass on D+1 beyond that instant.

## 17. Tests and expected assertions

test_daily_total_uses_next_day_00utc; test_missing_boundary_is_not_zero_filled.

- `tests/test_weather.py`

## 18. Scientific limitations

Reanalysis precipitation can differ from gauges. One grid cell cannot resolve field-scale irrigation.

## 19. Related feature dependencies

- [`weather.era5_land_ingestion`](era5_land_ingestion.md)
- [`weather.historical_rolling_features`](historical_rolling_features.md)

## 20. Related bug/fix IDs

[`BUG-0001`](../../bugs/BUG-0001.md), [`BUG-0003`](../../bugs/BUG-0003.md)

## 21. Last reviewed timestamp in UTC

`2026-10-22T07:34:24Z`
