---
feature_id: soil.soil_moisture
name: Soil moisture analysis
category: soil
status: planned
mathematical_method: Not implemented. No in-situ or microwave soil-moisture retrieval
  is in this repository.
input_datasets:
- None in repository
source_code: []
configuration: []
outputs:
- none
tests: []
documentation: docs/features/soil/soil_moisture.md
last_verified: '2026-10-22T08:49:05Z'
related_bugs: []
---

## 1. Feature ID and name

`soil.soil_moisture` — Soil moisture analysis.

## 2. Status and version

Status: `planned`. Satellite processing version 1.1.0 and integration version 3.2.0 apply where those modules are used. Pixel-exclusion accounting version is 1.0.0.

## 3. Purpose

Eventually estimate soil-water availability, dryness, wetness and saturation. Not implemented.

## 4. Scientific background

NDVI and ERA5-Land precipitation are related to vegetation and atmospheric water, not a calibrated soil-moisture product.

## 5. Mathematical formula or algorithm

No soil-moisture equation is implemented. Do not treat NDVI as soil moisture.

## 6. Explanation of every variable and unit

n/a

## 7. Worked numerical example

n/a — no numerical method is executed.

## 8. Source datasets and provenance

No in-situ soil-moisture dataset is ingested. Modeled ERA5-Land volumetric water is a separate feature (`soil.era5_land_volumetric_moisture`) and is not this ground-truth target.

## 9. Input requirements

Would require in-situ probes and/or a documented satellite soil-moisture product.

## 10. Processing steps

Planned only.

## 11. Implementation paths and functions

No implementation path. Absence verified by repository search.

Source files:
- `*(none — planned)*`

## 12. Configuration parameters

none

No configuration file.

## 13. Outputs and units

none

## 14. Validation criteria

supervised_soil_forecasting is not_ready.

## 15. Missing-value handling

There are no soil-moisture values to fill.

## 16. Temporal leakage considerations

n/a

## 17. Tests and expected assertions

Modeling readiness tests assert soil task not_ready.

No dedicated implementation tests (planned feature).

## 18. Scientific limitations

This is a planned capability. Documenting it as implemented would be false.

## 19. Related feature dependencies

- [`integration.modeling_eligibility`](../integration/modeling_eligibility.md)
- [`soil.era5_land_volumetric_moisture`](era5_land_volumetric_moisture.md)

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T08:49:05Z`
