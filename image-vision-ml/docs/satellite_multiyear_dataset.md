# Multi-Year Sentinel-2 Dataset

Phase 2.4 builds a validated historical Sentinel-2 archive for the Plovdiv test AOI. The archive is intended for later meteorological and soil-moisture integration. It is not a forecast product.

## Architecture

```text
YAML config
    -> STAC search (no rasters)
    -> projected footprint filter
    -> stratified seasonal selection
    -> windowed COG download
    -> shared-grid processing
    -> scene quality gates
    -> monthly / yearly / interannual NDVI
    -> training-readiness report
    -> FastAPI read endpoints
```

Reusable modules:

- `ml/ingestion/stac.py` — catalog search and projected footprint intersection
- `ml/ingestion/selection.py` — seasonally distributed scene selection
- `ml/ingestion/download.py` — restartable AOI windows
- `ml/preprocessing/calibration.py` — documented reflectance policy
- `ml/preprocessing/grid.py` — canonical target grid
- `ml/validation/dataset_quality.py` — scene and dataset quality gates
- `ml/validation/coverage.py` — monthly discovery vs validation coverage
- `ml/validation/calibration_audit.py` — scene calibration evidence without rewriting coefficients
- `ml/validation/modeling_readiness.py` — task-specific readiness and exclusion reasons
- `ml/ingestion/expansion.py` — local dry-run expansion preview
- `ml/analysis/timeseries.py` — chronological, monthly, yearly, and interannual NDVI
- `scripts/satellite_dataset.py` — CLI
- `backend/app/api/satellite.py` — read/process status API

## Multi-year configuration

`configs/satellite_multiyear.yaml` defines dataset `plovdiv_2023_2025`:

- Period: 2023-01-01 to 2025-12-31
- AOI bbox: `[24.65, 42.05, 24.68, 42.08]` in EPSG:4326
- Target CRS: EPSG:32635 at 10 m
- Discovery cloud cover: 30%
- Minimum geometric footprint overlap: 95%
- Quality: `min_aoi_coverage_pct=95`, `min_valid_ndvi_pct=70`, `calibration_policy=verified_only`

These thresholds are configurable starting values, not universal scientific standards. The older `configs/satellite_timeseries.yaml` (`plovdiv_2025`) remains valid.

## STAC discovery

`search_sentinel2()` queries Earth Search `sentinel-2-l2a` by bbox, date range, and scene-level cloud cover. Pagination is consumed fully. Duplicate STAC item IDs are removed. Search does not download rasters.

Scene identity stores STAC ID, acquisition timestamp, platform, MGRS tile, processing baseline, collection, asset hrefs, geometry, bbox overlap, and footprint overlap. Two tiles on the same day remain two observations.

## Footprint filtering

Bounding-box overlap is stored separately from polygon coverage.

```text
footprint_overlap_pct = 100 * intersection_area / aoi_area
```

Areas are computed in the configured projected CRS (default EPSG:32635). Degree units are not used as area. Adjacent MGRS tile `34TGM` can overlap the AOI bounding box and still have 0% polygon coverage.

A geometric pass does not make a scene scientifically valid. Actual raster coverage is measured after preprocessing.

## Calibration policy

See `docs/sentinel2_calibration_validation.md`.

Documented rule:

```text
reflectance = DN * scale + offset
```

- `earthsearch:boa_offset_applied=true` → scale from `raster:bands`, offset `0`
- `earthsearch:boa_offset_applied=false` → advertised scale and offset
- Missing flag → unverified, `requires_review`
- Missing scale and missing flag → processing error
- Pixel-statistic heuristics never rewrite coefficients

Negative reflectance after a documented conversion is retained. A majority-negative result after a negative advertised offset is recorded as a discrepancy and flagged for review.

## Spatial alignment

The target grid is derived once from the configured AOI and stored in the processed manifest. Continuous bands use bilinear resampling. SCL uses nearest neighbour. `validate_dataset_grid(dataset_id)` reports CRS, width, height, and affine mismatches. Changing the grid after processing requires `--force` and invalidates incompatible outputs.

