# UI Phase 1.2 — Satellite + Weather Analytics (contracts only)

UI Phase 1.2 is implemented. The page consumes the Phase 3.2 integration API and does not invent soil-moisture values, model scores, or predictive correlation results.

## Route

`/integration?scene={scene_id}`

Navigation:

- Sidebar item **Combined Analytics**, between Satellite Explorer and Weather Analytics.
- From Satellite Explorer, **View weather context** links to `/integration?scene={activeSceneId}` when an integration row exists.
- From Weather Analytics, **Combined analytics** opens the same page.

Keep Predictions disabled until a later phase.

## API contracts

Typed FastAPI/Pydantic resources (all read-only, prepared outputs only):

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/integration/datasets` | Discover integrated collections |
| GET | `/api/v1/integration/datasets/{id}` | Metadata, leakage policy, completeness counts |
| GET | `/api/v1/integration/datasets/{id}/observations` | One row per validated scene |
| GET | `/api/v1/integration/datasets/{id}/quality` | Independent quality dimensions and issues |
| GET | `/api/v1/integration/datasets/{id}/features` | Feature definitions, units, window rule |
| GET | `/api/v1/satellite/datasets/{id}/scenes/{scene_id}/map/metadata` | Existing georeferenced overlay |
| GET | `/api/v1/satellite/datasets/{id}/scenes/{scene_id}/quality` | Scene NDVI/cloud quality |

Observation filters: `scene_id`, `start_date`, `end_date`, `window_complete`, `availability=complete|incomplete|missing`, `offset`, `limit`.

Missing weather features are JSON `null`, never `0`. Incomplete windows must remain visually distinct from complete ones (`connectNulls: false` on charts, same rule as Weather Analytics).

Do not request raw GeoTIFF or ERA5-Land NetCDF from the browser. Do not display filesystem paths.

## Suggested page layout

1. **Acquisition selector** — validated scenes only, labelled with UTC timestamp and satellite quality status. Selecting a scene updates the URL `scene` parameter so Satellite Explorer and this page share identity.
2. **Map thumbnail** — reuse `SatelliteMap` RGB/NDVI overlay for the selected scene. Mean NDVI from the integrated row, with min/max if present. Show valid-pixel % and cloud/shadow metrics.
3. **Preceding rainfall** — three values: 7 / 14 / 30-day precipitation totals. If `window_*d_complete` is false, render the value as **Incomplete** and show `observed_days / expected_days` plus the UTC window `[start, end]`. Do not draw a filled bar that looks like zero rain.
4. **Temperature and humidity context** — prior 7- and 30-day mean temperature, 7-day RH, 7-day wind. Same incomplete treatment.
5. **Optional evaporation** — 7- and 30-day totals, labelled as ERA5-Land water-balance context, not in-situ ET.
6. **Timeline comparison** — sparse NDVI points (one per scene) over the daily precipitation series for the weather dataset. NDVI is not a daily series; connect NDVI points only as a visual aid and label the chart **exploratory**. Do not fit a regression or print an R².
7. **Quality strip** — five separate badges: satellite observation valid, weather observation valid, weather feature window complete, integrated observation complete, suitable for modeling. Incomplete feature windows must be prominent.
8. **Provenance** — weather grid longitude/latitude, distance to AOI centroid, source dataset IDs, integration version. No file paths.

## What not to show

- Soil-moisture predictions or “estimated SM”.
- Correlation or skill metrics presented as results.
- Filled-in rainfall for missing months.
- Any indication that eight scenes are a training set.

The current satellite archive is sparse. Any visual relationship between NDVI and preceding weather is exploratory context for analysts, not a predictive finding.

## Frontend types

Types live in `frontend/src/types/integration.ts`, mirroring the FastAPI/Pydantic contracts. The client is `frontend/src/services/integration.ts`. Vite already proxies `/api/v1`; no extra proxy paths were added.
