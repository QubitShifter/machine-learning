---
feature_id: satellite.ndvi_validity_coverage
name: NDVI validity and coverage
category: satellite
status: implemented
mathematical_method: valid_ndvi_pct = 100 * valid_pixels / total_aoi_pixels
input_datasets:
- Processed NDVI and valid_mask on EPSG:32635 10 m grid
source_code:
- ml/preprocessing/features.py
- ml/validation/dataset_quality.py
configuration:
- configs/satellite_multiyear.yaml
outputs:
- quality_report.json valid_ndvi_pct
- dataset_quality.json
tests:
- tests/test_dataset_quality.py
- tests/test_pixel_exclusion.py
documentation: docs/features/satellite/ndvi_validity_coverage.md
last_verified: '2026-10-22T07:34:24Z'
related_bugs:
- BUG-0004
- BUG-0005
---

## 1. Feature ID and name

`satellite.ndvi_validity_coverage` — NDVI validity and coverage.

## 2. Status and version

Status: `implemented`. Satellite processing version 1.1.0 and integration version 3.2.0 apply where those modules are used. Pixel-exclusion accounting version is 1.0.0.

## 3. Purpose

Measure the fraction of AOI pixels with finite, masked NDVI and apply quality gates.

## 4. Scientific background

Geometric footprint overlap is not the same as valid spectral coverage. Winter snow can yield 100% footprint overlap and still fail the 70% valid-NDVI gate.

## 5. Mathematical formula or algorithm

valid_ndvi_pct = 100 * N_finite_ndvi / N_aoi. Reject if footprint < 95% or valid_ndvi_pct < 70%. Warning if 70% ≤ valid_ndvi_pct < 85%.

## 6. Explanation of every variable and unit

N_aoi: 258×341 = 87978 for the Plovdiv target grid. N_finite_ndvi: finite NDVI after mask.

## 7. Worked numerical example

57307/87978 = 65.14% → rejected (valid_ndvi_below_threshold). Thresholds are not lowered.

## 8. Source datasets and provenance

statistics.json written during processing; quality_report.json during validate.

## 9. Input requirements

Processed statistics and geometric footprint_overlap_pct from STAC/AOI intersection.

## 10. Processing steps

Compute statistics; evaluate_scene_quality; persist quality_report.json.

## 11. Implementation paths and functions

`calculate_ndvi_statistics`, `evaluate_scene_quality`.

Source files:
- `ml/preprocessing/features.py`
- `ml/validation/dataset_quality.py`

## 12. Configuration parameters

quality.min_aoi_coverage_pct=95, min_valid_ndvi_pct=70, warning_valid_ndvi_pct=85.

- `configs/satellite_multiyear.yaml`

## 13. Outputs and units

valid_ndvi_pct (percent), valid_pixels (count), total_aoi_pixels (count).

## 14. Validation criteria

Rejected scenes remain rejected. Missing NDVI is not fabricated to pass the gate.

## 15. Missing-value handling

NaN NDVI pixels reduce coverage; they are not filled.

## 16. Temporal leakage considerations

Coverage is per acquisition date.

## 17. Tests and expected assertions

test_quality_thresholds_are_not_lowered; January scene stays rejected.

- `tests/test_dataset_quality.py`
- `tests/test_pixel_exclusion.py`

## 18. Scientific limitations

A 70% land-NDVI gate is an operational project threshold, not a universal scientific standard.

## 19. Related feature dependencies

- [`satellite.ndvi`](ndvi.md)
- [`satellite.pixel_exclusion_accounting`](pixel_exclusion_accounting.md)

## 20. Related bug/fix IDs

[`BUG-0004`](../../bugs/BUG-0004.md), [`BUG-0005`](../../bugs/BUG-0005.md)

## 21. Last reviewed timestamp in UTC

`2026-10-22T07:34:24Z`
