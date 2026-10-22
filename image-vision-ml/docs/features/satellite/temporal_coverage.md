---
feature_id: satellite.temporal_coverage
name: Satellite temporal coverage
category: satellite
status: implemented
mathematical_method: Monthly counts of catalog/discovered/downloaded/processed/validated/review/rejected/unknown
input_datasets:
- STAC discovered.json
- raw and processed manifests
- quality reports
source_code:
- ml/validation/coverage.py
- ml/ingestion/expansion.py
configuration:
- configs/satellite_multiyear.yaml
outputs:
- coverage.json
- dataset_quality.json coverage
tests:
- tests/test_coverage.py
- tests/test_expansion.py
documentation: docs/features/satellite/temporal_coverage.md
last_verified: '2026-10-22T07:34:24Z'
related_bugs:
- BUG-0005
- BUG-0006
---

## 1. Feature ID and name

`satellite.temporal_coverage` — Satellite temporal coverage.

## 2. Status and version

Status: `implemented`. Satellite processing version 1.1.0 and integration version 3.2.0 apply where those modules are used. Pixel-exclusion accounting version is 1.0.0.

## 3. Purpose

Distinguish catalog knowledge from downloaded and validated observations. Unknown discovery is never displayed as zero.

## 4. Scientific background

A month without a validated NDVI scene is not a zero vegetation observation.

## 5. Mathematical formula or algorithm

For each YYYY-MM: count scenes by status. catalog_known false ⇒ discovered_candidate_scenes is null, not 0.

## 6. Explanation of every variable and unit

Statuses: catalog, discovered, downloaded, processed, validated, requires_review, rejected, unknown.

## 7. Worked numerical example

A month with catalog unknown reports discovered_candidate_scenes=null.

## 8. Source datasets and provenance

Earth Search STAC search results stored locally; no silent catalog invention.

## 9. Input requirements

manifest.json, discovered.json if present, scene quality reports.

## 10. Processing steps

build_monthly_coverage; expansion preview is dry-run only.

## 11. Implementation paths and functions

`build_monthly_coverage`, `preview_dataset_candidates`.

Source files:
- `ml/validation/coverage.py`
- `ml/ingestion/expansion.py`

## 12. Configuration parameters

period.start/end, discovery.min_footprint_overlap_pct=95.

- `configs/satellite_multiyear.yaml`

## 13. Outputs and units

Monthly integer counts; null where unknown.

## 14. Validation criteria

Tests forbid coercing unknown discovery to 0.

## 15. Missing-value handling

Missing catalog evidence stays null.

## 16. Temporal leakage considerations

Coverage diagnostics are not features for model training.

## 17. Tests and expected assertions

tests/test_coverage.py unknown-vs-zero assertions.

- `tests/test_coverage.py`
- `tests/test_expansion.py`

## 18. Scientific limitations

STAC search completeness depends on the catalog snapshot date.

## 19. Related feature dependencies

- [`integration.modeling_eligibility`](../integration/modeling_eligibility.md)

## 20. Related bug/fix IDs

[`BUG-0005`](../../bugs/BUG-0005.md), [`BUG-0006`](../../bugs/BUG-0006.md)

## 21. Last reviewed timestamp in UTC

`2026-10-22T07:34:24Z`
