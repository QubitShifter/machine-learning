---
feature_id: soil.year_over_year_moisture_comparison
name: Historical soil-moisture year-over-year comparison
category: soil
status: implemented
mathematical_method: monthly mean of complete days plotted by calendar month; Δθ=θ_B-θ_A; DJF winter spans Dec Y–Feb Y+1
input_datasets:
- monthly_summary.csv
source_code:
- frontend/src/utils/soilYearComparison.ts
- frontend/src/components/soil/YearOverYearSoilChart.tsx
- frontend/src/pages/SoilAnalysisPage.tsx
- backend/app/api/soil.py
- backend/app/services/soil_service.py
configuration:
- configs/soil_era5_land.yaml
outputs:
- Soil Analysis year-over-year chart
- interannual Δθ panel
- seasonal DJF/MAM/JJA/SON means
tests:
- frontend/src/utils/soilYearComparison.test.ts
- frontend/src/components/soil/YearOverYearSoilChart.test.tsx
- frontend/src/app/App.test.tsx
documentation: docs/features/soil/year_over_year_moisture_comparison.md
last_verified: '2026-10-22T16:38:11Z'
related_bugs: []
---

## 1. Feature ID and name

`soil.year_over_year_moisture_comparison` — Historical soil-moisture year-over-year comparison.

## 2. Status and version

Status: `implemented`. Uses existing monthly aggregation `monthly_mean_of_complete_days` from soil processing version `3.4.0`. No new processing version.

## 3. Purpose

Compare modeled ERA5-Land volumetric soil water for the same calendar months across years in the Historical Comparison workspace on the Soil Analysis page, with selectable depth and year visibility independent of the detailed year/month controls.

## 4. Scientific background

ERA5-Land TESSEL stores instantaneous volumetric soil water (m³/m³) in four layers. Monthly points are means of complete UTC days, not a single-day state and not in-situ field moisture. Three complete years are a short sample, not a climatology.

## 5. Mathematical formula or algorithm

Monthly mean (already computed in `monthly_summary.csv`):

θ_month = mean(θ_day) over complete days in that UTC month.

Year-over-year chart: for month m ∈ {1…12} and year Y, plot θ_{Y-m} or a gap if the month is missing or incomplete.

Interannual difference:

Δθ = θ_yearB − θ_yearA

Relative change, only if |θ_yearA| ≥ 10⁻⁶:

100 × Δθ / θ_yearA

Otherwise relative change is undefined.

Weighted 0–100 cm profile (already in the monthly file):

θ_{0-100} = 0.07 θ1 + 0.21 θ2 + 0.72 θ3

Seasonal mean requires every month in the season to be `availability=complete`. Winter DJF for start year Y is December Y, January Y+1, February Y+1. Spring/summer/autumn stay inside calendar year Y.

## 6. Explanation of every variable and unit

- θ, swvl1–4, θ_{0-100}: volumetric soil water, m³/m³.
- complete_days: count of UTC days with 24 hourly layer states.
- Δθ: year B minus year A, m³/m³.
- Daily min/max in a month: extrema of daily θ_{0-100} inside that month; not a confidence interval.

## 7. Worked numerical example

From `data/processed/soil/plovdiv_soil_2023_2025/monthly_summary.csv`:

θ_2023-01 (0–100 cm) = 0.3029981553682717 m³/m³ (31 complete days).

θ_2025-01 (0–100 cm) = 0.3734779265619093 m³/m³ (31 complete days).

Δθ = 0.0704797711936376 m³/m³.

Displayed to four decimals as 0.0705 m³/m³. February 2024 has 29 complete days (leap year); February 2023 has 28.

## 8. Source datasets and provenance

`plovdiv_soil_2023_2025` monthly summary via `GET /api/v1/soil/datasets/{id}/monthly`. Source grid 42.1° N, 24.7° E, 4.85 km from the Plovdiv AOI center. Observation kind `modeled_volumetric_soil_moisture`. `is_ground_truth=false`.

