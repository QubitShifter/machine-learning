---
feature_id: soil.era5_land_volumetric_moisture
name: ERA5-Land volumetric soil moisture
category: soil
status: implemented
mathematical_method: Daily mean of 24 hourly instantaneous states; missing hours yield null
input_datasets:
- CDS ERA5-Land volumetric_soil_water_layer_1..4
source_code:
- ml/preprocessing/soil.py
- ml/ingestion/soil_config.py
- ml/ingestion/soil_pipeline.py
- ml/validation/soil_quality.py
configuration:
- configs/soil_era5_land.yaml
outputs:
- daily_soil.csv
- quality_report.json
tests:
- tests/test_soil.py
- backend/tests/test_soil_api.py
documentation: docs/features/soil/era5_land_volumetric_moisture.md
last_verified: '2026-10-22T08:49:05Z'
related_bugs: []
---

## 1. Feature ID and name

`soil.era5_land_volumetric_moisture` — ERA5-Land volumetric soil moisture.

## 2. Status and version

Status: `implemented`. Soil processing version 3.4.0. Live 2023–2025 CDS retrieval is not required for this engineering phase and was not executed during implementation.

## 3. Purpose

Ingest modeled volumetric soil water for the Plovdiv study AOI as a historical state series, with provenance that it is not a field probe.

## 4. Scientific background

ERA5-Land `swvl1..4` are TESSEL/HTESSEL volumetric water content (m³/m³) on ~0.1° land points. They are instantaneous states, not accumulated precipitation. The nearest cell to the study AOI is the same ~4.85 km offset used by the weather dataset when the grid matches.

## 5. Mathematical formula or algorithm

For UTC day D, if all 24 hourly samples θ_{D,h} exist and are finite:

θ̄_D = (1/24) Σ_{h=0}^{23} θ_{D,h}

Also stored: daily min, max, 23:00 end-of-day, and θ_{23} − θ_{00}. Missing hours yield null daily statistics. Values are never zero-filled. Precipitation D+1 00:00 UTC deaccumulation is not applied.

## 6. Explanation of every variable and unit

- θ_{D,h}: volumetric soil water at hour h of day D (m³/m³).
- θ̄_D: daily mean (m³/m³).
- swvl1..4: layers 0–7, 7–28, 28–100, 100–289 cm.
- observation_kind: `modeled_volumetric_soil_moisture`.

## 7. Worked numerical example

24 hourly swvl1 values of 0.30 give θ̄_D = 0.30. Twenty-three valid hours and one missing hour give θ̄_D = null.

## 8. Source datasets and provenance

CDS product `reanalysis-era5-land`. Dataset ID `plovdiv_soil_2023_2025`. Official catalogue: https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land

## 9. Input requirements

Hourly NetCDF (or JSON fixtures). Required CDS names: `volumetric_soil_water_layer_1..4`. Optional soil temperature is configurable but not in the default config.

## 10. Processing steps

`check` → `download --dry-run` → opt-in `download --month YYYY-MM --resume` → `process` → `validate` → `report`. Downloads reuse empty-file and checksum safeguards. `include_next_day_boundary` is false.

## 11. Implementation paths and functions

- `ml/preprocessing/soil.py`: `aggregate_daily_soil`, `daily_mean_theta`
- `ml/ingestion/soil_pipeline.py`: `download_soil`, `process_soil_dataset`
- `ml/ingestion/era5_land.py`: `VARIABLE_ALIASES` swvl1..4

Source files:
- [`ml/preprocessing/soil.py`](../../../ml/preprocessing/soil.py)

## 12. Configuration parameters

[`configs/soil_era5_land.yaml`](../../../configs/soil_era5_land.yaml): dataset_id, AOI, retrieval_area, layers, quality.theta_min/max, field_capacity/wilting_point (null).

## 13. Outputs and units

`data/processed/soil/<dataset_id>/daily_soil.csv` (m³/m³), optional parquet if an engine exists (`parquet_generated` recorded), `quality_report.json`, `soil_chart_data.json`, optional PNG.

## 14. Validation criteria

Unique timestamps, 24-hour completeness, nonnegative θ, θ ≤ 1 flagged not clamped, required layers present, spatial cell compared with weather.

## 15. Missing-value handling

Missing hours stay missing. Daily mean is null unless 24 valid hours exist. Missing is never stored as 0.

## 16. Temporal leakage considerations

Historical reanalysis for day D uses hours on day D only. It is not an operational forecast issued before D.

## 17. Tests and expected assertions

[`tests/test_soil.py`](../../../tests/test_soil.py): dry-run has no boundary request; incomplete days are not complete; negative θ kept and reviewed; `is_ground_truth` false.

## 18. Scientific limitations

Not 10 m or field-scale. Not independent ground truth. Correlation with ERA5 precipitation is not validation.

## 19. Related feature dependencies

- [`soil.root_zone_profile_mean`](root_zone_profile_mean.md)
- [`weather.era5_land_ingestion`](../weather/era5_land_ingestion.md)
- [`soil.soil_moisture`](soil_moisture.md)

## 20. Related bug/fix IDs

None newly confirmed for this feature. Empty-file download safety is inherited from [BUG-0001](../../bugs/BUG-0001.md).

## 21. Last reviewed timestamp in UTC

`2026-10-22T08:49:05Z`
