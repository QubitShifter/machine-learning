---
feature_id: weather.temperature_conversion
name: Temperature conversion
category: weather
status: implemented
mathematical_method: T_C = T_K - 273.15
input_datasets:
- ERA5-Land 2m_temperature
source_code:
- ml/preprocessing/weather.py
configuration:
- configs/weather_era5_land.yaml
outputs:
- daily_weather.csv temperature_mean_c/min_c/max_c
tests:
- tests/test_weather.py
documentation: docs/features/weather/temperature_conversion.md
last_verified: '2026-10-22T07:34:24Z'
related_bugs: []
---

## 1. Feature ID and name

`weather.temperature_conversion` — Temperature conversion.

## 2. Status and version

Status: `implemented`. Satellite processing version 1.1.0 and integration version 3.2.0 apply where those modules are used. Pixel-exclusion accounting version is 1.0.0.

## 3. Purpose

Convert ERA5-Land 2 m air temperature from kelvin to Celsius for daily statistics.

## 4. Scientific background

ERA5-Land stores t2m in kelvin.

## 5. Mathematical formula or algorithm

T_C = T_K - 273.15 with KELVIN_OFFSET = 273.15. Daily mean/min/max use the 24 UTC hourly instants.

## 6. Explanation of every variable and unit

T_K: kelvin. T_C: degree Celsius. KELVIN_OFFSET dimensionless 273.15.

## 7. Worked numerical example

283.15 K → 10.00 °C.

## 8. Source datasets and provenance

ERA5-Land t2m.

## 9. Input requirements

Hourly t2m or precomputed t2m_c.

## 10. Processing steps

kelvin_to_celsius per hour; daily mean/min/max.

## 11. Implementation paths and functions

`kelvin_to_celsius`, `aggregate_daily_weather`.

Source files:
- `ml/preprocessing/weather.py`

## 12. Configuration parameters

variables includes 2m_temperature.

- `configs/weather_era5_land.yaml`

## 13. Outputs and units

temperature_mean_c, temperature_min_c, temperature_max_c (°C).

## 14. Validation criteria

Values >100 in t2m are treated as kelvin.

## 15. Missing-value handling

If hourly temperatures are missing, daily temperature is null, never 0.

## 16. Temporal leakage considerations

Daily UTC temperature on date D is not used in satellite features for date D; see historical windows.

## 17. Tests and expected assertions

test_unit_conversions; test_daily_temperature_and_wind_and_humidity.

- `tests/test_weather.py`

## 18. Scientific limitations

2 m air temperature is not canopy or soil temperature.

## 19. Related feature dependencies

- [`weather.relative_humidity`](relative_humidity.md)

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T07:34:24Z`