## Download strategy

Downloads are limited, restartable, checksum-verified, and interrupt-safe. Incomplete scenes are never marked complete. Dry-run reports selected IDs, coverage, and an approximate byte estimate.

Default selection is stratified by year and meteorological season (DJF, MAM, JJA, SON). It does not rank solely by lowest cloud cover. The first live test should request at most nine scenes (about three seasons per year).

Raw files are immutable after a successful download.

## Storage

```text
data/raw/satellite/plovdiv_2023_2025/
    manifest.json
    scenes/<scene_id>/{blue_B02,green_B03,red_B04,nir_B08,scl}.tif
    scenes/<scene_id>/{metadata,calibration}.json

data/processed/satellite/plovdiv_2023_2025/
    manifest.json
    scenes/<scene_id>/{ndvi.tif,valid_mask.tif,rgb_preview.png,ndvi_preview.png,statistics.json,quality_report.json}
    timeseries/{ndvi_observations.csv,ndvi_monthly.csv,ndvi_observations.json,ndvi_timeseries.png,ndvi_by_year.png}
    quality/{dataset_quality.json,dataset_quality.csv,training_readiness.json,coverage_report.png}
```

`first_image` and `plovdiv_2025` keep their existing layouts.

## Quality gates

Scene statuses: `valid`, `warning`, `rejected`, `requires_review`.

Examples:

- Unverified or conflicting calibration → `requires_review`
- Missing raster or CRS mismatch → `rejected`
- Valid NDVI below the warning threshold → `warning`
- Valid NDVI below the rejection threshold or geometric coverage below threshold → `rejected`

Warnings are not automatic failures. Exclusion reasons are stored. Partial-AOI scenes are flagged and excluded from full-coverage series unless the config says otherwise.

## Temporal aggregation

Missing months stay missing. Absent observations are not treated as NDVI = 0. Monthly and yearly summaries weight each scene equally; they are not pixel-area-weighted climatologies. Interannual charts share a calendar-month axis. Charts: `ndvi_timeseries.png`, `ndvi_by_year.png`, `coverage_report.png`.

## Dataset validation and training readiness

`training_readiness.json` reports readiness for:

1. Historical satellite analysis
2. Vegetation forecasting research
3. Supervised soil forecasting

The third category remains `not_ready` until weather covariates and soil-moisture labels exist. A multi-year NDVI record is not a soil-moisture training set.

## API endpoints

Existing image and dataset routes are unchanged. Added:

- `GET /api/v1/satellite/datasets/{dataset_id}/quality`
- `GET /api/v1/satellite/datasets/{dataset_id}/scenes/{scene_id}/quality`
- `GET /api/v1/satellite/datasets/{dataset_id}/timeseries/ndvi/monthly`
- `GET /api/v1/satellite/datasets/{dataset_id}/timeseries/ndvi/yearly`
- `GET /api/v1/satellite/datasets/{dataset_id}/timeseries/ndvi/comparison`
- `GET /api/v1/satellite/datasets/{dataset_id}/quality/report`

Acquisition remains a CLI operation.

## CLI usage

```bash
python -m scripts.satellite_dataset search --config configs/satellite_multiyear.yaml
python -m scripts.satellite_dataset download --config configs/satellite_multiyear.yaml --limit 9 --dry-run
python -m scripts.satellite_dataset download --config configs/satellite_multiyear.yaml --limit 9
python -m scripts.satellite_dataset download --config configs/satellite_multiyear.yaml \
  --scene-id S2B_35TLG_20230609_0_L2A --dry-run
python -m scripts.satellite_dataset process --config configs/satellite_multiyear.yaml
python -m scripts.satellite_dataset validate --config configs/satellite_multiyear.yaml
python -m scripts.satellite_dataset timeseries --config configs/satellite_multiyear.yaml
python -m scripts.satellite_dataset report --config configs/satellite_multiyear.yaml
python -m scripts.satellite_dataset candidates --config configs/satellite_multiyear.yaml
python -m scripts.satellite_dataset candidates --config configs/satellite_multiyear.yaml --refresh-stac
```

