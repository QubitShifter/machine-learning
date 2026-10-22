---
feature_id: weather.drying_and_wetness_indicators
name: Drying and weather-derived wetness indicators
category: weather
status: implemented
mathematical_method: Dry-day runs, days since rain, trailing P and P-E proxies
input_datasets:
- Daily ERA5-Land precipitation and evaporation
source_code:
- ml/preprocessing/wetness.py
configuration:
- configs/weather_era5_land.yaml
outputs:
- consecutive_dry_days
- days_since_rain
- precip_minus_evap_7d_mm
tests:
- tests/test_soil.py
documentation: docs/features/weather/drying_and_wetness_indicators.md
last_verified: '2026-10-22T08:49:05Z'
related_bugs: []
---

## 1. Feature ID and name

`weather.drying_and_wetness_indicators` — Drying and weather-derived wetness indicators.

## 2. Status and version

Status: `implemented`. Wetness version 3.4.0.

## 3. Purpose

Expose interpretable drying and wetness-proxy columns while keeping rainfall-history, wetness-proxy, and soil-moisture kinds distinct.

## 4. Scientific background

A dry day is P < 1.0 mm by default, matching existing integration. Rainfall minus evaporation is a proxy, not a closed water balance. ERA5-Land total evaporation is not crop ET. Irrigation, runoff and drainage are unknown.

## 5. Mathematical formula or algorithm

Conceptual water balance (not implemented): S_{t+1} = S_t + P_t + I_t − ET_t − R_t − D_t.

Implemented: consecutive dry days; days since P ≥ dry_day_mm; trailing sums of P and E for 7 and 30 days including date D for end-of-day analysis; P_prev_N excluding D for satellite-aligned comparison. Existing integration 7/14/30 windows are not rewritten.

## 6. Explanation of every variable and unit

- P, E: millimetres.
- consecutive_dry_days: integer run length, null after missing P.
- days_since_rain: 0 on a rain day; null until the first rain and after missing P.
- precip_minus_evap_Nd_mm: wetness proxy (mm), kind `weather_derived_wetness_proxy`.
- water_balance_status: `not_estimated`.

## 7. Worked numerical example

P = [5, 0, None, 0, 8] mm, threshold 1 mm. Day 0 rain (0 days since). Day 1 dry (1). Day 2 missing (null). Day 4 rain (0).

## 8. Source datasets and provenance

Daily weather CSV. Not ERA5-Land swvl. Not in-situ moisture.

## 9. Input requirements

`precipitation_total_mm` and `evaporation_total_mm`.

## 10. Processing steps

Same wetness command as API. Does not overwrite satellite–weather integration files.

## 11. Implementation paths and functions

`ml/preprocessing/wetness.py`: `consecutive_dry_days`, `days_since_rain`, `trailing_sum`, `attach_wetness_features`.

Source files:
- [`ml/preprocessing/wetness.py`](../../../ml/preprocessing/wetness.py)

## 12. Configuration parameters

`features.dry_day_precipitation_mm` in [`configs/weather_era5_land.yaml`](../../../configs/weather_era5_land.yaml) remains 1.0.

## 13. Outputs and units

Wetness CSV columns including `precip_prev_*d_mm` (D excluded) and `precip_trailing_*d_end_of_day_mm` (D included).

## 14. Validation criteria

Missing P is not 0. Trailing windows with any missing day are null. Existing D−N…D−1 integration tests must still pass.

## 15. Missing-value handling

A missing day breaks dry-day runs and days-since-rain. Rolling sums require a complete window.

## 16. Temporal leakage considerations

Satellite-aligned P_N(D) = Σ_{i=1..N} P_{D−i}. End-of-day trailing sums include D and must not be used as if they were available at the start of D.

## 17. Tests and expected assertions

[`tests/test_soil.py`](../../../tests/test_soil.py) missing-value and window tests; [`tests/test_satellite_weather.py`](../../../tests/test_satellite_weather.py) unchanged prior windows.

## 18. Scientific limitations

P−E is not soil-water storage. Irrigation is not assumed zero. Water-balance terms I, R, D, crop ET remain `not_estimated`.

## 19. Related feature dependencies

- [`weather.antecedent_precipitation_index`](antecedent_precipitation_index.md)
- [`weather.historical_rolling_features`](historical_rolling_features.md)
- [`weather.evaporation`](evaporation.md)
- [`integration.temporal_leakage_prevention`](../integration/temporal_leakage_prevention.md)

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T08:49:05Z`
