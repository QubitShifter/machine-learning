---
feature_id: weather.evaporation
name: Evaporation
category: weather
status: implemented
mathematical_method: E_up_mm = -1000 * e_accum_m  (ECMWF positive-downward)
input_datasets:
- ERA5-Land total_evaporation
source_code:
- ml/preprocessing/weather.py
configuration:
- configs/weather_era5_land.yaml
outputs:
- evaporation_total_mm
- evaporation_method
tests:
- tests/test_weather.py
documentation: docs/features/weather/evaporation.md
last_verified: '2026-10-22T07:34:24Z'
related_bugs: []
---

## 1. Feature ID and name

`weather.evaporation` — Evaporation.

## 2. Status and version

Status: `implemented`. Satellite processing version 1.1.0 and integration version 3.2.0 apply where those modules are used. Pixel-exclusion accounting version is 1.0.0.

## 3. Purpose

Convert ERA5-Land accumulated evaporation to upward millimetres using the same daily-boundary convention as precipitation.

## 4. Scientific background

ECMWF accumulated fluxes are positive downward, so surface evaporation is typically negative in the raw field.

## 5. Mathematical formula or algorithm

EVAPORATION_SIGN = -1. convert_evaporation_mm(e) = -1000 * e. Daily total uses next-day 00:00 UTC when present.

## 6. Explanation of every variable and unit

e: metres, ECMWF sign. evaporation_total_mm: millimetres, positive upward (water leaving the surface).

## 7. Worked numerical example

Raw e = -0.002 m at D+1 00:00 → +2.0 mm upward evaporation for day D.

## 8. Source datasets and provenance

ERA5-Land total_evaporation.

## 9. Input requirements

Hourly e plus next-day 00:00 boundary.

## 10. Processing steps

Same _daily_flux path as precipitation with convert_evaporation_mm.

## 11. Implementation paths and functions

`convert_evaporation_mm`.

Source files:
- `ml/preprocessing/weather.py`

## 12. Configuration parameters

variables includes total_evaporation.

- `configs/weather_era5_land.yaml`

## 13. Outputs and units

evaporation_total_mm (mm, upward).

## 14. Validation criteria

Uses the same complete-day rule as precipitation.

## 15. Missing-value handling

Null if boundary missing; not zero-filled.

## 16. Temporal leakage considerations

Same UTC window rules as precipitation when aggregated to satellite features.

## 17. Tests and expected assertions

Daily aggregation tests include evaporation_total_mm.

- `tests/test_weather.py`

## 18. Scientific limitations

Potential/actual evapotranspiration for crops is not computed. Sign convention must not be applied twice.

## 19. Related feature dependencies

- [`weather.precipitation_aggregation`](precipitation_aggregation.md)

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T07:34:24Z`