`search` does not download imagery. `validate` and `report` work offline against local datasets. Repeatable `--scene-id` selects exact catalog records and skips stratified `--limit` ranking. Already downloaded checksum-verified scenes are skipped. Process without `--force` reuses unchanged NDVI outputs.

## Testing strategy

Unit tests use mocked STAC items and synthetic rasters. They do not require internet access and do not modify existing raw archives. Coverage includes footprint geometry, calibration provenance, quality gates, monthly/yearly aggregation, and the new API routes.

## Observed limited acquisition (2026-10-20)

These are measured results from a nine-scene stratified sample, not the full 2023–2025 archive.

- STAC scenes after cloud and 95% footprint filters: **645**
- Downloaded / processed: **9 / 9**
- Validated: **8**
- Requires review: **1** (`S2B_34TGM_20250208_0_L2A` — advertised BOA offset produced majority-negative reflectance; coefficients were not rewritten)
- Rejected: **0**
- Canonical grid: EPSG:32635, 10 m, 258 × 341, transform origin (305520, 4661340)
- Grid consistency: all nine processed scenes matched
- Valid NDVI coverage of the nine processed scenes: mean 96.5%, median 97.6%
- Validated NDVI means: 2023-02 0.408, 2023-03 0.425, 2023-07 0.595, 2024-02 0.365, 2024-04 0.673, 2024-07 0.579, 2025-04 0.593, 2025-07 0.580
- Training readiness: historical analysis `suitable_for_exploratory_analysis`; vegetation research `limited`; supervised soil forecasting `not_ready`

Some MGRS `34TGM` items have a true polygon overlap with this AOI and produced valid pixels. The Phase 2.3 failure (`S2C_34TGM_20250203_0_L2A`) remains the bbox-only false-positive case covered by tests.

## Phase 2.5 controlled expansion (2026-10-21)

A second batch added eight catalog 35TLG scenes chosen for missing seasons, not for lowest cloud cover. Stratified `--limit` ranking would have re-selected the original nine scenes, so download now accepts repeatable `--scene-id`.

- Candidates requested: **8**; downloaded: **8**; failed downloads: **0**
- Processed onto the existing EPSG:32635 10 m grid: **8 new + 9 reused**
- Newly validated: **7**
- Newly requires review: **1** (`S2C_35TLG_20250308_0_L2A` — conflicting BOA offset; coefficients were not rewritten)
- Dataset totals: catalog **645**, downloaded/processed **17**, validated **15**, requires review **2**, rejected **0**
- Previous NDVI GeoTIFF hashes for the original nine scenes were unchanged
- Longest validated gap: 285 days → 210 days
- Validated coverage by year: 2023 **5**, 2024 **6**, 2025 **4**
- SON is now represented in 2023, 2024 and 2025
- Phase 3.2 integration: **8 → 15** rows; complete weather windows **4 → 7**; modeling-ready still **0**
- Incomplete precipitation totals remain null, including 2024-06, 2024-09, 2025-06 and 2025-09

Refresh integration after validation with:

```bash
python -m scripts.weather_dataset integrate --config configs/weather_era5_land.yaml --satellite-dataset plovdiv_2023_2025
```

Do not run that command from the UI. Additional ERA5-Land months appear in the integrated table only after they are downloaded, processed, and this command is rerun.

## Phase 3.3 coverage, calibration, and task readiness (2026-10-22)

Phase 3.3 adds diagnostics. It does not regenerate the archive, train models, or download a new historical batch.

### Historical coverage methodology

Monthly coverage is computed from observed acquisition dates. It does not interpolate missing months. For each YYYY-MM in 2023-01 through 2025-12 the report stores:

- discovered candidate scenes, or `null` when discovery evidence is missing
- ingested / validated / requires-review / rejected counts
- available acquisition dates
- AOI cloud/shadow summary when a processed SCL mask exists
- a coverage status that distinguishes: no scene discovered; discovered but not downloaded; downloaded but not processed; processed but rejected; requires calibration review; validated observation; unknown discovery evidence

