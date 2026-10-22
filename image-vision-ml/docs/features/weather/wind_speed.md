---
feature_id: weather.wind_speed
name: Wind speed
category: weather
status: implemented
mathematical_method: "wind_speed = sqrt(u10\xB2 + v10\xB2)"
input_datasets:
- ERA5-Land 10m_u_component_of_wind
- 10m_v_component_of_wind
source_code:
- ml/preprocessing/weather.py
configuration:
- configs/weather_era5_land.yaml
outputs:
- wind_speed_mean_ms
tests:
- tests/test_weather.py
documentation: docs/features/weather/wind_speed.md
last_verified: '2026-10-22T07:34:24Z'
related_bugs: []
---

## 1. Feature ID and name

`weather.wind_speed` — Wind speed.

## 2. Status and version

Status: `implemented`. Satellite processing version 1.1.0 and integration version 3.2.0 apply where those modules are used. Pixel-exclusion accounting version is 1.0.0.

## 3. Purpose

Compute 10 m wind speed magnitude from ERA5-Land vector components.

## 4. Scientific background

ERA5-Land stores u10 and v10, not speed.

## 5. Mathematical formula or algorithm

wind_speed = sqrt(u10^2 + v10^2).

## 6. Explanation of every variable and unit

u10, v10, wind_speed: metres per second.

## 7. Worked numerical example

u=0, v=1 → 1 m/s. u=3, v=4 → 5 m/s.

## 8. Source datasets and provenance

ERA5-Land 10 m wind components.

## 9. Input requirements

Hourly u10, v10.

## 10. Processing steps

wind_speed per hour; daily mean of hourly speeds.

## 11. Implementation paths and functions

`wind_speed`.

Source files:
- `ml/preprocessing/weather.py`

## 12. Configuration parameters

Both u and v components required.

- `configs/weather_era5_land.yaml`

## 13. Outputs and units

wind_speed_mean_ms (m/s).

## 14. Validation criteria

Daily aggregation tests.

## 15. Missing-value handling

Missing components ⇒ null speed, not 0.

## 16. Temporal leakage considerations

UTC daily mean; excluded from satellite-day D windows.

## 17. Tests and expected assertions

test_unit_conversions; test_daily_temperature_and_wind_and_humidity.

- `tests/test_weather.py`

## 18. Scientific limitations

10 m wind is not in-canopy or 2 m wind. Daily mean of speeds is not the speed of the mean vector.

## 19. Related feature dependencies

None.

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T07:34:24Z`
