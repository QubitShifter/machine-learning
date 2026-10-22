---
feature_id: ui.soil_analysis_workspaces
name: Soil Analysis historical and detailed workspaces
category: ui
status: implemented
mathematical_method: none; layout and independent selection state only
input_datasets: []
source_code:
- frontend/src/pages/SoilAnalysisPage.tsx
- frontend/src/components/soil/YearOverYearSoilChart.tsx
- frontend/src/styles/index.css
configuration:
- frontend/src/styles/index.css
outputs:
- Historical Comparison workspace
- Detailed Soil Analysis workspace
- Explore this year navigation
tests:
- frontend/src/app/App.test.tsx
- frontend/src/components/soil/YearOverYearSoilChart.test.tsx
documentation: docs/features/ui/soil_analysis_workspaces.md
last_verified: '2026-10-22T16:38:11Z'
related_bugs: []
---

## 1. Feature ID and name

`ui.soil_analysis_workspaces` — Soil Analysis historical and detailed workspaces.

## 2. Status and version

Status: `implemented`. Display-only layout of existing Soil Analysis charts. Soil processing version remains `3.4.0`.

## 3. Purpose

Keep each Soil Analysis control next to the charts it affects. Historical year-over-year comparison is a separate workspace from detailed depth, time-series, and rainfall analysis.

## 4. Scientific background

ERA5-Land volumetric soil water is modeled reanalysis (m³/m³). Layout must not recompute monthly means, Δθ, seasonal DJF grouping, or rainfall–moisture alignment. Higher moisture is not treated as better crop health.

## 5. Mathematical formula or algorithm

No new formula. Desktop CSS:

- `.soil-comparison-stats` is one column below `1024px` and two columns at `1024px` and above.
- Detailed profile and time series use `xl:grid-cols-2`.
- Controls wrap with `.soil-control-bar` and `.soil-year-toggle-row`.

Page scroll is the only required scroll container. The seasonal table may overflow horizontally inside its panel.

## 6. Explanation of every variable and unit

- `comparisonDepth`, `enabledYears`, `monthIndex`, `yearA`, `yearB`: local state inside `YearOverYearSoilChart`.
- `detailYear`, `detailMonth`: URL `year` / `month` query parameters for the detailed workspace only.
- `detailAggregation`: `daily` or `monthly`.
- `detailSoilLayer`: selected TESSEL layer or weighted 0–100 cm profile for detailed charts.

Units remain m³/m³ for soil water and mm for precipitation.

## 7. Worked numerical example

January 2023 0–100 cm mean 0.3029981553682717 m³/m³ and January 2025 0.3734779265619093 m³/m³ still display Δθ = 0.0705 m³/m³ after the layout change. Unchecking comparison year 2024 does not change the detailed year selector.

## 8. Source datasets and provenance

No new datasets. Monthly rows still come from `GET /api/v1/soil/datasets/{id}/monthly`. Daily and combined rows still use the detailed year/month range.

## 9. Input requirements

The same processed monthly, daily, and combined soil–weather payloads used by the previous Soil Analysis page.

## 10. Processing steps

1. Render Historical Comparison first with the year-over-year chart, depth selector, year toggles, Δθ panel, and seasonal means.
2. Render Detailed Soil Analysis second with year, month, aggregation, and layer controls immediately above the depth profile, time series, rainfall chart, and compact provenance.
3. Share the monthly API result between workspaces without sharing selection state.
4. On explicit **Explore this year**, set the detailed year (and optional month from a chart point), then `scrollIntoView` on `#detailed-soil-analysis`. Hover does not navigate.

## 11. Implementation paths and functions

`SoilAnalysisPage.exploreYear`, `YearOverYearSoilChart` (`onExploreYear`, comparison-local state).

Source files:

- `frontend/src/pages/SoilAnalysisPage.tsx`
- `frontend/src/components/soil/YearOverYearSoilChart.tsx`
- `frontend/src/styles/index.css`

## 12. Configuration parameters

CSS classes in `frontend/src/styles/index.css`. Breakpoint `1024px` for comparison statistics. No soil YAML changes.

## 13. Outputs and units

DOM: `data-testid="soil-historical-workspace"`, `data-testid="soil-detailed-workspace"`, `data-testid="soil-detail-controls"`. Explore buttons `aria-label="Explore this year YYYY"`.

## 14. Validation criteria

Historical Comparison appears first. Detailed year/month/aggregation sit above detailed charts. Comparison year toggles do not change the detailed year. Explore this year updates the detailed year and leaves comparison toggles unchanged. Scientific values and missing-month gaps are unchanged.

## 15. Missing-value handling

Unchanged. Missing months stay null. Charts keep `connectNulls=false`. Incomplete seasons stay gaps.

## 16. Temporal leakage considerations

Layout does not join future months into past years. Explore this year only copies a selected year/month into the detailed URL; it does not fill missing months.

## 17. Tests and expected assertions

Workspace order; independent comparison vs detailed year; month change does not alter January Δθ; Explore this year sets detailed year; existing depth, layer, dual-axis, and YoY charts still render.

- `frontend/src/app/App.test.tsx`
- `frontend/src/components/soil/YearOverYearSoilChart.test.tsx`

jsdom tests are not proof of desktop/mobile clipping. Browser layout is recorded separately in the change history.

## 18. Scientific limitations

Workspace grouping does not add climatology, crop-health scoring, or in-situ moisture. Three complete years remain a short sample.

## 19. Related feature dependencies

- [`soil.year_over_year_moisture_comparison`](../soil/year_over_year_moisture_comparison.md)
- [`soil.moisture_profile_visualization`](../soil/moisture_profile_visualization.md)
- [`integration.rainfall_soil_chart`](../integration/rainfall_soil_chart.md)

## 20. Related bug/fix IDs

None. The previous control placement was inconvenient, not a scientific defect.

## 21. Last reviewed timestamp in UTC

`2026-10-22T16:38:11Z`