Unknown discovery is never written as zero. Dataset-quality JSON now includes `coverage`, and `data/processed/plovdiv_2023_2025/quality/coverage.json` is written by `validate`.

### Calibration consistency

`verified_only` is unchanged. A plausible or even finite NDVI value does not promote a scene to `valid`. Authoritative STAC scale/offset and `earthsearch:boa_offset_applied` remain the calibration source. Pixel statistics never rewrite coefficients.

The two unresolved scenes after Phase 2.5 remain `requires_review` unless new source metadata is added:

| Scene | Date | Evidence |
|---|---|---|
| `S2B_34TGM_20250208_0_L2A` | 2025-02-08 | Advertised BOA offset with majority-negative optical reflectance; stored NDVI range is physically implausible |
| `S2C_35TLG_20250308_0_L2A` | 2025-03-08 | Same class of Earth Search offset conflict on the native 35TLG tile |

Audit output: `quality/calibration_audit.json`. Processing baselines are copied from stored metadata and are not inferred from scene IDs.

### Candidate selection and safe expansion

`python -m scripts.satellite_dataset candidates` is a local dry-run. Default behaviour does not contact STAC and does not download COGs.

Selection order:

1. Months without a validated observation
2. Months in the longest observation gaps
3. Under-represented seasons
4. Native MGRS `35TLG` when catalog evidence exists
5. Skip already ingested `scene_id`s

Scene-level `eo:cloud_cover` is recorded but is not treated as AOI clear-pixel fraction. Missing months are allowed to have no scientifically acceptable candidate. `--refresh-stac` is the opt-in live catalog refresh. Actual ingestion still requires an explicit `download --scene-id` command.

### Exploratory analysis vs forecasting readiness

Task assessments live in `task_readiness` and are separate from observation-level `suitable_for_modeling`.

| Task | Meaning |
|---|---|
| `exploratory_ndvi_analysis` | Small valid NDVI sample on a consistent grid |
| `weather_ndvi_relationship_analysis` | Leakage-safe complete satellite–weather pairs |
| `vegetation_forecasting` | `limited` until density, years, gap, and calibration meet the project forecast gates; `ready` only for a validated forecasting dataset |
| `supervised_soil_forecasting` | Requires measured soil-moisture labels. NDVI is not a substitute |

Operational thresholds are in `readiness` config defaults (`ml/ingestion/config.py`). They are project gates, not universal remote-sensing standards.

`suitable_for_modeling` still means supervised soil-forecasting eligibility:

```text
integrated_complete
and weather integration_readiness is ready
and satellite supervised_soil_forecasting is ready
```

Inspect exclusion reasons at:

- `GET /api/v1/satellite/datasets/{id}/quality` → `task_readiness.by_task`
- `GET /api/v1/integration/datasets/{id}/quality` → `task_readiness` after `weather_dataset integrate`

### 2023–2025 baseline vs this phase

The observational baseline after ingesting `S2B_35TLG_20250119_0_L2A` is 18 processed scenes, 15 validated, two calibration-review scenes (`S2B_34TGM_20250208_0_L2A`, `S2C_35TLG_20250308_0_L2A`), and one rejected January 2025 scene. The January rejection is a valid-NDVI threshold decision (`BUG-0005`), not a reason to lower gates. Pixel exclusions are accounted on the 10 m target grid (`BUG-0004`). Soil-forecasting remains `not_ready`. This archive does not claim 100% monthly coverage and does not add fabricated observations.

Equations, implementation paths, and tests: [`feature_registry.md`](feature_registry.md).

## Known limitations

- STAC footprints can overstate usable raster coverage.
- Scene-level `eo:cloud_cover` is not the cloudy fraction inside the AOI.
- Earth Search calibration metadata can contradict stored COG encoding; those scenes are reviewed, not silently recoded.
- Same-day overlapping tiles are classified, not mosaicked.
- Monthly means are observation-weighted, not an unbiased month-long average.
- Three years of NDVI cannot support climate-change or soil-degradation inference.
