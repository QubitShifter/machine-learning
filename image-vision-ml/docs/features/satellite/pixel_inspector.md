---
feature_id: satellite.pixel_inspector
name: Georeferenced pixel inspector
category: satellite
status: implemented
mathematical_method: WGS84 click warped to raster CRS; nearest 10 m index; windowed GeoTIFF reads
input_datasets:
- processed ndvi.tif
- valid_mask.tif
- calibrated B02 B03 B04 B08
- native SCL
source_code:
- ml/visualization/map_overlay.py
- backend/app/services/satellite_map.py
- backend/app/api/satellite.py
- frontend/src/components/satellite/PixelInspector.tsx
- frontend/src/pages/SatelliteExplorerPage.tsx
- frontend/src/components/satellite/InspectorSection.tsx
configuration:
- configs/satellite_multiyear.yaml
outputs:
- GET /api/v1/satellite/datasets/{id}/scenes/{scene}/map/pixel
tests:
- tests/test_pixel_inspect.py
- backend/tests/test_pixel_inspect_api.py
- frontend/src/app/App.test.tsx
documentation: docs/features/satellite/pixel_inspector.md
last_verified: '2026-10-22T13:53:14Z'
related_bugs:
- BUG-0011
---

## 1. Feature ID and name

`satellite.pixel_inspector` — Georeferenced pixel inspector.

## 2. Status and version

Status: `implemented`. Sampling method `nearest_10m_target_grid`. Overlay render version `map-overlay-v2`.

## 3. Purpose

Read the scientific value of one AOI pixel after a map click, from processed rasters, not from displayed RGB colors. In Satellite Explorer the inspector sits at the top of the independently scrolling right sidebar so a click does not require scrolling the map out of view.

## 4. Scientific background

MapLibre shows a resampled PNG. PNG colors are stretched and not invertible to BOA reflectance or NDVI. Inspection must transform the click into the native raster grid and read GeoTIFF samples.

## 5. Mathematical formula or algorithm

1. Warp (lon, lat) EPSG:4326 → NDVI CRS with `rasterio.warp.transform`.
2. `dataset.index` gives row, col on the 10 m grid.
3. If outside `[0,height) × [0,width)`, return `coverage_state=out_of_coverage` and null values.
4. Window-read NDVI and valid_mask at (row, col).
5. Sample optical bands and SCL at the 10 m pixel center with nearest neighbor.
6. Reflectance = DN × scale + offset; nodata becomes null, not 0.

## 6. Explanation of every variable and unit

Longitude/latitude WGS84 degrees. Row/col are 0-based raster indices. B02/B03/B04/B08 are unitless BOA reflectance. NDVI is unitless. SCL is an integer class. `valid_mask` is boolean land-and-finite status.

## 7. Worked numerical example

DN_B04=4000, scale=0.0001, offset=0 → reflectance 0.4. A masked pixel with NDVI stored as NaN returns `ndvi=null` and an exclusion reason, never NDVI 0.

## 8. Source datasets and provenance

Processed scene GeoTIFFs and raw calibrated bands. Quality and calibration statuses come from `quality_report.json` / `processing_metadata.json`. `estimated_from_display_rgb` is always false.

## 9. Input requirements

NDVI and valid_mask. Optical bands and SCL are optional; missing sources return null plus `missing_reasons`.

## 10. Processing steps

Resolve dataset/scene; windowed reads only; classify exclusion with `classify_pixel_exclusions` on the 1×1 neighborhood when SCL is present.

## 11. Implementation paths and functions

`sample_pixel`, `GET .../map/pixel`, `PixelInspector`. Existing `GET .../map/ndvi/sample` remains for Explorer compatibility. Explorer layout: Pixel Inspector is first in `satellite-inspector-panel`; a click expands it, scrolls only that aside, and draws a MapLibre marker without camera motion. Scene changes clear the sample.

Source files:
- `ml/visualization/map_overlay.py`
- `backend/app/api/satellite.py`
- `frontend/src/components/satellite/PixelInspector.tsx`
- `frontend/src/pages/SatelliteExplorerPage.tsx`
- `frontend/src/components/satellite/InspectorSection.tsx`

## 12. Configuration parameters

Target CRS EPSG:32635, 10 m. Calibration scale/offset from processing metadata.

- `configs/satellite_multiyear.yaml`

## 13. Outputs and units

JSON with lon/lat, scene id, date, row/col, four reflectances, NDVI, SCL code/name, valid-mask, exclusion reason, calibration status, scene-quality status, missing_reasons.

## 14. Validation criteria

Outside footprint → all scientific values null. Masked NDVI is null not 0. Display RGB is not used.

## 15. Missing-value handling

Unavailable, nodata, nonfinite, and out-of-coverage samples are JSON null with a reason string. Zero is reserved for a measured zero reflectance on valid land.

## 16. Temporal leakage considerations

The inspector reads the selected scene only.

## 17. Tests and expected assertions

Inside pixel matches raster values; outside is out_of_coverage; masked NDVI is null; API returns SCL name. Frontend: inspector opens on click, updates on a second click, does not call `window.scrollTo`, and clears on scene change.

- `tests/test_pixel_inspect.py`
- `backend/tests/test_pixel_inspect_api.py`
- `frontend/src/app/App.test.tsx`

## 18. Scientific limitations

Nearest-neighbor assignment of 20 m SCL to a 10 m center is the same rule as processing, not a sub-pixel class fraction. Overlay PNG remaining after downsample is not the sampled grid.

## 19. Related feature dependencies

- [`satellite.ndvi`](ndvi.md)
- [`satellite.reflectance_calibration`](reflectance_calibration.md)
- [`satellite.cloud_scl_masking`](cloud_scl_masking.md)
- [`satellite.scl_map_overlay`](scl_map_overlay.md)
- [`ui.satellite_explorer_workspace`](../ui/satellite_explorer_workspace.md)

## 20. Related bug/fix IDs

[`BUG-0011`](../../bugs/BUG-0011.md) — Pixel Inspector previously sat below Scene Information and SCL Classes, so reaching measurements scrolled the map away. Layout-only fix; sampling unchanged.

## 21. Last reviewed timestamp in UTC

`2026-10-22T13:53:14Z`
