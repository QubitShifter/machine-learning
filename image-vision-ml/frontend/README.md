# Image Vision ML frontend

Scientific dashboard for the existing FastAPI satellite and weather services. The UI reads processed datasets only. It does not download CDS weather or invent observations.

## Requirements

- Node.js 20 or newer
- npm 10 or newer
- Backend on port 9000

## Installation

```bash
cd /home/gpetrov/projects/machine-learning/image-vision-ml/frontend
npm install
```

## Development

Terminal 1, backend:

```bash
cd /home/gpetrov/projects/machine-learning/image-vision-ml
source .venv/bin/activate
uvicorn backend.app.main:app --reload --port 9000
```

Do not start this while a weather CDS download is writing shared weather files if you need to avoid restarting FastAPI. Overlay rendering does not touch weather data.

Terminal 2, frontend:

```bash
cd /home/gpetrov/projects/machine-learning/image-vision-ml/frontend
npm run dev
```

- Frontend: http://localhost:5173
- Backend: http://localhost:9000
- Swagger UI: http://localhost:9000/api
- OpenAPI JSON: http://localhost:9000/openapi.json

Vite proxies `/api/v1`, `/openapi.json`, and `/health` to port 9000. It does not proxy `/api`.

## Commands

```bash
npm run dev
npm run typecheck
npm test
npm run build
npm run preview
```

## Pages

| Route | Page |
|---|---|
| `/` | Overview, including recent validated satellite scenes |
| `/satellite` | Georeferenced RGB/NDVI map, scene selector, NDVI timeline |
| `/satellite?scene=<id>` | Deep-link a processed acquisition |
| `/satellite?catalog=1` | Include discovered catalog scenes |
| `/integration` | Combined Sentinel-2 + ERA5-Land analytics |
| `/integration?scene=<id>` | Deep-link an integrated acquisition |
| `/weather` | ERA5-Land daily and monthly charts |
| `/quality` | Integrity, validity, completeness, and readiness |
| Predictions | Disabled; soil-moisture modelling is not implemented |

## Map overlay architecture

Satellite Explorer displays processed rasters on MapLibre. It does **not** stretch inspection PNGs (`rgb_preview.png`, `ndvi_preview.png`) onto the AOI.

Pipeline:

1. Open processed `ndvi.tif` / `valid_mask.tif` (EPSG:32635 for the Plovdiv target grid).
2. For RGB, align raw `red_B04.tif`, `green_B03.tif`, `blue_B02.tif` onto that grid and apply the existing display stretch (`clip(reflectance / 0.30, 0, 1)` then gamma `1/2.2`).
3. Reproject source pixels into a north-up EPSG:3857 grid with `rasterio.warp.calculate_default_transform`.
4. Derive the WGS84 envelope from the **rendered** 3857 transform (`west,south,east,north`).
5. Serve a clean RGBA PNG plus MapLibre corner order: top-left, top-right, bottom-right, bottom-left.

Projected easting/northing is never sent to the browser as longitude/latitude.

### Overlay API

- `GET /api/v1/satellite/datasets/{id}/scenes/{scene_id}/map/metadata`
- `GET /api/v1/satellite/datasets/{id}/scenes/{scene_id}/map/rgb`
- `GET /api/v1/satellite/datasets/{id}/scenes/{scene_id}/map/ndvi`
- `GET /api/v1/satellite/datasets/{id}/scenes/{scene_id}/map/ndvi/sample?longitude=&latitude=`

Existing `/rgb` and `/ndvi/preview` inspection images remain for thumbnails only.

### Mask policy

Transparent pixels are those with `valid_mask == 0` or non-finite NDVI. That mask is SCL classes 4 and 5 plus finite reflectance. Cloud, shadow, cirrus, water, and nodata are transparent. Valid dark land is not made transparent just because it is dark.

The black region in the RGB inspection PNG and the white region in the NDVI inspection PNG for `S2A_35TLG_20250718_1_L2A` match the invalid-mask pixels (including SCL class 10 cirrus). They are not raw-band nodata.

### NDVI colormap

Fixed display scale, not per-scene normalized: −1.0 dark red, 0.0 light gray, 0.2–1.0 sequential greens. The map legend uses the same stops. Colorization is display-only.

### Cache

Derived overlays are written under `data/cache/satellite_map/{dataset}/{scene}/map-overlay-v1/{fingerprint}/`. Cache keys include scene identity, source file size/mtime, render version, and mask policy. Writes are atomic. Scientific GeoTIFFs are never overwritten. Delete a scene cache directory to force a rebuild.

## Combined analytics (UI 1.2)

Route: `/integration`. Sidebar label: **Combined Analytics**.

The page reads prepared Phase 3.2 outputs only:

- `GET /api/v1/integration/datasets`
- `GET /api/v1/integration/datasets/{id}`
- `GET /api/v1/integration/datasets/{id}/observations`
- `GET /api/v1/integration/datasets/{id}/quality`
- `GET /api/v1/integration/datasets/{id}/features`

Observation filters (`scene_id`, `start_date`, `end_date`, `window_complete`, `availability`) are honoured by the backend. The UI currently fetches the full small table with the documented 2000-row page size.

Units come from the feature catalog: rainfall and evaporation in mm, temperature in °C, humidity in %, wind in m/s, dry days in days.

UTC lookback: for acquisition UTC date D, features use completed UTC days D−N through D−1. Acquisition-day weather is excluded. Nested 7/14/30-day rainfall totals must not be added together.

Missing values stay `null` / **Unavailable**. They are never drawn as 0 mm. A partial window (for example 23/30 days) remains incomplete. Zero rainfall is shown as `0 mm`.

The scatter plot is exploratory. Points with a null X or Y are omitted; the plotted-pair count is shown. No regression, soil-moisture estimate, or causal claim is displayed.

Deep links: `/integration?scene=<scene_id>` and Satellite Explorer **View weather context** → `/integration?scene=<scene_id>`. Invalid scene IDs show a notice and fall back to the latest complete window.

Refresh reloads integration metadata, observations, quality, and feature definitions. New ERA5-Land months appear only after:

```bash
python -m scripts.weather_dataset integrate --config configs/weather_era5_land.yaml --satellite-dataset plovdiv_2023_2025
```

The frontend does not run that command. `suitable_for_modeling` remaining zero means soil-moisture labels and archive completeness are not ready, not that the page failed.

## Data behaviour

- Counts come from the API.
- Missing weather values stay `null`.
- Scene selector defaults to validated, overlay-ready scenes.
- Combined Analytics defaults to the most recent observation with complete weather windows.
- No NetCDF is loaded in the browser.

## Known UI 1.1 limitations

- Cloud/quality-mask overlay is still omitted; no such image product exists.
- Map tiles come from OpenFreeMap and need outbound network access.
- Overlay placement uses the rendered Mercator rectangle. Visual check against named map features is still recommended after backend geometry tests.
- Pixel inspect samples the processed NDVI GeoTIFF with nearest neighbor; it does not interpolate.
- Daily weather requests paginate through `/daily` with a 2000-row page size.
