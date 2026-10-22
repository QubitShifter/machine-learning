---
feature_id: aoi.study_area_registry
name: Multi-AOI registry and draft geometry
category: aoi
status: partial
mathematical_method: WGS84 bbox/polygon validation; equirectangular area km²; no dataset creation
input_datasets:
- configs/aoi_registry.yaml
source_code:
- ml/aoi/geometry.py
- ml/aoi/registry.py
- backend/app/services/aoi_service.py
- frontend/src/pages/AoiPage.tsx
configuration:
- configs/aoi_registry.yaml
outputs:
- GET /api/v1/aoi/areas
- POST /api/v1/aoi/drafts
tests:
- tests/test_aoi_registry.py
- backend/tests/test_aoi_api.py
- frontend/src/utils/aoiGeometry.test.ts
- frontend/src/app/App.test.tsx
documentation: docs/features/aoi/study_area_registry.md
last_verified: '2026-10-22T13:29:48Z'
related_bugs: []
---

## 1. Feature ID and name

`aoi.study_area_registry` — Multi-AOI registry and draft geometry.

## 2. Status and version

Status: `partial`. Registry version `3.5.0`. Operational Plovdiv AOI is read-only. Multi-dataset satellite switching is not implemented.

## 3. Purpose

Prepare the application to describe more than one agricultural study area without downloading new Sentinel-2, weather, or soil archives, and without modifying the current Plovdiv dataset.

## 4. Scientific background

The operational study window is `[24.65, 42.05, 24.68, 42.08]` (west, south, east, north, EPSG:4326). Satellite, weather, and soil pipelines currently assume one dataset identity per product. Wiring new geometry into those pipelines would be an invasive refactor.

## 5. Mathematical formula or algorithm

Bbox validity: west < east, south < north, edges ≤ 2°, area in [0.01, 2500] km².

Area ≈ |Δlon| · 111320 · cos(φ̄) · |Δlat| · 110574 / 10^6 km².

Polygon area uses an equirectangular shoelace. Self-intersecting rings are rejected. Approximate 10 m pixel count is area_m² / 100. ERA5 cell count is ceil(Δlon/0.1)·ceil(Δlat/0.1).

## 6. Explanation of every variable and unit

Coordinates are WGS84 degrees. Area is km². `status=operational` means an existing dataset. `status=draft` means a proposal with `downloads_started=false`.

## 7. Worked numerical example

Plovdiv 0.03° × 0.03° at 42.065°N is a few square kilometres and is accepted. A 5° box is rejected as too large for this phase.

## 8. Source datasets and provenance

Operational rows come from `configs/aoi_registry.yaml`. Drafts are stored in `data/cache/aoi_drafts.json`, never under `data/raw/soil` or `data/processed/soil`.

## 9. Input requirements

A bbox of four numbers or a polygon of at least three vertices.

## 10. Processing steps

Load registry; validate geometry; persist draft JSON; return scope notes. Do not call STAC, CDS, or soil processing.

## 11. Implementation paths and functions

`validate_bbox`, `geometry_payload`, `load_registry`, `aoi_service.create_draft`, `AoiPage` MapLibre two-click box / vertex polygon.

Source files:
- `ml/aoi/geometry.py`
- `backend/app/api/aoi.py`
- `frontend/src/pages/AoiPage.tsx`

## 12. Configuration parameters

`configs/aoi_registry.yaml` lists the operational Plovdiv AOI and dataset ids.

- `configs/aoi_registry.yaml`

## 13. Outputs and units

Registry JSON, draft records, UI coordinates/area/scope. No GeoTIFFs.

## 14. Validation criteria

Operational Plovdiv row is immutable in this API. Invalid geometry returns HTTP 422. Drafts set `downloads_started=false`.

## 15. Missing-value handling

Unknown AOI ids are not invented. Missing registry file yields an empty area list.

## 16. Temporal leakage considerations

Geometry proposals have no time axis and do not join weather or soil.

## 17. Tests and expected assertions

Plovdiv bbox valid; inverted/oversized boxes rejected; self-intersecting polygon rejected; API draft does not start downloads.

- `tests/test_aoi_registry.py`
- `backend/tests/test_aoi_api.py`
- `frontend/src/utils/aoiGeometry.test.ts`

## 18. Scientific limitations

This is a documented prototype plus isolated UI. Selecting a draft does not switch Explorer rasters, weather cells, or soil archives. Full multi-AOI processing remains a later architectural change.

## 19. Related feature dependencies

- [`satellite.ndvi`](../satellite/ndvi.md)
- [`sources.agricultural_data_registry`](../sources/agricultural_data_registry.md)

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T13:29:48Z`
