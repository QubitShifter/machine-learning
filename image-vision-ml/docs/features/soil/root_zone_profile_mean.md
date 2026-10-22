---
feature_id: soil.root_zone_profile_mean
name: Root-zone 0-100 cm profile mean
category: soil
status: implemented
mathematical_method: 0.07 θ1 + 0.21 θ2 + 0.72 θ3
input_datasets:
- Daily ERA5-Land swvl1, swvl2, swvl3 means
source_code:
- ml/preprocessing/soil.py
configuration:
- configs/soil_era5_land.yaml
outputs:
- theta_root_zone_0_100
tests:
- tests/test_soil.py
documentation: docs/features/soil/root_zone_profile_mean.md
last_verified: '2026-10-22T08:49:05Z'
related_bugs: []
---

## 1. Feature ID and name

`soil.root_zone_profile_mean` — Root-zone 0–100 cm profile mean.

## 2. Status and version

Status: `implemented`. Soil processing version 3.4.0.

## 3. Purpose

Provide a thickness-weighted volumetric mean over 0–100 cm when layers 1–3 are valid.

## 4. Scientific background

ECMWF layers 1–3 span 0–7, 7–28 and 28–100 cm. Layer 4 (100–289 cm) is below 1 m and is excluded. The result is a profile-average volumetric moisture, not crop-specific effective root-zone water.

## 5. Mathematical formula or algorithm

θ_{0-100} = 0.07 θ1 + 0.21 θ2 + 0.72 θ3

Weights sum to 1.0. If any of θ1, θ2, θ3 is missing, the result is null.

## 6. Explanation of every variable and unit

- θ1, θ2, θ3: daily mean volumetric water in layers 1–3 (m³/m³).
- 0.07, 0.21, 0.72: layer thicknesses in metres.
- θ_{0-100}: profile mean (m³/m³).

## 7. Worked numerical example

θ1=0.30, θ2=0.28, θ3=0.25 → 0.07×0.30 + 0.21×0.28 + 0.72×0.25 = 0.2598.

## 8. Source datasets and provenance

Derived from `soil.era5_land_volumetric_moisture`. Dataset ID `plovdiv_soil_2023_2025`.

## 9. Input requirements

Finite daily means for swvl1, swvl2 and swvl3.

## 10. Processing steps

Computed inside `aggregate_daily_soil` after daily layer means.

## 11. Implementation paths and functions

`ml/preprocessing/soil.py`: `root_zone_theta_0_100`, `ROOT_ZONE_WEIGHTS`.

Source files:
- [`ml/preprocessing/soil.py`](../../../ml/preprocessing/soil.py)

## 12. Configuration parameters

Layer thicknesses are scientific constants in code, matching ERA5-Land documentation. They are not operator knobs.

## 13. Outputs and units

Column `theta_root_zone_0_100` (m³/m³). Period-relative anomaly is attached only when ≥30 complete days exist; it is not a climate normal.

## 14. Validation criteria

Weights sum to 1.0. Layer 4 is excluded. Missing any of layers 1–3 yields null.

## 15. Missing-value handling

Any missing layer → null. No substitution.

## 16. Temporal leakage considerations

Uses the same UTC day as the layer means. Not a forecast.

## 17. Tests and expected assertions

[`tests/test_soil.py`](../../../tests/test_soil.py) `test_root_zone_weights_and_formula`.

## 18. Scientific limitations

Not automatically the crop root zone. Different crops root to different depths. Not plant-available water unless FC and WP exist.

## 19. Related feature dependencies

- [`soil.era5_land_volumetric_moisture`](era5_land_volumetric_moisture.md)
- [`soil.plant_available_water`](plant_available_water.md)

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T08:49:05Z`
