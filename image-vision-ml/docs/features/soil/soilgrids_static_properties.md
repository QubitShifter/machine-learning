---
feature_id: soil.soilgrids_static_properties
name: SoilGrids static soil properties
category: soil
status: planned
mathematical_method: Not ingested. REST API paused; properties are not fabricated
input_datasets:
- None
source_code:
- ml/ingestion/soilgrids.py
configuration: []
outputs:
- none
tests:
- tests/test_soil.py
documentation: docs/features/soil/soilgrids_static_properties.md
last_verified: '2026-10-22T08:49:05Z'
related_bugs:
- BUG-0010
---

## 1. Feature ID and name

`soil.soilgrids_static_properties` — SoilGrids static soil properties.

## 2. Status and version

Status: `planned`. A lightweight availability adapter exists; no property values are stored.

## 3. Purpose

Eventually attach sand, clay, silt, bulk density, SOC, coarse fragments, pH, and uncertainty as static agricultural context.

## 4. Scientific background

ISRIC SoilGrids are machine-learning soil maps, not laboratory measurements for the Plovdiv AOI. REST v2.0 is paused. WMS/WCS/WebDAV or official downloads would be required.

## 5. Mathematical formula or algorithm

No property is computed. `import_soilgrids_properties` returns `not_available`.

## 6. Explanation of every variable and unit

Candidate codes: sand, clay, silt (g/kg), bdod, soc, cfvo, phh2o. Units would come from the product, not from invention.

## 7. Worked numerical example

n/a — no values are produced.

## 8. Source datasets and provenance

https://isric.org/explore/soilgrids/ recorded in the source registry as `paused`.

## 9. Input requirements

A restored official access route. `allow_network` remains false by default.

## 10. Processing steps

`soilgrids_availability()` reports paused REST and `network_executed=false`.

## 11. Implementation paths and functions

`ml/ingestion/soilgrids.py`: `soilgrids_availability`, `import_soilgrids_properties`.

Source files:
- [`ml/ingestion/soilgrids.py`](../../../ml/ingestion/soilgrids.py)

## 12. Configuration parameters

none for live import.

## 13. Outputs and units

none

## 14. Validation criteria

Adapter must not fabricate records. Tests assert empty `records`.

## 15. Missing-value handling

All properties absent. Field capacity and wilting point stay null.

## 16. Temporal leakage considerations

Static maps have no forecast issue time. They still must not be labelled as measured soil moisture.

## 17. Tests and expected assertions

[`tests/test_soil.py`](../../../tests/test_soil.py) `test_soilgrids_does_not_fabricate_properties`.

## 18. Scientific limitations

Global maps ≠ local lab data. REST pause is an external service limitation, not a project-code defect.

## 19. Related feature dependencies

- [`soil.plant_available_water`](plant_available_water.md)
- [`sources.agricultural_data_registry`](../sources/agricultural_data_registry.md)

## 20. Related bug/fix IDs

[BUG-0010](../../bugs/BUG-0010.md)

## 21. Last reviewed timestamp in UTC

`2026-10-22T08:49:05Z`
