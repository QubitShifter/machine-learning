---
feature_id: satellite.scl_map_overlay
name: SCL geospatial overlay
category: satellite
status: implemented
mathematical_method: nearest-neighbor SCL onto 10 m target grid; categorical color map; nearest reprojection to EPSG:3857
input_datasets:
- Sentinel-2 L2A scl.tif
- processed ndvi.tif
- valid_mask.tif
source_code:
- ml/visualization/map_overlay.py
- backend/app/services/satellite_map.py
- backend/app/api/satellite.py
- frontend/src/components/satellite/SclLegend.tsx
- frontend/src/pages/SatelliteExplorerPage.tsx
configuration:
- configs/satellite_multiyear.yaml
outputs:
- GET /api/v1/satellite/datasets/{id}/scenes/{scene}/map/scl
- map metadata scl_legend and scl_provenance
tests:
- tests/test_scl_overlay.py
- frontend/src/app/App.test.tsx
documentation: docs/features/satellite/scl_map_overlay.md
last_verified: '2026-10-22T13:29:48Z'
related_bugs:
- BUG-0004
---

## 1. Feature ID and name

`satellite.scl_map_overlay` — SCL geospatial overlay.

## 2. Status and version

Status: `implemented`. Overlay render version `map-overlay-v2`.

## 3. Purpose

Show the Sentinel-2 Scene Classification Layer as a georeferenced categorical map beside NDVI and RGB, with an explicit legend and provenance.

## 4. Scientific background

SCL is a classified product. Native SCL is 20 m; optical and NDVI are 10 m. Mixing native 20 m class counts with 10 m land statistics is a reporting error (BUG-0004). Overlay alignment therefore uses nearest neighbor onto the 10 m AOI grid.

## 5. Mathematical formula or algorithm

1. Load native SCL.
2. `reproject_categorical` onto the processed NDVI grid with `Resampling.nearest`.
3. Colorize integer codes 0–11 with a fixed RGB palette. Class 0 is transparent.
4. Reproject the colorized RGB to EPSG:3857 with nearest neighbor, never bilinear.

## 6. Explanation of every variable and unit

Codes: 0 no data, 1 saturated, 2 dark area, 3 cloud shadow, 4 vegetation, 5 bare soil, 6 water, 7 unclassified, 8 cloud medium, 9 cloud high, 10 thin cirrus, 11 snow/ice. Colors are display only.

## 7. Worked numerical example

A 10 m pixel whose center falls in a native 20 m SCL cell coded 11 is shown as snow/ice magenta. It is not averaged with neighboring vegetation.

## 8. Source datasets and provenance

Sentinel-2 L2A `scl.tif` under the scene raw directory. Target grid from processed `ndvi.tif`. Metadata reports native 20 m, target 10 m, alignment nearest_neighbor.

## 9. Input requirements

Processed NDVI and valid_mask define the 10 m grid. Native SCL must exist. RGB bands are not required for SCL mode.

## 10. Processing steps

Inspect overlay sources; if `scl.tif` is present add mode `scl`; render categorical PNG; cache under render version `map-overlay-v2`.

## 11. Implementation paths and functions

`colorize_scl`, `_source_display_arrays` mode `scl`, `get_map_overlay_path(..., "scl")`, Explorer SCL tab, `SclLegend`.

Source files:
- `ml/visualization/map_overlay.py`
- `backend/app/services/satellite_map.py`
- `frontend/src/components/satellite/SclLegend.tsx`

## 12. Configuration parameters

`processing.bands` includes `scl`. `processing.target_resolution_m` is 10. Valid-land mask classes {4,5} are not applied to the SCL overlay.

- `configs/satellite_multiyear.yaml`

## 13. Outputs and units

PNG overlay, `scl_legend` (code, name, RGB), `scl_provenance`. Units are class codes, not reflectance.

## 14. Validation criteria

`supported_modes` includes `scl` only when the SCL raster exists. RGB resampling for SCL is `Resampling.nearest`. `native_20m_mixed_with_10m_counts` is false.

## 15. Missing-value handling

Class 0 is transparent. Unknown codes are shown in a distinct purple and remain opaque. Missing SCL disables the mode rather than inventing classes.

## 16. Temporal leakage considerations

The overlay is the selected scene only. It does not use later acquisitions.

## 17. Tests and expected assertions

Palette matches codes 0,4,5,6,9,11; nodata alpha 0; inspect_overlay_sources order ndvi, rgb, scl; SCL display resampling nearest.

- `tests/test_scl_overlay.py`
- `frontend/src/app/App.test.tsx`

## 18. Scientific limitations

The MapLibre PNG is a display product. Scientific class counts remain the 10 m histogram panel, not native 20 m pixels and not downsampled overlay pixels.

## 19. Related feature dependencies

- [`satellite.cloud_scl_masking`](cloud_scl_masking.md)
- [`satellite.pixel_exclusion_accounting`](pixel_exclusion_accounting.md)
- [`satellite.scene_histograms`](scene_histograms.md)

## 20. Related bug/fix IDs

[`BUG-0004`](../../bugs/BUG-0004.md)

## 21. Last reviewed timestamp in UTC

`2026-10-22T13:29:48Z`
