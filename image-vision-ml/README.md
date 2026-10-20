# Image Vision ML

A modular machine-learning and computer-vision platform for satellite and drone imagery. The first application area is environmental observation. Predictive soil models are not implemented yet.

## Current capabilities

- Local Sentinel-2 scene processing (reflectance, SCL mask, NDVI, RGB preview)
- REST API for a single registered scene (`first_image`)
- Historical Sentinel-2 discovery, limited windowed download, shared-grid processing and NDVI time series
- Multi-year (2023–2025) dataset configuration, projected footprint filtering, quality gates, and training-readiness reports

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

```bash
curl http://localhost:9000/health
curl http://localhost:9000/api/v1/satellite/images
curl http://localhost:9000/api/v1/satellite/datasets
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
python -m scripts.satellite_dataset validate --config configs/satellite_multiyear.yaml
python -m scripts.satellite_dataset report --config configs/satellite_multiyear.yaml
```

Search does not download rasters. Keep `--limit` small unless you intend a larger archive.

## Tests

```bash
pytest
```

## Documentation

- `docs/sentinel2_calibration_validation.md`
- `docs/satellite_timeseries.md`
- `docs/satellite_multiyear_dataset.md`
- `docs/architecture.md`
- `docs/roadmap.md`
