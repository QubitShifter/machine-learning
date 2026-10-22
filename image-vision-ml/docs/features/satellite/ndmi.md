---
feature_id: satellite.ndmi
name: NDMI with Sentinel-2 B11
category: satellite
status: planned
mathematical_method: not implemented; (NIR-SWIR)/(NIR+SWIR) would require B11
input_datasets: none
source_code: none
configuration: none
outputs: none
tests: none
documentation: docs/features/satellite/ndmi.md
last_verified: '2026-10-22T09:37:16Z'
related_bugs: []
---

## 1. Feature ID and name

`satellite.ndmi` — NDMI with Sentinel-2 B11.

## 2. Status and version

Status: `planned`. Not implemented.

## 3. Purpose

Reserve an interface for the Normalized Difference Moisture Index once SWIR B11 is ingested.

## 4. Scientific background

NDMI uses NIR and SWIR. Current Image Vision ML satellite ingestion stores B02, B03, B04, B08, and SCL only.

## 5. Mathematical formula or algorithm

Not implemented. The conventional formula would be `(B08−B11)/(B08+B11)` after BOA calibration. No NDMI raster is produced.

## 6. Explanation of every variable and unit

B11 is not present. No NDMI unit is emitted.

## 7. Worked numerical example

Not applicable. The UI lists NDMI under later modules only.

## 8. Source datasets and provenance

None.

## 9. Input requirements

Sentinel-2 L2A B11 COGs, which are not in the current band list.

## 10. Processing steps

None.

## 11. Implementation paths and functions

UI reservation: `frontend/src/components/analysis/PlannedModules.tsx`. No backend endpoint.

## 12. Configuration parameters

None.

## 13. Outputs and units

None.

## 14. Validation criteria

Must not appear as an implemented histogram or map overlay.

## 15. Missing-value handling

Not applicable.

## 16. Temporal leakage considerations

Not applicable.

## 17. Tests and expected assertions

Frontend planned-modules copy states NDMI is not available because B11 is not ingested.

## 18. Scientific limitations

Without B11, NDMI cannot be computed. Substituting NDVI or RGB is not NDMI.

## 19. Related feature dependencies

- [`satellite.scene_histograms`](scene_histograms.md)
- [`satellite.reflectance_calibration`](reflectance_calibration.md)

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T09:37:16Z`
