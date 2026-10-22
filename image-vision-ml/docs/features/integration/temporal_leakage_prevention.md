---
feature_id: integration.temporal_leakage_prevention
name: Temporal leakage prevention
category: integration
status: implemented
mathematical_method: "Windows are D\u2212N \u2026 D\u22121; SAME_DAY_POLICY=excluded"
input_datasets:
- Satellite acquisition timestamps
- daily weather
source_code:
- ml/integration/satellite_weather.py
- ml/integration/validate.py
- ml/integration/features.py
configuration:
- configs/weather_era5_land.yaml
outputs:
- window_Nd_start_utc
- window_Nd_end_utc
- quality_warnings
tests:
- tests/test_integration_integrity.py
- tests/test_satellite_weather.py
documentation: docs/features/integration/temporal_leakage_prevention.md
last_verified: '2026-10-22T07:34:24Z'
related_bugs: []
---

## 1. Feature ID and name

`integration.temporal_leakage_prevention` — Temporal leakage prevention.

## 2. Status and version

Status: `implemented`. Satellite processing version 1.1.0 and integration version 3.2.0 apply where those modules are used. Pixel-exclusion accounting version is 1.0.0.

## 3. Purpose

Guarantee that weather features paired with a Sentinel-2 scene never include the acquisition day or later days.

## 4. Scientific background

Same-day rain or post-overpass weather would not be available for an operational forecast issued at overpass time.

## 5. Mathematical formula or algorithm

LEAKAGE_POLICY=previous_completed_utc_days_only. WINDOW_RULE as documented in integration/features.py.

## 6. Explanation of every variable and unit

D UTC calendar date; N window length.

## 7. Worked numerical example

If window_7d_end_utc == D, validation emits incorrect_window_end / leakage issue.

## 8. Source datasets and provenance

Implementation and validation, not a separate dataset.

## 9. Input requirements

Observation date and daily weather index.

## 10. Processing steps

Build prior dates; compare stored start/end; recompute sums; fail if D included.

## 11. Implementation paths and functions

`prior_window_dates`, `_validate_windows`.

Source files:
- `ml/integration/satellite_weather.py`
- `ml/integration/validate.py`
- `ml/integration/features.py`

## 12. Configuration parameters

windows_days.

- `configs/weather_era5_land.yaml`

## 13. Outputs and units

ISO date bounds; boolean completeness; null aggregates if leak/incomplete.

## 14. Validation criteria

Dedicated integrity tests.

## 15. Missing-value handling

Incomplete windows null the aggregate rather than shortening the window.

## 16. Temporal leakage considerations

This feature is the leakage control.

## 17. Tests and expected assertions

Windows do not include acquisition date; future rain is not zero-filled.

- `tests/test_integration_integrity.py`
- `tests/test_satellite_weather.py`

## 18. Scientific limitations

UTC calendar days, not local solar time and not hour-of-overpass truncation.

## 19. Related feature dependencies

- [`weather.historical_rolling_features`](../weather/historical_rolling_features.md)

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T07:34:24Z`
