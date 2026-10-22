---
feature_id: satellite.pixel_exclusion_accounting
name: Disjoint pixel-exclusion accounting
category: satellite
status: implemented
mathematical_method: valid_pixels + sum(excluded_by_reason) = total_aoi_pixels
input_datasets:
- Target-grid SCL, reflectance, NDVI, valid_mask
source_code:
- ml/validation/pixel_exclusion.py
- ml/validation/dataset_quality.py
configuration:
- configs/satellite_multiyear.yaml
outputs:
- quality_report.json exclusion_counts.disjoint_by_reason
tests:
- tests/test_pixel_exclusion.py
documentation: docs/features/satellite/pixel_exclusion_accounting.md
last_verified: '2026-10-22T07:34:24Z'
related_bugs:
- BUG-0004
---

## 1. Feature ID and name

`satellite.pixel_exclusion_accounting` — Disjoint pixel-exclusion accounting.

## 2. Status and version

Status: `implemented`. Satellite processing version 1.1.0 and integration version 3.2.0 apply where those modules are used. Pixel-exclusion accounting version is 1.0.0.

## 3. Purpose

Account for every AOI pixel exactly once with explicit exclusion precedence on the processed 10 m grid.

## 4. Scientific background

Native SCL is 20 m. Subtracting 20 m class counts from 10 m valid-pixel totals created a false 23,191 other_or_unclassified residual on 2025-01-19.

## 5. Mathematical formula or algorithm

Precedence: non-valid SCL class (incl. snow/ice, dark, water, nodata) → optical red/NIR nonfinite → blue/green nonfinite → |NIR+RED|≤1e-6 → valid_ndvi. Native 20 m SCL is diagnostic only.

## 6. Explanation of every variable and unit

See SCL_CLASS_NAMES in pixel_exclusion.py. other_or_unclassified now means optical/denominator leftovers on the same grid, not a mixed-resolution residual.

## 7. Worked numerical example

S2B_35TLG_20250119_0_L2A: valid 57307, snow 23388, dark 6480, SCL nodata 258, water 52, red/NIR nodata 485, blue/green 8; sum 87978.

## 8. Source datasets and provenance

Reprojected rasters at validate time; original GeoTIFFs are not rewritten.

## 9. Input requirements

raw scl.tif and optical bands; processed valid_mask/ndvi; processing_metadata calibration.

## 10. Processing steps

Deserialize target grid; nearest SCL; bilinear optical; to_reflectance; classify_pixel_exclusions.

## 11. Implementation paths and functions

`classify_pixel_exclusions`, `exclusion_report_for_scene`.

Source files:
- `ml/validation/pixel_exclusion.py`
- `ml/validation/dataset_quality.py`

## 12. Configuration parameters

processing.valid_scl_classes, processing.target_crs/resolution.

- `configs/satellite_multiyear.yaml`

## 13. Outputs and units

Counts (pixels). pixel_conservation_ok boolean.

## 14. Validation criteria

sum(disjoint)=total_aoi_pixels; stored valid_mask agrees when reconstructable.

## 15. Missing-value handling

Unreadable rasters fall back to residual_unresolved_grid and set pixel_conservation_ok false.

## 16. Temporal leakage considerations

Accounting is per scene.

## 17. Tests and expected assertions

Disjoint conservation tests; January scene exact counts.

- `tests/test_pixel_exclusion.py`

## 18. Scientific limitations

Bilinear optical resampling expands nodata along the target-grid border. That is a resampling effect, not a new SCL class.

## 19. Related feature dependencies

- [`satellite.cloud_scl_masking`](cloud_scl_masking.md)
- [`satellite.ndvi_validity_coverage`](ndvi_validity_coverage.md)

## 20. Related bug/fix IDs

[`BUG-0004`](../../bugs/BUG-0004.md)

## 21. Last reviewed timestamp in UTC

`2026-10-22T07:34:24Z`
