---
feature_id: satellite.ndvi
name: NDVI computation
category: satellite
status: implemented
mathematical_method: NDVI = (NIR - RED) / (NIR + RED)
input_datasets:
- Earth Search sentinel-2-l2a BOA reflectance
source_code:
- ml/preprocessing/features.py
- ml/preprocessing/raster.py
configuration:
- configs/satellite_multiyear.yaml
outputs:
- ndvi.tif
- statistics.json valid_pixels/mean/min/max
tests:
- backend/tests/test_features.py
- tests/test_pixel_exclusion.py
documentation: docs/features/satellite/ndvi.md
last_verified: '2026-10-22T07:34:24Z'
related_bugs:
- BUG-0004
- BUG-0005
---

## 1. Feature ID and name

`satellite.ndvi` — NDVI computation.

## 2. Status and version

Status: `implemented`. Satellite processing version 1.1.0 and integration version 3.2.0 apply where those modules are used. Pixel-exclusion accounting version is 1.0.0.

## 3. Purpose

Compute a vegetation-greenness index from calibrated red and NIR surface reflectance on the 10 m AOI grid.

## 4. Scientific background

NDVI is a bounded spectral index used as a vegetation-activity proxy, not a direct soil-moisture observation.

## 5. Mathematical formula or algorithm

NDVI = (NIR - RED) / (NIR + RED), with |NIR+RED| > 1e-6. Implemented in `calculate_ndvi`.

## 6. Explanation of every variable and unit

RED, NIR: unitless BOA reflectance. NDVI: unitless, theoretically about [-1, 1]. NDVI_DENOMINATOR_EPS = 1e-6.

## 7. Worked numerical example

RED=0.2, NIR=0.6 → (0.4)/(0.8)=0.5. RED=NIR=0 → NaN.

## 8. Source datasets and provenance

Sentinel-2 L2A via Earth Search STAC; local GeoTIFF windows under data/raw/satellite/.

## 9. Input requirements

Calibrated B04 and B08 arrays on the target grid; optional valid_mask from SCL 4/5 and finite bands.

## 10. Processing steps

Calibrate DN → reflectance; build valid mask; compute NDVI; write GeoTIFF and statistics.

## 11. Implementation paths and functions

`ml.preprocessing.features.calculate_ndvi`, `calculate_ndvi_statistics`; called from `process_local_dataset`.

Source files:
- `ml/preprocessing/features.py`
- `ml/preprocessing/raster.py`

## 12. Configuration parameters

processing.calculate_ndvi, processing.bands, processing.target_resolution_m=10.

- `configs/satellite_multiyear.yaml`

## 13. Outputs and units

ndvi.tif (unitless), statistics.json (valid_pixels, valid_percentage, mean/min/max/median/std).

## 14. Validation criteria

Finite pixels only; statistics ignore NaN. Quality gate uses valid_percentage vs min_valid_ndvi_pct=70.

## 15. Missing-value handling

Invalid, non-finite, masked, and near-zero-denominator pixels are NaN. They are not interpolated.

## 16. Temporal leakage considerations

NDVI is a same-scene observation. It is not a forecast and does not use later scenes.

## 17. Tests and expected assertions

test_ndvi_formula expects 0.5; test_ndvi_zero_denominator expects NaN.

- `backend/tests/test_features.py`
- `tests/test_pixel_exclusion.py`

## 18. Scientific limitations

NDVI saturates in dense canopy, is season- and soil-background dependent, and is not soil moisture.

## 19. Related feature dependencies

- [`satellite.reflectance_calibration`](reflectance_calibration.md)
- [`satellite.cloud_scl_masking`](cloud_scl_masking.md)
- [`satellite.ndvi_validity_coverage`](ndvi_validity_coverage.md)

## 20. Related bug/fix IDs

[`BUG-0004`](../../bugs/BUG-0004.md), [`BUG-0005`](../../bugs/BUG-0005.md)

## 21. Last reviewed timestamp in UTC

`2026-10-22T07:34:24Z`
