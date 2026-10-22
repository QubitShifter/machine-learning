---
feature_id: weather.wetness_visualization
name: Rainfall-history and wetness-proxy charts
category: weather
status: implemented
mathematical_method: API_t=P_t+k API_{t-1}; trailing sums; consecutive dry days; P-E proxy
input_datasets:
- wetness_indicators.csv
- daily_weather.csv
source_code:
- ml/preprocessing/wetness.py
- backend/app/api/soil.py
- frontend/src/pages/WeatherAnalyticsPage.tsx
configuration:
- configs/weather_era5_land.yaml
outputs:
- GET /api/v1/soil/wetness/{weather_dataset_id}
- Weather Analytics wetness panels
tests:
- tests/test_soil.py
- frontend/src/app/App.test.tsx
documentation: docs/features/weather/wetness_visualization.md
last_verified: '2026-10-22T09:37:16Z'
related_bugs: []
---

## 1. Feature ID and name

`weather.wetness_visualization` — Rainfall-history and wetness-proxy charts.

## 2. Status and version

Status: `implemented`. Wetness version `3.4.0`.

## 3. Purpose

Display rainfall history and weather-derived wetness proxies next to existing temperature, precipitation, humidity, wind, and evaporation charts, without calling them soil moisture.

## 4. Scientific background

Antecedent precipitation index, rolling rainfall, dry-day runs, and precipitation-minus-evaporation are rainfall-history or water-flux proxies. They are not volumetric soil water and not a closed field water balance.

## 5. Mathematical formula or algorithm

`API_t = P_t + k API_{t-1}` for k in {0.85, 0.90, 0.95}. Missing P_t yields null API thereafter.

Trailing N-day sums require a complete window; any missing day yields null.

Consecutive dry days: run of P < 1 mm; missing P breaks the run.

`P−E` 7/30 d uses end-of-day trailing sums of precipitation and ERA5-Land evaporation.

## 6. Explanation of every variable and unit

Precipitation, API, rolling rainfall, evaporation, P−E: millimetres. Consecutive dry days: days. Temperature °C, RH %, wind m/s remain on existing weather cards.

## 7. Worked numerical example

P = [0, 2], k=0.90, API0=0 → API = [0, 2]. A later missing P makes subsequent API null.

## 8. Source datasets and provenance

Generated from the ERA5-Land daily weather table. Kind labels: `rainfall_history_indicator` and `weather_derived_wetness_proxy`.

## 9. Input requirements

`data/processed/wetness/<weather_dataset_id>/wetness_indicators.csv`.

## 10. Processing steps

Fetch up to 2000 wetness rows for the selected UTC range. Plot series with `connectNulls=false`. Label historical reanalysis versus forecasts (`is_forecast` if observation_kind contains forecast).

## 11. Implementation paths and functions

`get_wetness`, `WeatherAnalyticsPage` wetness section.

Source files:
- `ml/preprocessing/wetness.py`
- `frontend/src/pages/WeatherAnalyticsPage.tsx`

## 12. Configuration parameters

k factors 0.85/0.90/0.95; dry-day threshold 1 mm; windows 7/14/30. Satellite-aligned `precip_prev_N` still excludes date D.

- `configs/weather_era5_land.yaml`

## 13. Outputs and units

Charts: rolling 7 d rainfall (mm), API k=0.90 with k=0.85/0.95 in tooltips (mm), consecutive dry days, P−E 7 d (mm).

## 14. Validation criteria

Null precipitation is not drawn as 0. Copy states these are not volumetric soil moisture. Future forecasts are excluded from historical analytics.

## 15. Missing-value handling

Missing P or E yields null rolling/API/P−E values. Gaps stay gaps.

## 16. Temporal leakage considerations

End-of-day API includes P_t. Satellite integration windows remain D−N…D−1 exclusive of D and are not rewritten by these charts.

## 17. Tests and expected assertions

Wetness missing-data and no-future-window tests in `tests/test_soil.py`. Frontend asserts wetness copy is not soil moisture.

## 18. Scientific limitations

ERA5-Land evaporation is not crop ET. Irrigation, runoff, and drainage are absent, so P−E is not a closed water balance.

## 19. Related feature dependencies

- [`weather.antecedent_precipitation_index`](antecedent_precipitation_index.md)
- [`weather.drying_and_wetness_indicators`](drying_and_wetness_indicators.md)
- [`weather.precipitation_aggregation`](precipitation_aggregation.md)

## 20. Related bug/fix IDs

None newly confirmed.

## 21. Last reviewed timestamp in UTC

`2026-10-22T09:37:16Z`
