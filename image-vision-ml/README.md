# Image Vision ML

A modular machine-learning and computer-vision platform for satellite and drone imagery. The first application area is environmental observation. Predictive soil models are not implemented yet.

## Current capabilities

- Local Sentinel-2 scene processing (reflectance, SCL mask, NDVI, RGB preview)
- REST API for a single registered scene (`first_image`)
- Historical Sentinel-2 discovery, limited windowed download, shared-grid processing and NDVI time series
- Multi-year (2023–2025) dataset configuration, projected footprint filtering, quality gates, and training-readiness reports
- ERA5-Land hourly retrieval, UTC daily weather aggregation, quality reports, and leakage-safe satellite-weather features
- Daily weather tables are written as CSV; Parquet export is optional and requires `pyarrow` or `fastparquet`

## Setup

```bash
cd /home/gpetrov/projects/machine-learning/image-vision-ml
source .venv/bin/activate
pip install -e ".[dev,ml]"
```

## API

```bash
uvicorn backend.app.main:app --reload --port 9000
```

Swagger UI: http://localhost:9000/api
OpenAPI JSON: http://localhost:9000/openapi.json

## Web UI

```bash
cd /home/gpetrov/projects/machine-learning/image-vision-ml/frontend
npm install
npm run dev
```

The dashboard is at http://localhost:5173 and proxies `/api/v1` to the FastAPI process on port 9000. See `frontend/README.md` for pages, tests, and data-integrity notes.

```bash
curl http://localhost:9000/health
curl http://localhost:9000/api/v1/satellite/images
curl http://localhost:9000/api/v1/satellite/datasets
curl http://localhost:9000/api/v1/weather/datasets
```

## Historical dataset CLI

```bash
python -m scripts.satellite_dataset search --config configs/satellite_timeseries.yaml
python -m scripts.satellite_dataset download --config configs/satellite_timeseries.yaml --limit 5 --dry-run
python -m scripts.satellite_dataset download --config configs/satellite_timeseries.yaml --limit 5
python -m scripts.satellite_dataset process --config configs/satellite_timeseries.yaml
python -m scripts.satellite_dataset timeseries --config configs/satellite_timeseries.yaml
python -m scripts.satellite_dataset search --config configs/satellite_multiyear.yaml
python -m scripts.satellite_dataset download --config configs/satellite_multiyear.yaml --limit 9 --dry-run
python -m scripts.satellite_dataset download --config configs/satellite_multiyear.yaml --scene-id S2B_35TLG_20230609_0_L2A --dry-run
python -m scripts.satellite_dataset validate --config configs/satellite_multiyear.yaml
python -m scripts.satellite_dataset report --config configs/satellite_multiyear.yaml
python -m scripts.satellite_dataset candidates --config configs/satellite_multiyear.yaml
```

Search does not download rasters. Keep `--limit` small unless you intend a larger archive.

## Historical weather CLI

CDS credentials live in `~/.cdsapirc` and are never stored in this repository. Check authentication before requesting data. The first live download should be a single month.

```bash
python -m scripts.weather_dataset check --config configs/weather_era5_land.yaml
python -m scripts.weather_dataset status --config configs/weather_era5_land.yaml
python -m scripts.weather_dataset download --config configs/weather_era5_land.yaml --month 2025-04 --dry-run
python -m scripts.weather_dataset download --config configs/weather_era5_land.yaml --start-month 2023-01 --end-month 2025-12 --dry-run
python -m scripts.weather_dataset download --config configs/weather_era5_land.yaml --start-month 2023-01 --end-month 2025-12 --resume
python -m scripts.weather_dataset process --config configs/weather_era5_land.yaml
python -m scripts.weather_dataset validate --config configs/weather_era5_land.yaml
python -m scripts.weather_dataset report --config configs/weather_era5_land.yaml
python -m scripts.weather_dataset integrate --config configs/weather_era5_land.yaml --satellite-dataset plovdiv_2023_2025
```

## Tests

```bash
pytest
```

## Documentation

- `docs/sentinel2_calibration_validation.md`
- `docs/satellite_timeseries.md`
- `docs/satellite_multiyear_dataset.md`
- `docs/weather_integration.md`
- `docs/architecture.md`
- `docs/roadmap.md`
