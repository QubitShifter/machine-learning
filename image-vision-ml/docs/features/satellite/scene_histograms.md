---
feature_id: satellite.scene_histograms
name: Scene NDVI, reflectance, and SCL histograms
category: satellite
status: implemented
mathematical_method: equal-width np.histogram on unmasked finite samples; P99 auto-zoom viewport; NDVI domain [-1,1]; reflectance domain [0,1]
input_datasets:
- Processed ndvi.tif or ndvi_corrected.tif
- valid_mask.tif
- Calibrated B02/B03/B04 rasters
- Target-grid SCL
source_code:
- ml/analysis/scene_histograms.py
- backend/app/api/satellite.py
- backend/app/services/satellite_service.py
- frontend/src/components/satellite/SceneScientificPanels.tsx
- frontend/src/components/charts/HistogramChart.tsx
- frontend/src/utils/histogramZoom.ts
configuration:
- configs/satellite_multiyear.yaml
outputs:
- GET /api/v1/satellite/datasets/{id}/scenes/{scene}/histograms
- histograms_b{bins}.json cache
tests:
- tests/test_scene_histograms.py
- backend/tests/test_histogram_api.py
- frontend/src/app/App.test.tsx
- frontend/src/utils/histogramZoom.test.ts
documentation: docs/features/satellite/scene_histograms.md
last_verified: '2026-10-22T13:29:48Z'
related_bugs: []
---

## 1. Feature ID and name

`satellite.scene_histograms` — Scene NDVI, reflectance, and SCL histograms.

## 2. Status and version

Status: `implemented`. Histogram version `3.5.0`. Pixel-exclusion version `1.0.0`. Processing version `1.1.0` where present.

## 3. Purpose

Inspect the selected Sentinel-2 scene scientifically from the actual processed rasters, without sending GeoTIFFs to the browser or treating display PNGs as reflectance.

## 4. Scientific background

NDVI is unitless in [−1, 1] for valid land pixels. BOA surface reflectance is dimensionless, typically 0–1 after `DN * scale + offset`. SCL is a classification map. Native SCL is 20 m; optical and NDVI are 10 m. Class counts for this panel use the 10 m AOI target grid.

## 5. Mathematical formula or algorithm

Equal-width bins: edges = `np.linspace(low, high, bins+1)` with default `bins=45`.

Counts: `np.histogram(in_range, bins=edges)` on samples where `valid_mask` is true and the value is finite and inside `[low, high]`.

Pixel conservation: `in_range + out_of_range + nonfinite_unmasked + masked = total_pixels`.

Statistics (mean, median, std, min, max, P10, P90, P99) use only in-range unmasked finite samples. Masked pixels are never counted as NDVI or reflectance 0. Invalid values are not clamped into the domain.

Auto Zoom (default display): visible X-axis `[0, min(1, max(enabled P99)×1.15)]` with a 0.05 floor. Full Range restores `[0, 1]`. Zoom is a viewport over the original equal-width bins; counts are never merged. Explorer requests 100 reflectance bins so a zoomed window still has useful bars. Percent of valid samples outside the viewport is the share of in-range counts whose bin `edge_left >= zoom_high`.

SCL: unique class counts on the 10 m target grid. Groups: snow/ice (11), cloud and shadow (3,8,9,10), water (6), vegetation (4), bare soil (5), other (0,1,2,7 and unknown codes).

## 6. Explanation of every variable and unit

- NDVI: `(NIR−RED)/(NIR+RED)`, unitless.
- Reflectance: BOA surface reflectance, dimensionless.
- `valid_mask`: processed land-and-finite mask; false pixels are excluded.
- P10/P90/P99: percentiles of in-range samples. P99 drives Auto Zoom.
- Pixel accounting: total, masked, histogrammed, nonfinite, out of domain, conservation.
- `scientific_use`: `rejected_or_review` when scene quality is rejected or requires_review.

## 7. Worked numerical example

Array `[0.4, 0.8]` unmasked and one masked `0.0`: mean = 0.6, masked count = 1, valid count = 2. The masked 0 is not a histogram bin.

## 8. Source datasets and provenance

Processed scene directory under `data/processed/satellite/<dataset>/scenes/<scene>/`. Reflectance from raw `red_B04.tif`, `green_B03.tif`, `blue_B02.tif` with processing_metadata calibration. Cache fingerprints mtime/size of sources plus bins and histogram version.

## 9. Input requirements

`ndvi.tif` or `ndvi_corrected.tif` and `valid_mask.tif` on the same grid. Reflectance optional if raw bands exist. SCL from reprojected 10 m SCL or, if rasters are absent, `exclusion_counts.scl_class_distribution_target_grid`.

## 10. Processing steps

Load NDVI and mask; compute NDVI histogram; load reflectance via `_load_reflectance`; nearest-neighbour SCL onto the target grid; attach quality and calibration independently; write versioned JSON cache.

## 11. Implementation paths and functions

`masked_histogram`, `scene_histogram_payload`, `build_scene_histograms`, `GET .../histograms`, `SceneScientificPanels`.

Source files:
- `ml/analysis/scene_histograms.py`
- `backend/app/api/satellite.py`
- `frontend/src/components/satellite/SceneScientificPanels.tsx`

## 12. Configuration parameters

`bins` query 8–200, default 45. Explorer reflectance display uses 100 bins. `processing.valid_scl_classes` remains {4,5} for the mask, not for SCL class display.

- `configs/satellite_multiyear.yaml`

## 13. Outputs and units

JSON: NDVI histogram and statistics; per-channel reflectance histograms; 10 m SCL classes and groups; warnings; provenance. Cache `histograms_b{bins}.json`.

## 14. Validation criteria

Pixel conservation true. `masked_treated_as_zero` false. `clamped` false. `native_20m_mixed` false. Rejected scenes carry `scientific_use=rejected_or_review`. Auto Zoom upper bound ≤ 1. Per-band histogrammed counts are not forced equal.

## 15. Missing-value handling

Masked and non-finite samples are excluded, not filled. Missing reflectance sets `available=false`. Catalog-only scenes return 404.

## 16. Temporal leakage considerations

A histogram is a same-scene observation. It does not use later scenes or weather after the acquisition date.

## 17. Tests and expected assertions

Pixel conservation; masked 0 excluded; out-of-range not clamped; SCL 10 m groups; rejected warning with independent calibration status; API 404 without rasters; P99 auto-zoom; one-pixel band spread not forced equal.

- `tests/test_scene_histograms.py`
- `backend/tests/test_histogram_api.py`
- `frontend/src/app/App.test.tsx`
- `frontend/src/utils/histogramZoom.test.ts`

## 18. Scientific limitations

Histograms describe the selected AOI window only. Rejected scenes must not be cited as validated agricultural science. Display RGB PNG is not this product. Out-of-range reflectance is counted, not hidden.

## 19. Related feature dependencies

- [`satellite.ndvi`](ndvi.md)
- [`satellite.reflectance_calibration`](reflectance_calibration.md)
- [`satellite.cloud_scl_masking`](cloud_scl_masking.md)
- [`satellite.pixel_exclusion_accounting`](pixel_exclusion_accounting.md)

## 20. Related bug/fix IDs

None newly confirmed for this feature. Mixed-resolution SCL accounting remains [BUG-0004](../../bugs/BUG-0004.md).

## 21. Last reviewed timestamp in UTC

`2026-10-22T13:29:48Z`
