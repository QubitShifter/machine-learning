---
feature_id: sources.agricultural_data_registry
name: Agricultural data-source registry
category: sources
status: implemented
mathematical_method: Catalogue only; no automatic multi-source download
input_datasets:
- docs/data_sources/registry.yaml
source_code:
- ml/sources/registry.py
- ml/ingestion/soilgrids.py
configuration:
- docs/data_sources/registry.yaml
outputs:
- registry records with integration_status
tests:
- tests/test_soil.py
documentation: docs/features/sources/agricultural_data_registry.md
last_verified: '2026-10-22T08:49:05Z'
related_bugs:
- BUG-0010
---

## 1. Feature ID and name

`sources.agricultural_data_registry` — Agricultural data-source registry.

## 2. Status and version

Status: `implemented` as a catalogue. Individual sources may be operational, implemented, planned, or paused.

## 3. Purpose

Record scientific providers, access routes, licences, and whether they are actually ingested.

## 4. Scientific background

Mixing planned URLs with operational archives causes false readiness. ERA5-Land weather is operational. ERA5-Land soil-water code is implemented without a live 36-month download in this phase. SoilGrids REST is paused.

## 5. Mathematical formula or algorithm

No equation. Each record stores source_id, provider, product, version, category, variables, units, spatial/temporal resolution, coverage, update frequency, access, authentication, licence, limitations, uncertainty, tasks, integration_status, official URL, verification_date.

## 6. Explanation of every variable and unit

`integration_status`: `operational`, `implemented`, `planned`, `paused`. `live_download_executed` is explicit for soil water (false in this phase).

## 7. Worked numerical example

n/a — catalogue lookup. `python -m scripts.soil_dataset sources` prints JSON counts.

## 8. Source datasets and provenance

[`docs/data_sources/registry.yaml`](../../data_sources/registry.yaml). Official URLs were recorded on 2026-10-22.

## 9. Input requirements

YAML registry file. Network is not required to load it.

## 10. Processing steps

`load_source_registry()`. SoilGrids adapter returns `not_available` without fabricating properties.

## 11. Implementation paths and functions

- `ml/sources/registry.py`: `load_source_registry`, `get_source`
- `ml/ingestion/soilgrids.py`: `soilgrids_availability`

Source files:
- [`ml/sources/registry.py`](../../../ml/sources/registry.py)

## 12. Configuration parameters

Registry path `docs/data_sources/registry.yaml`.

## 13. Outputs and units

JSON via CLI/API `/api/v1/soil/sources`.

## 14. Validation criteria

Required sources present: ERA5-Land weather/soil, SMAP L4, GPM IMERG, Sentinel-1, SoilGrids, COP-DEM, ECMWF Open Data, crop/land-cover.

## 15. Missing-value handling

Unavailable properties are omitted or `not_estimated`. No fabricated soil maps.

## 16. Temporal leakage considerations

n/a for the catalogue. Forecast sources must use issue-time contracts.

## 17. Tests and expected assertions

[`tests/test_soil.py`](../../../tests/test_soil.py) registry and SoilGrids tests.

## 18. Scientific limitations

A URL is not an integration. Global soil maps are not laboratory data. SMAP/GPM/S1 are planned.

## 19. Related feature dependencies

- [`soil.era5_land_volumetric_moisture`](../soil/era5_land_volumetric_moisture.md)
- [`soil.soilgrids_static_properties`](../soil/soilgrids_static_properties.md)
- [`weather.era5_land_ingestion`](../weather/era5_land_ingestion.md)

## 20. Related bug/fix IDs

[BUG-0010](../../bugs/BUG-0010.md)

## 21. Last reviewed timestamp in UTC

`2026-10-22T08:49:05Z`
