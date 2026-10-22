---
feature_id: soil.plant_available_water
name: Plant-available water fraction
category: soil
status: planned
mathematical_method: R = (θ − θ_WP) / (θ_FC − θ_WP) only when both thresholds exist
input_datasets:
- None; field capacity and wilting point are unavailable
source_code:
- ml/preprocessing/soil.py
configuration:
- configs/soil_era5_land.yaml
outputs:
- plant_available_water_fraction
tests:
- tests/test_soil.py
documentation: docs/features/soil/plant_available_water.md
last_verified: '2026-10-22T08:49:05Z'
related_bugs: []
---

## 1. Feature ID and name

`soil.plant_available_water` — Plant-available water fraction.

## 2. Status and version

Status: `planned`. The guard function exists and returns null because θ_FC and θ_WP are not available.

## 3. Purpose

Eventually express volumetric moisture relative to soil-specific field capacity and wilting point.

## 4. Scientific background

Universal dry/wet θ thresholds are not used. Hydraulic parameters from pedotransfer on SoilGrids would still be estimates, not measured FC/WP.

## 5. Mathematical formula or algorithm

R = (θ − θ_WP) / (θ_FC − θ_WP) when θ, θ_FC, θ_WP are finite and θ_FC > θ_WP. Otherwise null. Not calculated in this phase.

## 6. Explanation of every variable and unit

- θ: volumetric water (m³/m³), typically θ_{0-100}.
- θ_FC, θ_WP: same units and depth support.
- R: dimensionless relative plant-available water.

## 7. Worked numerical example

`plant_available_water_fraction(0.25, None, None) is None`.

## 8. Source datasets and provenance

No FC/WP source is ingested. Config keys `quality.field_capacity` and `quality.wilting_point` are null.

## 9. Input requirements

Scientifically suitable FC and WP for the same soil support and depth as θ.

## 10. Processing steps

`aggregate_daily_soil` calls `plant_available_water_fraction` and stores null.

## 11. Implementation paths and functions

`ml/preprocessing/soil.py`: `plant_available_water_fraction`.

Source files:
- [`ml/preprocessing/soil.py`](../../../ml/preprocessing/soil.py)

## 12. Configuration parameters

[`configs/soil_era5_land.yaml`](../../../configs/soil_era5_land.yaml) `quality.field_capacity`, `quality.wilting_point`.

## 13. Outputs and units

Column `plant_available_water_fraction` remains empty.

## 14. Validation criteria

Do not compute R from invented thresholds. Tests assert None without FC/WP.

## 15. Missing-value handling

Any missing threshold → null.

## 16. Temporal leakage considerations

n/a until thresholds exist. R would still be a derived indicator, not a probe.

## 17. Tests and expected assertions

[`tests/test_soil.py`](../../../tests/test_soil.py) `test_root_zone_weights_and_formula`.

## 18. Scientific limitations

Without local hydraulic parameters the indicator is scientifically unsuitable.

## 19. Related feature dependencies

- [`soil.root_zone_profile_mean`](root_zone_profile_mean.md)
- [`soil.soilgrids_static_properties`](soilgrids_static_properties.md)

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T08:49:05Z`
