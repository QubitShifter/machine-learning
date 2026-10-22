# Bug and Fix History

Permanent chronological record of confirmed bugs, suspected defects, scientific data issues, fixes, and unresolved technical problems in Image Vision ML.

Individual records live under [`bugs/`](bugs/README.md). Feature documentation lives in the [`feature registry`](feature_registry.md).

## Workflow

```text
OPEN → INVESTIGATING → FIXED → VERIFIED
```

Also supported: `DEFERRED`, `NOT_A_BUG`, `REOPENED`.

Rules:

1. Record an issue when it is confirmed or meaningfully suspected.
2. Link evidence (reports, paths, tests). Do not paste secrets or huge logs.
3. Record root cause only when established; otherwise `under investigation`.
4. A fix timestamp is the time the code or data change was made.
5. Add regression tests where feasible.
6. Record actual test results.
7. Mark `VERIFIED` only after validation succeeds, with a **later** timestamp than `FIXED`.
8. Keep the entire timeline. Never reuse IDs. Never delete closed records.

Statuses are stored lowercase in YAML (`open`, `investigating`, `fixed`, `verified`, `deferred`, `not_a_bug`, `reopened`).

Timestamps are UTC ISO 8601 (`2026-10-22T07:34:24Z`). Historical incidents with unknown event times use `unknown` and `retrospective: true`. `documented_at` is when the record was written.

```bash
python -m scripts.bug_log list
python -m scripts.bug_log validate
```

`python -m scripts.bug_log update BUG-0004 --status verified --note "..."` appends a timeline event and must not rewrite earlier timestamps.

Not every rejected satellite observation is a software bug.

## Records

