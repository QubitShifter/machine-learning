# Sentinel-2 Earth Search Calibration Validation

Date: 2026-10-20
Scene: `S2B_35TLG_20250916_1_L2A`
Collection: Earth Search `sentinel-2-l2a`
Product: Sentinel-2 Level-2A, processing baseline 05.11

## Correct transformation

For this Earth Search COG item the stored pixels are already harmonized.

```text
reflectance = DN * 0.0001 + 0.0
```

Do **not** apply the advertised `raster:bands` offset of `-0.1` to these files.

The general rule implemented by `ml/preprocessing/calibration.py` is:

1. Read `raster:bands.scale` and `raster:bands.offset` from the STAC asset.
2. If `earthsearch:boa_offset_applied` is `true`, keep the scale and set offset to `0`.
3. If the flag is `false`, apply both advertised scale and offset.
4. Persist the resolved coefficients in `calibration.json`.
5. If neither STAC nor local calibration is available, fail instead of inventing values.

`nodata` remains `0` and is masked **before** scale/offset.

## Evidence

Authoritative sources:

- ESA Processing Baseline 04.00 introduced `BOA_ADD_OFFSET = -1000` so SAFE JP2 values decode as `(DN - 1000) / 10000`. That is **not** automatically the Earth Search COG encoding.
- [Earth Search collection notes](https://github.com/Element84/earth-search/blob/main/docs/collections/sentinel-2-l2a.md) say some COGs already have the offset applied during conversion. The practical instruction is to inspect item metadata rather than assume SAFE behaviour.
- The live STAC item for this scene (`https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/S2B_35TLG_20250916_1_L2A`) contains:
  - `s2:processing_baseline`: `05.11`
  - `earthsearch:boa_offset_applied`: **true**
  - optical `raster:bands`: `scale=0.0001`, `offset=-0.1`

The item-level flag and the raster-extension offset contradict each other. The documented Earth Search flag is treated as authoritative for this collection. Pixel statistics are recorded as provenance and never rewrite the coefficients:

| Band | Stored DN mean | DN < 1000 | After `*0.0001` only | After `*0.0001 - 0.1` |
|---|---:|---:|---:|---:|
| B02 blue | 515 | 80,784 / 87,380 | 0.051 | −0.049 |
| B03 green | 748 | 67,562 / 87,380 | 0.075 | −0.025 |
| B04 red | 804 | 58,683 / 87,380 | 0.080 | −0.020 |
| B08 NIR | 2,710 | 6 / 87,380 | 0.271 | 0.171 |

A vegetated September AOI near Plovdiv cannot have a negative mean red reflectance. The stored DNs already look like post-offset / 10,000 reflectance. Applying `-0.1` a second time is a double correction.

The local GeoTIFFs themselves contain identity scale/offset tags (`1.0` / `0.0`). Those tags are storage defaults, not scientific calibration.

## Missing calibration handling

If `calibration.json`, STAC `raster:bands`, and non-identity GeoTIFF tags are all absent, processing raises `UnsupportedCalibrationError`. The pipeline does not invent `0.0001` / `-0.1`.

## Corrections made

The previous sidecar applied `offset=-0.1` for every optical band and `calculate_ndvi()` discarded non-positive reflectance. That combination produced only 28,570 finite NDVI pixels and was scientifically wrong for this item.

Changes:

- Resolve offset from `earthsearch:boa_offset_applied`.
- Update `first_image/calibration.json` to `scale=0.0001`, `offset=0.0`.
- Keep negative reflectance when it occurs after correct calibration; exclude only fill values, non-finite values, rejected SCL classes, and near-zero NDVI denominators.

## Valid-pixel statistics

Total pixels in the local window: **87,380**.

| Stage | Pixels | Percent | Notes |
|---|---:|---:|---|
| SCL classes 4 or 5 | 87,260 | 99.86 | 120 pixels are SCL 2 (dark/shadow) |
| Finite calibrated bands (`nodata=0` masked) | 87,380 | 100.00 | No fill pixels in this window |
| Previous finite NDVI (`offset=-0.1` and red,nir > 0) | 28,570 | 32.70 | Double offset plus positivity filter |
| Corrected finite NDVI (`offset=0`, SCL 4/5, valid denominator) | 87,260 | 99.86 | Negatives are no longer dropped automatically |

The earlier 67% loss was caused by **incorrect calibration**, not by clouds or missing data. Scene cloud cover is 0.000163%.

After the correction, `first_image` NDVI is min −0.2333, max 0.9990, mean 0.5670, valid 87,260 / 87,380 (99.86%). That matches the original exploratory raw-DN NDVI because a common positive scale cancels in the NDVI ratio. The previous `-0.1` offset did **not** cancel.

Earth Search metadata is not always trustworthy. Scene `S2C_35TLG_20250305_0_L2A` advertised `earthsearch:boa_offset_applied=false` and `offset=-0.1`, but its red DNs have mean 814. Applying `-0.1` made 76% of red reflectance negative. Phase 2.4 no longer silently switches the offset to 0. That discrepancy is stored as `validation_status=conflicting` and `requires_review=true`. Under `calibration_policy=verified_only`, the scene is excluded from the validated dataset until the source encoding is confirmed. This is the same class of catalog error documented in [Earth Search issue #66](https://github.com/Element84/earth-search/issues/66).

Negative surface-reflectance estimates can occur after atmospheric correction. They are not, by themselves, proof that the coefficients are wrong.

## Phase 3.3 calibration audit

`ml/validation/calibration_audit.py` writes `calibration_audit.json` during `validate`. It classifies stored evidence only. It does not invent `s2:processing_baseline`, does not infer encoding from the scene ID, and does not promote a scene to `valid` because NDVI looks plausible.

The two unresolved archive scenes are the same Earth Search offset-conflict class documented above and in [issue #66](https://github.com/Element84/earth-search/issues/66):

- `S2B_34TGM_20250208_0_L2A` (2025-02-08): `earthsearch:boa_offset_applied=false` with advertised optical offset −0.1; sample fractions after that offset were majority-negative; stored NDVI min/max fall far outside [−1, 1]. Status remains `requires_review`.
- `S2C_35TLG_20250308_0_L2A` (2025-03-08): native 35TLG tile with the same advertised-offset vs sample conflict and physically implausible NDVI. Status remains `requires_review`.

The defects are not assumed identical beyond the shared catalog-encoding class. Missing authoritative metadata keeps `requires_review`. Reprocessing may refresh evidence; it must not silently rewrite coefficients.

`calibration_status` / audit `current_status` describe radiometric coefficients. `scene_quality_status` describes overall usability (coverage, valid NDVI, grid, missing assets). A winter scene may be `scene_quality_status=rejected` while `calibration_status=verified`. See [`feature_registry.md`](feature_registry.md) and [`bugs/BUG-0006.md`](bugs/BUG-0006.md), [`bugs/BUG-0007.md`](bugs/BUG-0007.md).
