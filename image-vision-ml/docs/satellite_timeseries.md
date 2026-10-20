# Satellite Time-Series Analysis

Descriptive historical NDVI analysis for local Sentinel-2 datasets. This is not a soil-moisture, drought, or degradation forecast.

## 1. Architecture

```text
YAML config
    -> STAC search (no rasters)
    -> windowed COG download
    -> shared-grid processing
    -> scene statistics
    -> chronological NDVI series
    -> FastAPI read endpoints
```

Reusable modules:

- `ml/ingestion/stac.py` — catalog search
- `ml/ingestion/download.py` — restartable AOI windows
- `ml/ingestion/manifest.py` — atomic dataset status
- `ml/preprocessing/raster.py` — local processing
- `ml/preprocessing/grid.py` — canonical target grid
- `ml/analysis/timeseries.py` — temporal aggregation
- `scripts/satellite_dataset.py` — CLI
- `backend/app/api/satellite.py` — read/process status API

## 2. Data sources

Earth Search STAC (`https://earth-search.aws.element84.com/v1`), collection `sentinel-2-l2a`. Only Cloud-Optimized GeoTIFF windows over the configured bbox are downloaded.

## 3. Scene discovery

`search_sentinel2()` queries bbox, date range and scene-level cloud cover. Pagination is consumed fully. Duplicate item IDs are removed. Results are sorted by acquisition time. Scene-level `eo:cloud_cover` is stored separately from AOI footprint overlap; they are not the same quantity. Phase 2.4 also computes projected polygon intersection (`footprint_overlap_pct`) and keeps bbox overlap as a separate diagnostic.

## 4. Geographic alignment

Every processed observation in a dataset is warped to one target grid:

- CRS from configuration (default EPSG:32635)
- bounds snapped outward to the target resolution
- fixed width, height and affine transform

Continuous bands use bilinear resampling. SCL uses nearest neighbour. Pixels outside a scene footprint become nodata and are not treated as valid observations.

## 5. Reflectance calibration

See `docs/sentinel2_calibration_validation.md`. The resolver uses `earthsearch:boa_offset_applied` so Earth Search COGs are not double-offset. Pixel-statistic heuristics no longer rewrite coefficients; ambiguous scenes are flagged for review.

## 6. SCL masking

Default accepted classes: 4 (vegetation) and 5 (not vegetated). Classes are configurable. Negative calibrated reflectance is retained; NDVI is undefined only when the denominator is near zero.

## 7. Dataset storage

```text
data/raw/satellite/{dataset_id}/manifest.json
data/raw/satellite/{dataset_id}/scenes/{scene_id}/
data/processed/satellite/{dataset_id}/scenes/{scene_id}/
data/processed/satellite/{dataset_id}/timeseries/
```

`first_image` is unchanged and is not a time-series dataset.

## 8. Manifest structure

Each scene record stores identifier, acquisition time, cloud cover, AOI coverage, source URLs, status, checksums, retry count and errors. Statuses: discovered, downloading, downloaded, processing, processed, failed, skipped. Failed downloads are never marked complete.

## 9. CLI commands

```bash
python -m scripts.satellite_dataset search --config configs/satellite_timeseries.yaml
python -m scripts.satellite_dataset download --config configs/satellite_timeseries.yaml --limit 5
python -m scripts.satellite_dataset download --config configs/satellite_timeseries.yaml --limit 5 --dry-run
python -m scripts.satellite_dataset process --config configs/satellite_timeseries.yaml
python -m scripts.satellite_dataset timeseries --config configs/satellite_timeseries.yaml
python -m scripts.satellite_dataset validate --config configs/satellite_timeseries.yaml
```

Search does not download rasters. Download is limited and restartable.

## 10. API endpoints

Existing `/api/v1/satellite/images...` routes are unchanged.

New routes:

- `GET /api/v1/satellite/datasets`
- `GET /api/v1/satellite/datasets/{dataset_id}`
- `GET /api/v1/satellite/datasets/{dataset_id}/scenes`
- `GET /api/v1/satellite/datasets/{dataset_id}/timeseries/ndvi`
- `GET /api/v1/satellite/datasets/{dataset_id}/timeseries/ndvi/chart`
- `GET /api/v1/satellite/datasets/{dataset_id}/timeseries/ndvi/monthly`
- `GET /api/v1/satellite/datasets/{dataset_id}/timeseries/ndvi/yearly`
- `GET /api/v1/satellite/datasets/{dataset_id}/timeseries/ndvi/comparison`
- `GET /api/v1/satellite/datasets/{dataset_id}/quality`
- `POST /api/v1/satellite/datasets/{dataset_id}/process`

Acquisition remains a CLI operation. The process endpoint only works on already-downloaded scenes.

## 11. Time-series calculations

Observations are sorted by date. Duplicate dates keep the higher valid-pixel percentage. Consecutive change is `NDVI_later - NDVI_earlier`. Monthly means use only observed months. Missing months are listed, never interpolated. Partial AOI coverage is flagged and is not treated as a full-area mean.

A decline in NDVI is not interpreted as drought or soil degradation.

## 12. Known limitations

- Scene cloud cover is not the cloudy fraction inside the AOI.
- Earth Search calibration flags can still contradict stored COG values; those scenes require review instead of a silent offset rewrite.
- Unit tests mock STAC; a live download is a separate integration step.
- Overlapping tiles on the same date are not mosaicked.

Phase 2.4 adds projected footprint filtering, quality gates, and the `plovdiv_2023_2025` configuration. See `docs/satellite_multiyear_dataset.md`.

## 13. Recommended next steps

- Optional mosaic of same-day overlapping tiles
- Weather and soil covariates
- Predictive models after a longer verified archive exists
