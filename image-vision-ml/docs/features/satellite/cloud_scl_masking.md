---
feature_id: satellite.cloud_scl_masking
name: Cloud and SCL masking
category: satellite
status: implemented
mathematical_method: "valid = SCL \u2208 {4,5} AND finite optical bands"
input_datasets:
- Sentinel-2 SCL 20 m scene classification
- optical 10 m bands
source_code:
- ml/preprocessing/features.py
- ml/preprocessing/raster.py
configuration:
- configs/satellite_multiyear.yaml
outputs:
- valid_mask.tif
- quality_report.json cloud_shadow_fraction_pct
tests:
- backend/tests/test_features.py
- tests/test_pixel_exclusion.py
documentation: docs/features/satellite/cloud_scl_masking.md
last_verified: '2026-10-22T07:34:24Z'
related_bugs:
- BUG-0004
- BUG-0005
---

## 1. Feature ID and name

`satellite.cloud_scl_masking` — Cloud and SCL masking.

## 2. Status and version

Status: `implemented`. Satellite processing version 1.1.0 and integration version 3.2.0 apply where those modules are used. Pixel-exclusion accounting version is 1.0.0.

## 3. Purpose

Keep vegetation and bare-soil pixels and exclude cloud, shadow, snow/ice, water, nodata, and unclassified classes.

## 4. Scientific background

Sentinel-2 SCL is a categorical 20 m product. Optical bands are 10 m. This project resamples SCL with nearest neighbour onto the 10 m target grid.

## 5. Mathematical formula or algorithm

valid(x) = 1[SCL(x) ∈ {4,5}] ∧ finite(B02,B03,B04,B08). Cloud/shadow fraction uses SCL ∈ {3,8,9,10} on the target grid: 100 * n_cloud / n_aoi.

## 6. Explanation of every variable and unit

SCL codes 0 nodata, 1 saturated, 2 dark, 3 shadow, 4 vegetation, 5 bare, 6 water, 7 unclassified, 8–10 cloud/cirrus, 11 snow/ice.

## 7. Worked numerical example

SCL=[4,5,6,11] → mask [True, True, False, False]. Snow is excluded, not treated as valid winter vegetation.

## 8. Source datasets and provenance

ESA SCL packaged in Earth Search L2A items.

## 9. Input requirements

scl.tif plus optical reflectance on the same grid.

## 10. Processing steps

Nearest-neighbour SCL reprojection; make_valid_mask; cloud fraction from target-grid histogram.

## 11. Implementation paths and functions

`make_valid_mask`, `_build_valid_mask`, `reproject_categorical`.

Source files:
- `ml/preprocessing/features.py`
- `ml/preprocessing/raster.py`

## 12. Configuration parameters

processing.apply_scl_mask, processing.valid_scl_classes=[4,5].

- `configs/satellite_multiyear.yaml`

## 13. Outputs and units

valid_mask.tif (0/1), cloud_shadow_fraction_pct.

## 14. Validation criteria

Snow/ice, water, and cloud never count as valid NDVI land.

## 15. Missing-value handling

SCL nodata (class 0) is excluded. Fill is not interpolated.

## 16. Temporal leakage considerations

Masking is per-scene.

## 17. Tests and expected assertions

test_scl_mask; test_scl_rejection_and_snow_ice.

- `backend/tests/test_features.py`
- `tests/test_pixel_exclusion.py`

## 18. Scientific limitations

SCL errors (snow vs cloud, dark vs shadow) propagate. 20 m native SCL cannot resolve 10 m mixed pixels.

## 19. Related feature dependencies

- [`satellite.ndvi_validity_coverage`](ndvi_validity_coverage.md)
- [`satellite.pixel_exclusion_accounting`](pixel_exclusion_accounting.md)

## 20. Related bug/fix IDs

[`BUG-0004`](../../bugs/BUG-0004.md), [`BUG-0005`](../../bugs/BUG-0005.md)

## 21. Last reviewed timestamp in UTC

`2026-10-22T07:34:24Z`
