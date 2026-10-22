---
feature_id: satellite.reflectance_calibration
name: Reflectance calibration
category: satellite
status: implemented
mathematical_method: reflectance = DN * scale + offset, nodata masked first
input_datasets:
- Earth Search sentinel-2-l2a COGs
- STAC raster:bands
- earthsearch:boa_offset_applied
source_code:
- ml/preprocessing/features.py
- ml/preprocessing/calibration.py
- ml/validation/calibration_audit.py
configuration:
- configs/satellite_multiyear.yaml
outputs:
- calibration.json
- processing_metadata.json calibration
tests:
- tests/test_calibration.py
- tests/test_calibration_audit.py
- backend/tests/test_features.py
documentation: docs/features/satellite/reflectance_calibration.md
last_verified: '2026-10-22T07:34:24Z'
related_bugs:
- BUG-0006
- BUG-0007
---

## 1. Feature ID and name

`satellite.reflectance_calibration` — Reflectance calibration.

## 2. Status and version

Status: `implemented`. Satellite processing version 1.1.0 and integration version 3.2.0 apply where those modules are used. Pixel-exclusion accounting version is 1.0.0.

## 3. Purpose

Convert Sentinel-2 digital numbers to BOA reflectance using documented Earth Search coefficients.

## 4. Scientific background

ESA baseline 04.00 uses BOA_ADD_OFFSET=-1000 on SAFE JP2. Earth Search COGs may already include that offset when earthsearch:boa_offset_applied is true.

## 5. Mathematical formula or algorithm

reflectance = DN * scale + offset. If earthsearch:boa_offset_applied is true, offset is forced to 0 while scale is kept. nodata is masked before the affine transform.

## 6. Explanation of every variable and unit

DN: stored integer/float code. scale: typically 0.0001. offset: 0.0 when BOA already applied, otherwise advertised raster:bands offset (often -0.1). reflectance: unitless.

## 7. Worked numerical example

DN=3000, scale=0.0001, offset=0 → 0.30. DN=0 nodata → NaN, not -0.1.

## 8. Source datasets and provenance

STAC item raster:bands and earthsearch:boa_offset_applied; persisted in calibration.json. Coefficients are never invented.

## 9. Input requirements

Optical bands B02,B03,B04,B08 plus calibration sidecar or STAC metadata.

## 10. Processing steps

Read advertised scale/offset; apply BOA flag rule; persist; convert arrays; do not rewrite coefficients from sample NDVI.

## 11. Implementation paths and functions

`to_reflectance`; `ml.preprocessing.calibration` resolvers; `audit_scene_calibration`.

Source files:
- `ml/preprocessing/features.py`
- `ml/preprocessing/calibration.py`
- `ml/validation/calibration_audit.py`

## 12. Configuration parameters

quality.calibration_policy=verified_only.

- `configs/satellite_multiyear.yaml`

## 13. Outputs and units

Reflectance arrays (unitless); calibration.validation_status verified|unverified|conflicting|missing.

## 14. Validation criteria

verified_only scenes with unverified/conflicting calibration are requires_review, not auto-validated from plausible NDVI.

## 15. Missing-value handling

Missing calibration raises UnsupportedCalibrationError. Missing STAC hrefs are recorded, not fabricated.

## 16. Temporal leakage considerations

Calibration is radiometric, not temporal.

## 17. Tests and expected assertions

test_reflectance_scale_and_offset; conflicting offset is not validated from NDVI.

- `tests/test_calibration.py`
- `tests/test_calibration_audit.py`
- `backend/tests/test_features.py`

## 18. Scientific limitations

Two 2025 scenes remain requires_review because Earth Search encoding vs advertised offset conflicts. Negative reflectance can be a real BOA remainder.

## 19. Related feature dependencies

- [`satellite.ndvi`](ndvi.md)

## 20. Related bug/fix IDs

[`BUG-0006`](../../bugs/BUG-0006.md), [`BUG-0007`](../../bugs/BUG-0007.md)

## 21. Last reviewed timestamp in UTC

`2026-10-22T07:34:24Z`
