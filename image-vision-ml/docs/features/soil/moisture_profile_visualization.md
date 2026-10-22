---
feature_id: soil.moisture_profile_visualization
name: Modeled soil-moisture depth profile and time series
category: soil
status: implemented
mathematical_method: layer bars in m3 m-3; daily means; monthly mean of complete days; 0.07θ1+0.21θ2+0.72θ3
input_datasets:
- daily_soil.csv
- monthly_summary.csv
source_code:
- backend/app/api/soil.py
- backend/app/services/soil_service.py
- frontend/src/pages/SoilAnalysisPage.tsx
configuration:
- configs/soil_era5_land.yaml
outputs:
- GET /api/v1/soil/datasets/{id}/daily
- GET /api/v1/soil/datasets/{id}/monthly
- Soil Analysis page
tests:
- tests/test_soil.py
- backend/tests/test_soil_api.py
- frontend/src/app/App.test.tsx
documentation: docs/features/soil/moisture_profile_visualization.md
last_verified: '2026-10-22T16:38:11Z'
related_bugs: []
---

## 1. Feature ID and name

`soil.moisture_profile_visualization` — Modeled soil-moisture depth profile and time series.

## 2. Status and version

Status: `implemented`. Soil processing version `3.4.0`.

## 3. Purpose

Inspect ERA5-Land volumetric soil water by depth and date without presenting it as in-situ moisture or 10 m satellite precision.

## 4. Scientific background

ERA5-Land TESSEL layers: 0–7, 7–28, 28–100, 100–289 cm. Values are modeled volumetric fractions (m³/m³). Instantaneous states, not accumulated fluxes.

## 5. Mathematical formula or algorithm

Daily layer value = mean of 24 hourly states when the day is complete.

Monthly value = mean of complete days in that month, labelled as a monthly average.

Root-zone 0–100 cm: `θ = 0.07 θ1 + 0.21 θ2 + 0.72 θ3`. Layer 4 is excluded.

Time-series gaps remain null (`connectNulls=false`).

## 6. Explanation of every variable and unit

- `swvl1_mean` … `swvl4_mean`: layer volumetric water, m³/m³.
- `theta_root_zone_0_100`: thickness-weighted 0–100 cm mean, m³/m³.
- Complete day: 24 hourly records present.

## 7. Worked numerical example

θ1=0.30, θ2=0.28, θ3=0.25 → 0.07×0.30 + 0.21×0.28 + 0.72×0.25 = 0.2599 m³/m³.

## 8. Source datasets and provenance

`plovdiv_soil_2023_2025` from Copernicus ERA5-Land. Grid cell and distance from AOI center come from processed spatial metadata. Observation kind is always modeled/reanalysis.

## 9. Input requirements

Processed `daily_soil.csv`. Monthly summary preferred when present; otherwise recomputed from complete days.

## 10. Processing steps

In the Detailed Soil Analysis workspace, select year, month or full year, and daily/monthly aggregation; load daily or monthly rows; draw depth bars for the selected stamp; draw the layer time series. Year/month URL state does not control the Historical Comparison workspace.

## 11. Implementation paths and functions

`get_daily`, `get_monthly`, `SoilAnalysisPage`.

Source files:
- `backend/app/api/soil.py`
- `frontend/src/pages/SoilAnalysisPage.tsx`

## 12. Configuration parameters

[`configs/soil_era5_land.yaml`](../../../configs/soil_era5_land.yaml) layer depths and AOI.

## 13. Outputs and units

Depth bar chart (m³/m³); daily/monthly time series (m³/m³); provenance footer (source, dataset, grid, quality). Year, month, aggregation, and layer selectors sit immediately above these charts.

## 14. Validation criteria

`is_ground_truth` false. Monthly aggregation labelled `monthly_mean_of_complete_days`. Missing days are not drawn as 0.

## 15. Missing-value handling

Incomplete days stay in the table with null layer values. Charts do not interpolate across gaps.

## 16. Temporal leakage considerations

Historical reanalysis for date D uses hours on D only. Future forecasts are not mixed into this soil archive.

## 17. Tests and expected assertions

API monthly aggregation; detailed year/month/layer selectors; daily/monthly tab; units m³/m³; modeled reanalysis copy; Historical Comparison remains first on the page.

- `backend/tests/test_soil_api.py`
- `frontend/src/app/App.test.tsx`

## 18. Scientific limitations

One ERA5-Land cell (~0.1°, several km from the Plovdiv AOI centre) cannot imply 10 m precision. Current live archive may be a single month. Not crop-available water.

## 19. Related feature dependencies

- [`soil.era5_land_volumetric_moisture`](era5_land_volumetric_moisture.md)
- [`soil.root_zone_profile_mean`](root_zone_profile_mean.md)
- [`integration.rainfall_soil_chart`](../integration/rainfall_soil_chart.md)
- [`soil.year_over_year_moisture_comparison`](year_over_year_moisture_comparison.md)
- [`ui.soil_analysis_workspaces`](../ui/soil_analysis_workspaces.md)

## 20. Related bug/fix IDs

None newly confirmed.

## 21. Last reviewed timestamp in UTC

`2026-10-22T16:38:11Z`
