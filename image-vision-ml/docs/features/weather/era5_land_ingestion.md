---
feature_id: weather.era5_land_ingestion
name: ERA5-Land weather ingestion
category: weather
status: implemented
mathematical_method: "Monthly CDS retrieval + next-day 00:00 UTC boundary; nearest\
  \ native 0.1\xB0 cell to AOI centroid"
input_datasets:
- CDS reanalysis-era5-land
source_code:
- ml/ingestion/weather_download.py
- ml/ingestion/era5_land.py
- ml/ingestion/weather_pipeline.py
configuration:
- configs/weather_era5_land.yaml
outputs:
- data/raw/weather/*/hourly/*.nc
- manifest.json
tests:
- tests/test_weather_download.py
- tests/test_weather.py
documentation: docs/features/weather/era5_land_ingestion.md
last_verified: '2026-10-22T07:34:24Z'
related_bugs:
- BUG-0001
- BUG-0002
- BUG-0003
- BUG-0008
---

## 1. Feature ID and name

`weather.era5_land_ingestion` — ERA5-Land weather ingestion.

## 2. Status and version

Status: `implemented`. Satellite processing version 1.1.0 and integration version 3.2.0 apply where those modules are used. Pixel-exclusion accounting version is 1.0.0.

## 3. Purpose

Download and store ERA5-Land hourly fields for the Plovdiv study without contacting CDS unless explicitly requested.

## 4. Scientific background

ERA5-Land is ~0.1°. The 0.03° study AOI cannot be used as a CDS crop.

## 5. Mathematical formula or algorithm

CDS area = [42.20, 24.50, 41.90, 24.90] (N,W,S,E). Nearest cell by haversine to AOI centroid.

## 6. Explanation of every variable and unit

Study AOI bbox W/S/E/N. Retrieval box N/W/S/E degrees. Native resolution 0.1°.

## 7. Worked numerical example

AOI centroid ≈ (24.665, 42.065) maps to the stored source_grid_id of the nearest cell.

## 8. Source datasets and provenance

Copernicus CDS ERA5-Land. Empty files are incomplete, not successful downloads.

## 9. Input requirements

CDS credentials locally; monthly request plus next-day 00:00 boundary.

## 10. Processing steps

plan → retrieve to *.download → detect GRIB/NetCDF → commit (empty destinations may be replaced; non-empty never overwritten).

## 11. Implementation paths and functions

`download_weather_month`, `month_integrity`, `_commit_downloaded_file`.

Source files:
- `ml/ingestion/weather_download.py`
- `ml/ingestion/era5_land.py`
- `ml/ingestion/weather_pipeline.py`

## 12. Configuration parameters

configs/weather_era5_land.yaml period, variables, retrieval_area.

- `configs/weather_era5_land.yaml`

## 13. Outputs and units

NetCDF/JSON hourly files; checksums in the weather manifest.

## 14. Validation criteria

empty_hourly_file / empty_boundary_file ⇒ incomplete. Checksum mismatch ⇒ requires_review, not overwrite.

## 15. Missing-value handling

Missing months stay pending/failed. Values are not zero-filled.

## 16. Temporal leakage considerations

Ingestion stores reanalysis, not forecasts of future dates beyond the requested month.

## 17. Tests and expected assertions

Dry-run does not retrieve; empty files replaceable; complete files refused.

- `tests/test_weather_download.py`
- `tests/test_weather.py`

## 18. Scientific limitations

Reanalysis is model-assimilated, not a station observation. One cell represents ~10 km, not 10 m fields.

## 19. Related feature dependencies

- [`weather.precipitation_aggregation`](precipitation_aggregation.md)

## 20. Related bug/fix IDs

[`BUG-0001`](../../bugs/BUG-0001.md), [`BUG-0002`](../../bugs/BUG-0002.md), [`BUG-0003`](../../bugs/BUG-0003.md), [`BUG-0008`](../../bugs/BUG-0008.md)

## 21. Last reviewed timestamp in UTC

`2026-10-22T07:34:24Z`
