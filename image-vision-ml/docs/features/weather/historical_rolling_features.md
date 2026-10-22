---
feature_id: weather.historical_rolling_features
name: Historical rolling weather features
category: weather
status: implemented
mathematical_method: P_prev_N(D) = sum_{i=1..N} P[D-i]; date D excluded
input_datasets:
- Processed daily ERA5-Land rows
- Sentinel-2 acquisition date D
source_code:
- ml/integration/satellite_weather.py
- ml/integration/features.py
configuration:
- configs/weather_era5_land.yaml
- configs/satellite_multiyear.yaml
outputs:
- precip_prev_7d_mm
- precip_prev_14d_mm
- precip_prev_30d_mm
- window_*_complete
tests:
- tests/test_satellite_weather.py
- tests/test_integration_integrity.py
documentation: docs/features/weather/historical_rolling_features.md
last_verified: '2026-10-22T07:34:24Z'
related_bugs: []
---

## 1. Feature ID and name

`weather.historical_rolling_features` — Historical rolling weather features.

## 2. Status and version

Status: `implemented`. Satellite processing version 1.1.0 and integration version 3.2.0 apply where those modules are used. Pixel-exclusion accounting version is 1.0.0.

## 3. Purpose

Attach leakage-safe prior-N-day weather totals to each satellite acquisition date.

## 4. Scientific background

Using rain on the overpass day, or later days, would leak information that would not be available for a true forecast.

## 5. Mathematical formula or algorithm

For UTC calendar date D and window N ∈ {7,14,30}: days = D-N … D-1. P_prev_N = Σ precipitation_total_mm. Emitted only if every day is a complete valid observation; otherwise null. Same rule for temperature mean, evaporation sum, 7-day RH/wind, and 30-day dry-day count (P < 1.0 mm).

## 6. Explanation of every variable and unit

D: UTC date of Sentinel-2 acquisition. N: days. P: mm. dry_day_precipitation_mm=1.0.

## 7. Worked numerical example

D=2025-04-21, N=7 uses 2025-04-14..2025-04-20, never 2025-04-21.

## 8. Source datasets and provenance

Daily weather table + satellite acquisition timestamps.

## 9. Input requirements

Complete daily rows; satellite observation date.

## 10. Processing steps

prior_window_dates; _sum_or_missing / _mean_or_missing; flags window_Nd_complete.

## 11. Implementation paths and functions

`prior_window_dates`, weather feature builders in satellite_weather.py; catalog in integration/features.py.

Source files:
- `ml/integration/satellite_weather.py`
- `ml/integration/features.py`

## 12. Configuration parameters

features.windows_days=[7,14,30], dry_day_precipitation_mm=1.0.

- `configs/weather_era5_land.yaml`
- `configs/satellite_multiyear.yaml`

## 13. Outputs and units

Millimetres for sums; °C for means; percent; m/s; boolean completeness flags.

## 14. Validation criteria

Recompute from daily rows in integration validate. Incomplete windows stay null.

## 15. Missing-value handling

Never replaced with 0.

## 16. Temporal leakage considerations

Acquisition day D is excluded. No later weather. Not truncated to hours before overpass.

## 17. Tests and expected assertions

Window start/end assertions; quality_status warning does not zero-fill future rain.

- `tests/test_satellite_weather.py`
- `tests/test_integration_integrity.py`

## 18. Scientific limitations

Complete windows on a sparse NDVI archive are not soil-forecast labels.

## 19. Related feature dependencies

- [`integration.temporal_leakage_prevention`](../integration/temporal_leakage_prevention.md)
- [`weather.precipitation_aggregation`](precipitation_aggregation.md)

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T07:34:24Z`
