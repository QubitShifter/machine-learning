---
feature_id: weather.relative_humidity
name: Relative humidity
category: weather
status: implemented
mathematical_method: Magnus-Tetens RH = 100 * e(Td) / e_sat(T)
input_datasets:
- ERA5-Land 2m_temperature
- 2m_dewpoint_temperature
source_code:
- ml/preprocessing/weather.py
configuration:
- configs/weather_era5_land.yaml
outputs:
- relative_humidity_mean_pct
tests:
- tests/test_weather.py
documentation: docs/features/weather/relative_humidity.md
last_verified: '2026-10-22T07:34:24Z'
related_bugs: []
---

## 1. Feature ID and name

`weather.relative_humidity` — Relative humidity.

## 2. Status and version

Status: `implemented`. Satellite processing version 1.1.0 and integration version 3.2.0 apply where those modules are used. Pixel-exclusion accounting version is 1.0.0.

## 3. Purpose

Estimate relative humidity from air and dew-point temperature using the project's Magnus coefficients.

## 4. Scientific background

Alduchov and Eskridge (1996) Magnus-Tetens approximation, valid near meteorological surface temperatures.

## 5. Mathematical formula or algorithm

e(T) = 6.1094 * exp((17.625 * T) / (243.04 + T)) with T in °C and e in hPa. RH = 100 * e(Td) / e_sat(T). Clamp only within ±0.05 of [0,100].

## 6. Explanation of every variable and unit

MAGNUS_A=17.625, MAGNUS_B=243.04, MAGNUS_C=6.1094 hPa. T, Td in °C. RH in percent. ROUNDING_RH=0.05.

## 7. Worked numerical example

T=20 °C, Td=20 °C → RH=100%. Large impossibilities are kept, not clamped.

## 8. Source datasets and provenance

Derived from ERA5-Land t2m and d2m; not an ERA5 native RH field.

## 9. Input requirements

Hourly T_C and Td_C.

## 10. Processing steps

saturation_vapor_pressure_hpa twice; ratio; limited clamp.

## 11. Implementation paths and functions

`saturation_vapor_pressure_hpa`, `relative_humidity_pct`.

Source files:
- `ml/preprocessing/weather.py`

## 12. Configuration parameters

Both temperature and dewpoint must be requested.

- `configs/weather_era5_land.yaml`

## 13. Outputs and units

relative_humidity_mean_pct (percent).

## 14. Validation criteria

test_relative_humidity_keeps_large_impossibilities.

## 15. Missing-value handling

If T or Td missing, RH is null.

## 16. Temporal leakage considerations

Same UTC-day exclusion as other weather features when paired with satellite D.

## 17. Tests and expected assertions

Unit and daily aggregation tests in tests/test_weather.py.

- `tests/test_weather.py`

## 18. Scientific limitations

Magnus is an approximation; ice vs water saturation is not switched. Not a station hygrometer.

## 19. Related feature dependencies

- [`weather.temperature_conversion`](temperature_conversion.md)

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T07:34:24Z`
