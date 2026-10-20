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
python -m scripts.satellite_dataset process --config configs/satellite_multiyear.yaml
python -m scripts.satellite_dataset validate --config configs/satellite_multiyear.yaml
python -m scripts.satellite_dataset timeseries --config configs/satellite_multiyear.yaml
python -m scripts.satellite_dataset report --config configs/satellite_multiyear.yaml
```

`search` does not download imagery. `validate` and `report` work offline against local datasets.

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

## Known limitations

- STAC footprints can overstate usable raster coverage.
- Scene-level `eo:cloud_cover` is not the cloudy fraction inside the AOI.
- Earth Search calibration metadata can contradict stored COG encoding; those scenes are reviewed, not silently recoded.
- Same-day overlapping tiles are classified, not mosaicked.
- Monthly means are observation-weighted, not an unbiased month-long average.
- Three years of NDVI cannot support climate-change or soil-degradation inference.
