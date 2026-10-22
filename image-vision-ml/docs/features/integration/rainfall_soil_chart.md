---
feature_id: integration.rainfall_soil_chart
name: Combined rainfall and modeled soil-water chart
category: integration
status: implemented
mathematical_method: outer join on UTC date; dual axis mm vs m3 m-3; no interpolation
input_datasets:
- daily_soil.csv
- daily_weather.csv
- wetness_indicators.csv
source_code:
- ml/analysis/soil_weather.py
- backend/app/api/soil.py
- frontend/src/components/charts/DualAxisChart.tsx
- frontend/src/pages/SoilAnalysisPage.tsx
configuration:
- configs/soil_era5_land.yaml
- configs/weather_era5_land.yaml
outputs:
- GET /api/v1/soil/combined/{soil_id}/{weather_id}
tests:
- tests/test_soil.py
- backend/tests/test_soil_api.py
- frontend/src/app/App.test.tsx
documentation: docs/features/integration/rainfall_soil_chart.md
last_verified: '2026-10-22T16:38:11Z'
related_bugs: []
---

## 1. Feature ID and name

`integration.rainfall_soil_chart` — Combined rainfall and modeled soil-water chart.

## 2. Status and version

Status: `implemented`. Integration of Phase 3.4 soil and weather tables. Lagged correlation remains `prepared_not_interpreted`.

## 3. Purpose

Plot daily precipitation as bars and a selected modeled soil-water layer as a line on correctly labelled separate axes, with API on a separate panel.

## 4. Scientific background

Precipitation is a flux (mm). Volumetric soil water is a state (m³/m³). Plotting them on one unlabelled axis would mix units. ERA5-Land soil and ERA5-Land weather share modelling ancestry, so co-variation is not independent validation.

## 5. Mathematical formula or algorithm

Outer join on `date_utc`. Missing soil or weather fields stay null. Forecast rows (`observation_kind` contains `forecast`) drop precipitation from historical analytics. Dual-axis composed chart: bar = P (mm), line = selected θ (m³/m³). API is a separate millimetre panel.

Lagged Pearson utilities exist in `exploratory_soil_weather_report` but are not displayed as scientific conclusions.

## 6. Explanation of every variable and unit

- `precipitation_total_mm`: mm.
- `swvl*_mean`, `theta_root_zone_0_100`: m³/m³.
- `api_k090_mm`: mm, weather-derived wetness proxy.
- `soil_present` / `weather_present`: whether that date had a source row.

## 7. Worked numerical example

Soil on 2023-01-01 and 2023-01-03, weather on 2023-01-01 and 2023-01-02 with null P: aligned dates are 01, 02, 03; 02 has null θ; 03 has null P; neither is filled.

## 8. Source datasets and provenance

Soil dataset ID, weather dataset ID, ERA5-Land grid cell, modeled observation kind. Tooltip includes presence flags and grid id.

## 9. Input requirements

Soil daily table required. Weather and wetness CSVs optional; missing sources yield null fields, not zeros.

## 10. Processing steps

`align_soil_weather_wetness`; page the combined API using the detailed year/month range; frontend DualAxisChart with `connectNulls=false` on the line, placed in the Detailed Soil Analysis workspace below the year/month controls.

## 11. Implementation paths and functions

`align_soil_weather_wetness`, `get_combined`, `DualAxisChart`.

Source files:
- `ml/analysis/soil_weather.py`
- `backend/app/api/soil.py`
- `frontend/src/components/charts/DualAxisChart.tsx`

## 12. Configuration parameters

Date range query `start_date`/`end_date`. Limit ≤ 2000. Layer selection is a frontend control over existing columns.

- `configs/soil_era5_land.yaml`
- `configs/weather_era5_land.yaml`

## 13. Outputs and units

JSON records with separate soil and precipitation units. Chart: left axis mm, right axis m³/m³. `lagged_correlation_status=prepared_not_interpreted`.

## 14. Validation criteria

Mixed units are not on one axis. Missing P is not 0. `is_ground_truth` false. Gaps remain.

## 15. Missing-value handling

Outer join. Nulls stay null. Long missing intervals are not bridged.

## 16. Temporal leakage considerations

No future precipitation is copied onto earlier soil dates. Forecast observation kinds are excluded from historical bars.

## 17. Tests and expected assertions

Alignment test expects three dates with nulls preserved. Frontend dual-axis chart renders with modeled-reanalysis copy.

- `tests/test_soil.py`
- `backend/tests/test_soil_api.py`
- `frontend/src/app/App.test.tsx`

## 18. Scientific limitations

One month of overlap cannot support lagged-correlation claims. Shared ERA5-Land ancestry means correlation is exploratory only. Spatial support is the coarse ERA5-Land cell, not 10 m.

## 19. Related feature dependencies

- [`soil.moisture_profile_visualization`](../soil/moisture_profile_visualization.md)
- [`ui.soil_analysis_workspaces`](../ui/soil_analysis_workspaces.md)
- [`weather.wetness_visualization`](../weather/wetness_visualization.md)
- [`soil.era5_land_volumetric_moisture`](../soil/era5_land_volumetric_moisture.md)

## 20. Related bug/fix IDs

None newly confirmed.

## 21. Last reviewed timestamp in UTC

`2026-10-22T16:38:11Z`