<!-- BUG_TABLE_START -->
| Bug ID | Title | Category | Severity | Status | Detected at | Fixed at | Verified at | Affected feature | Root cause | Resolution | Details |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `BUG-0001` | ERA5-Land zero-byte monthly or boundary file treated as a completed download | data | high | verified | unknown | 2026-10-22T07:40:51Z | 2026-10-22T07:45:24Z | `weather.era5_land_ingestion`, `weather.precipitation_aggregation` | A zero-byte NetCDF was not distinguished from a successful CDS payload, and a later retry refused to replace an empty destination. | month_integrity flags empty_hourly_file and empty_boundary_file; empty destinations may be replaced; non-empty files are still never overwritten. | [BUG-0001](bugs/BUG-0001.md) |
| `BUG-0002` | Download retry refuses to overwrite a non-empty monthly weather file | data | informational | not_a_bug | unknown | — | — | `weather.era5_land_ingestion` | Intentional data-safety rule. Complete checksum-matched files must not be overwritten. | Kept. Empty files are handled under BUG-0001; checksum-mismatched non-empty files still require review. | [BUG-0002](bugs/BUG-0002.md) |
| `BUG-0003` | July 2024 weather month historically marked failed in the manifest | data | medium | not_a_bug | unknown | — | — | `weather.era5_land_ingestion` | unknown whether a CDS retrieve actually failed; failed is a valid downloader status. Current manifest status is downloaded. | No code change. Current July 2024 record is status downloaded with checksums. Historical failed mark is not preserved in the current file. | [BUG-0003](bugs/BUG-0003.md) |
| `BUG-0004` | Mixed 20 m SCL and 10 m NDVI pixel accounting produced a false other_or_unclassified residual | code | high | verified | 2026-10-22T07:13:38Z | 2026-10-22T07:40:51Z | 2026-10-22T07:45:24Z | `satellite.pixel_exclusion_accounting`, `satellite.cloud_scl_masking`, `satellite.ndvi_validity_coverage` | Native 20 m SCL class counts were subtracted from 10 m valid-pixel exclusions. | Disjoint classification on the processed 10 m target grid with explicit SCL then optical then NDVI-denominator precedence. | [BUG-0004](bugs/BUG-0004.md) |
| `BUG-0005` | January 2025 Sentinel-2 scene rejected for valid NDVI below 70 percent | science | informational | not_a_bug | 2026-10-22T07:13:38Z | — | — | `satellite.ndvi_validity_coverage`, `satellite.cloud_scl_masking` | Quality control working as designed. Winter snow/ice and dark SCL classes leave 65.14 percent valid land NDVI. | Scene left rejected. Thresholds unchanged. Missing NDVI not interpolated. | [BUG-0005](bugs/BUG-0005.md) |
| `BUG-0006` | Two Sentinel-2 scenes remain requires_review for radiometric calibration conflicts | science | high | deferred | unknown | — | — | `satellite.reflectance_calibration`, `integration.modeling_eligibility` | Earth Search advertised raster:bands offset versus earthsearch:boa_offset_applied encoding conflict (issue-66 class). Authoritative resolution is not available from sample NDVI. | Scenes kept requires_review. Coefficients not rewritten from statistics. | [BUG-0006](bugs/BUG-0006.md) |
| `BUG-0007` | Calibration audit current_status was easy to confuse with overall scene quality | documentation | medium | verified | 2026-10-22T07:34:24Z | 2026-10-22T07:40:51Z | 2026-10-22T07:45:24Z | `satellite.reflectance_calibration`, `satellite.ndvi_validity_coverage` | Field name current_status in the calibration audit stored calibration validity, while quality_status stored overall scene QC. A rejected snow scene can still have verified calibration. | Added scene_quality_status, scene_quality_reasons, calibration_status, and status_scope=calibration. quality_status kept for compatibility. | [BUG-0007](bugs/BUG-0007.md) |
| `BUG-0008` | Optional Parquet export is skipped without pyarrow or fastparquet | environment | low | not_a_bug | unknown | — | — | `weather.era5_land_ingestion` | pandas.DataFrame.to_parquet requires an optional engine. CSV export remains the canonical artefact. | Keep CSV as required output. Parquet remains best-effort and is skipped with a log message. | [BUG-0008](bugs/BUG-0008.md) |
| `BUG-0009` | Calibration audit STAC hrefs are empty when the scene record has no assets | documentation | low | verified | 2026-10-22T07:34:24Z | 2026-10-22T07:44:59Z | 2026-10-22T07:45:25Z | `satellite.reflectance_calibration` | Audit read record.assets; the manifest stores COG hrefs as source_urls. | Copy hrefs from assets or source_urls. Completeness flag remains; URLs are never invented. | [BUG-0009](bugs/BUG-0009.md) |
| `BUG-0010` | ISRIC SoilGrids REST API is paused so static soil properties cannot be ingested | environment | informational | not_a_bug | 2026-10-22T08:49:05Z | — | — | `soil.soilgrids_static_properties`, `sources.agricultural_data_registry` | External SoilGrids REST v2.0 service is reported paused by ISRIC. This is not a defect in Image Vision ML code. | Keep a not_available adapter. Do not fabricate sand/clay/silt/FC/WP. Do not mark SoilGrids operational. | [BUG-0010](bugs/BUG-0010.md) |
| `BUG-0011` | Satellite Explorer map scrolled out of view before Pixel Inspector | code | medium | verified | 2026-10-22T13:53:13Z | 2026-10-22T13:53:13Z | 2026-10-22T13:53:14Z | `ui.satellite_explorer_workspace`, `satellite.pixel_inspector` | Scene Information, SCL Classes, and Pixel Inspector were stacked in a tall sidebar under a 36 rem map card, so scrolling to pixel measurements moved the georeferenced map out of view. | Equal-height CSS Grid workspace with an independently scrolling inspector; Pixel Inspector first; Scene Information and SCL/NDVI legend collapsible. MapLibre sampling and overlay rendering were not changed. | [BUG-0011](bugs/BUG-0011.md) |
| `BUG-0012` | Experiment data fingerprint copied the weather checksum onto features_daily | code | medium | verified | 2026-10-22T18:45:03Z | 2026-10-22T18:47:09Z | 2026-10-22T18:47:21Z | `ml.soil_forecast_experiment` | prepare_experiment wrote features_daily_sha256 from source_fingerprints.daily_weather instead of hashing features_daily.csv. | Hash Phase 4.0 features_daily.csv, targets.csv, split_membership.csv and dataset_manifest.json; repaired the existing experiment artifact without refitting models or touching the 2025 holdout. | [BUG-0012](bugs/BUG-0012.md) |
<!-- BUG_TABLE_END -->