## 9. Input requirements

Processed `monthly_summary.csv` with `month`, layer means, `theta_root_zone_0_100_mean`, optional min/max, `complete_days`, and `availability`. Years are derived from those rows, not hardcoded.

## 10. Processing steps

1. Fetch monthly records from the existing API (shared with detailed analysis; selection state is not shared).
2. Derive available years and complete years (12 months with `availability=complete`).
3. Build a 12-row January–December table keyed by year; missing months stay null.
4. Draw one line per enabled year at the selected comparison depth.
5. Compute Δθ from the same monthly means.
6. Compute seasonal means only when every required month is complete.
7. Optional **Explore this year** copies the chosen year (and optional month from a chart click) into detailed-analysis URL state and scrolls to that workspace. Hover does not navigate.

## 11. Implementation paths and functions

`yearsFromMonthly`, `buildYearOverYearRows`, `interannualDelta`, `seasonalMean`, `YearOverYearSoilChart`, `SoilAnalysisPage`.

Source files:

- `frontend/src/utils/soilYearComparison.ts`
- `frontend/src/components/soil/YearOverYearSoilChart.tsx`
- `frontend/src/pages/SoilAnalysisPage.tsx`
- `backend/app/api/soil.py`
- `backend/app/services/soil_service.py`

## 12. Configuration parameters

Layer depths in [`configs/soil_era5_land.yaml`](../../../configs/soil_era5_land.yaml). Relative-change floor `1e-6`. No new YAML keys.

## 13. Outputs and units

Chart: January–December vs m³/m³. Tooltip: year, month, depth, monthly mean, units, complete days, completeness, ERA5-Land, modeled reanalysis, optional daily min/max. Δθ panel in m³/m³. Seasonal table in m³/m³.

## 14. Validation criteria

Default depth is weighted 0–100 cm. Default years are complete years. Missing months are gaps, never 0. Leap-year February retains 29 complete days. Comparison year toggles do not change the detailed year. Existing daily/monthly soil charts remain in the Detailed Soil Analysis workspace. Datasets are not overwritten.

## 15. Missing-value handling

Absent or non-complete months are JSON/UI null. Charts convert null to Recharts `undefined` with `connectNulls=false`. Incomplete seasons are null, not a partial-season average.

## 16. Temporal leakage considerations

Each monthly point uses only complete days inside that UTC month. Year B is not used to fill year A. Forecasts are not mixed into this archive.

## 17. Tests and expected assertions

Grouping Jan–Dec; leap-year February; depth selection; year toggling; missing-month null; exact January 2025−2023 Δθ; tooltip strings; provenance; Explore this year without changing comparison toggles; Historical Comparison appears first; existing Soil Analysis charts still render.

- `frontend/src/utils/soilYearComparison.test.ts`
- `frontend/src/components/soil/YearOverYearSoilChart.test.tsx`
- `frontend/src/app/App.test.tsx`
- `backend/tests/test_soil_api.py` (monthly endpoint unchanged)

## 18. Scientific limitations

One ERA5-Land ~0.1° cell is not a field measurement. Higher θ is not crop-health. Three years are not climatology. Layer 4 is not in the 0–100 cm profile. Daily min/max are not uncertainty bands. Frontend does not recompute monthly means from displayed rounded values.

## 19. Related feature dependencies

- [`soil.era5_land_volumetric_moisture`](era5_land_volumetric_moisture.md)
- [`soil.root_zone_profile_mean`](root_zone_profile_mean.md)
- [`soil.moisture_profile_visualization`](moisture_profile_visualization.md)
- [`ui.soil_analysis_workspaces`](../ui/soil_analysis_workspaces.md)

## 20. Related bug/fix IDs

None. The chart is a new capability, not a defect in the previous single-year soil charts.

## 21. Last reviewed timestamp in UTC

`2026-10-22T16:38:11Z`
