# Development Roadmap

## Phase 1 - Project Foundation

- [x] Create project structure
- [x] Create FastAPI application
- [ ] Configure Git
- [x] Configure Python environment

## Phase 2 - Data Ingestion

- [x] Download a first Sentinel-2 window
- [x] Discover historical Sentinel-2 scenes from Earth Search STAC
- [x] Download a limited multi-date AOI archive
- [x] Build a validated multi-year Sentinel-2 dataset with quality gates
- [x] Retrieve historical weather data
- [ ] Retrieve soil data
- [x] Store geospatial metadata and dataset manifests

## Phase 3 - Image Processing

- [x] Read GeoTIFF imagery
- [x] Extract image bands
- [x] Calculate NDVI with verified reflectance calibration
- [x] Apply SCL quality masks
- [x] Align multi-date scenes to a shared grid
- [x] Build a descriptive NDVI time series
- [x] Monthly, yearly, and interannual NDVI summaries
- [x] Join satellite NDVI with leakage-safe historical weather features
- [ ] Generate training features

## Phase 4 - Model Development

- [ ] Soil moisture baseline
- [ ] Vegetation forecasting
- [ ] Drought classification
- [ ] Erosion risk estimation
- [ ] Soil degradation indicators

## Phase 5 - Application

- [x] Satellite analysis and time-series endpoints
- [x] ERA5-Land weather dataset endpoints
- [x] Web interface
- [x] Geographical map
- [x] Georeferenced RGB/NDVI map overlays
- [x] Visualization dashboard
- [x] Combined Sentinel-2 + ERA5-Land analytics page

## Phase 6 - Advanced AI

- [ ] Vision Transformers
- [ ] Temporal Transformers
- [ ] Multimodal fusion
- [ ] Future image simulation
