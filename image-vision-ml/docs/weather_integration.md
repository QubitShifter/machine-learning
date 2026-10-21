# Phase 3.1 — ERA5-Land Historical Weather Integration

This document describes how `image-vision-ml` acquires Copernicus ERA5-Land hourly meteorology, aggregates it to UTC daily records, quality-controls the result, and joins it with validated Sentinel-2 NDVI observations.

ERA5-Land is a historical reanalysis. It is not a weather forecast and is not used here to predict future meteorological conditions.

## 1. ERA5-Land introduction

ERA5-Land is the land-surface component of the ECMWF ERA5 reanalysis. It provides a regular global grid of near-surface meteorological fields at approximately 0.1° (about 9 km). That is two to three orders of magnitude coarser than the project's Sentinel-2 10 m grid.

Official documentation:

- Copernicus Climate Data Store API: https://cds.climate.copernicus.eu/how-to-api
- ERA5-Land documentation: https://confluence.ecmwf.int/
- Accumulated-variable conversion table: https://confluence.ecmwf.int/display/CKB/Conversion+table+for+accumulated+variables+-+ERA5%3A+data+documentation

## 2. Source product and variables

| Internal output | CDS variable | Native units | Daily product |
|---|---|---|---|
| `temperature_mean_c` / min / max | `2m_temperature` | K | Mean / min / max °C |
| `dewpoint_mean_c` | `2m_dewpoint_temperature` | K | Mean °C |
| `relative_humidity_mean_pct` | derived from T and Td | — | Mean % |
| `precipitation_total_mm` | `total_precipitation` | m, accumulated | UTC-day total mm |
| `wind_speed_mean_ms` | `10m_u_component_of_wind`, `10m_v_component_of_wind` | m/s | Mean of hourly speeds |
| `evaporation_total_mm` | `total_evaporation` | m, accumulated, ECMWF positive-downward | UTC-day total mm, positive upward |

Optional CDS fields (`surface_solar_radiation_downwards`, `skin_temperature`, `potential_evaporation`) are recognised by the configuration schema but are not requested in the default Plovdiv configuration. Soil-water layers are reserved for Phase 3.2.

Dataset identifier: `reanalysis-era5-land` (hourly product). Daily statistics products are not used because they omit accumulated precipitation.

## 3. CDS account and authentication

1. Create a Copernicus CDS account.
2. Accept the ERA5-Land dataset terms on the CDS dataset page.
3. Create `~/.cdsapirc` using the official how-to-API page. The file contains a `url` and a personal `key`.

Example layout (placeholder values only):

```text
url: https://cds.climate.copernicus.eu/api
key: <CDS_PERSONAL_ACCESS_TOKEN>
```

Never commit the token, put it in YAML, print it, or return it from the API. The check command reports only whether the file exists and whether `url`/`key` are present.

```bash
python -m scripts.weather_dataset check --config configs/weather_era5_land.yaml
```

## 4. Data retrieval strategy

Downloads are explicitly opt-in and partitioned by UTC month. Each monthly request also retrieves the following day's 00:00 UTC record so the last calendar day of the month can be closed using the official accumulation convention.

Current CDS request keys used by this project (`data_format`, `download_format`, `area = [North, West, South, East]`) follow the live CDS catalogue. Historical `format` examples are not assumed to remain valid.

The first live test should request only `2025-04`. Do not retrieve the full 2023–2025 archive until that month has been inspected.

A queued CDS job is not a successful download. Failed or interrupted months are recorded as `failed` and can be resumed. Successfully downloaded files are never overwritten.

## 5. Spatial resolution limitations

The small Plovdiv study AOI (`24.65, 42.05, 24.68, 42.08`, west/south/east/north) is about 0.03° across — smaller than one ERA5-Land cell (~0.1°, ~9 km). CDS/MARS rejects a crop that does not contain at least one native grid point (`MultiAdaptorNoDataError`: *Area: non-empty area crop/mask*).

The scientific study AOI is therefore kept separate from the meteorological retrieval box:

- Study AOI (unchanged): `[24.65, 42.05, 24.68, 42.08]`
- CDS `area` (north, west, south, east): `[42.20, 24.50, 41.90, 24.90]`

The same retrieval box is used for monthly files and the next-day 00:00 UTC boundary request. After download, the pipeline selects the **nearest native grid cell to the study AOI centroid** using haversine distance. It does not use the retrieval-box centroid and does not upsample weather to the 10 m Sentinel-2 grid.

Every daily row stores `source_grid_id` and spatial provenance (source longitude/latitude, native resolution, method, query coordinates).

## 6. Temporal conventions

Canonical time is UTC.

- Hourly records have an explicit UTC timestamp.
- Daily rows include `date_utc`, `period_start_utc`, `period_end_utc`, and `timezone = UTC`.
- Europe/Sofia local-day aggregation is not implemented. Bulgaria observes daylight-saving time, so a fixed UTC+2 or UTC+3 offset must not be assumed.

## 7. Precipitation accumulation semantics

ERA5-Land `total_precipitation` and `total_evaporation` are forecast accumulations, not instantaneous rates.

Official UTC-day total:

```text
daily_total_m(D) = value at 00:00 UTC on day D+1
daily_total_mm   = daily_total_m * 1000
```

Do not sum the 24 raw cumulative values. For the sequence 01:00=1 mm, 02:00=3 mm, 03:00=4 mm, the rainfall is 4 mm, not 8 mm.

Hourly increments (used only as a documented fallback in unit tests and diagnostics):

- 01 UTC stores the first-hour increment.
- Later hours are differences from the previous cumulative step.
- A decrease starts a new forecast cycle.

If the next-day 00:00 boundary is missing, the calendar day is marked `requires_review` / incomplete. The pipeline never silently drops the last requested day's rainfall by treating a missing boundary as zero.

## 8. Unit conversions

```text
T_C = T_K - 273.15
precipitation_mm = precipitation_m * 1000
wind_speed = sqrt(u10^2 + v10^2)   # computed hourly, then averaged
RH_pct = 100 * e(Td) / e_sat(T)
```

Relative humidity uses the Magnus–Tetens formula (Alduchov and Eskridge 1996):

```text
e(T) = 6.1094 * exp(17.625 * T / (243.04 + T))     # T in °C, e in hPa
```

Values only 0.05 percentage points outside 0–100 are treated as rounding noise. Larger physically impossible humidities are preserved and flagged.

ECMWF accumulated fluxes are positive downward, so raw evaporation is typically negative. Processed `evaporation_total_mm` reverses that sign so positive values mean water leaving the surface. The reversal is explicit (`EVAPORATION_SIGN = -1.0`).

## 9. Daily aggregation method

For every UTC date in the processed interval the pipeline writes one row. Missing source hours stay `null`. No climatological fill and no zero-fill for absent rainfall.

Instantaneous fields (temperature, dew point, wind speed, derived RH) use the available hourly samples of that UTC day. Accumulated fields use the next-day 00:00 convention.

A complete day requires 24 hourly records and the following 00:00 UTC boundary.

Monthly `YYYY-MM.boundary.nc` files supply that next-day `00:00` UTC closer. When the following month is also downloaded, the same timestamp exists in both files. Matching values are reconciled as an expected boundary overlap; they are not treated as corrupt duplicates. A lone boundary hour is used only to close the previous month (for example 2023-04-01 00:00 closes 2023-03-31). It is not a daily observation of the following month and does not create monthly statistics for a month that was never downloaded.

## 10. Download and resume behaviour

Statuses: `pending`, `submitted`, `downloading`, `downloaded`, `processing`, `processed`, `failed`, `requires_review`.

Resume skips a month when the raw file exists and the stored checksum matches. Partial files from an interrupted retrieve are not promoted to `downloaded`. Dry-run prints the CDS payload and does not contact the network.

Importing weather modules does not perform network I/O. Automated tests mock the CDS client.

## 11. Quality validation

`ml/validation/weather_quality.py` checks:

- timestamp monotonicity, UTC consistency, and unexpected in-file duplicates
- expected month-boundary overlaps (reconciled when measurements match)
- conflicting boundary overlaps (`requires_review`, both values retained)
- expected hourly coverage and missing boundary hours
- source units and temperature conversion
- negative precipitation artefacts versus significant negatives
- ERA5-Land 01 UTC forecast-cycle resets (expected; not a warning)
- unexpected mid-cycle accumulation decreases
- plausible-range warnings for temperature, wind, humidity, and evaporation
- spatial provenance and variable availability
- historical-period completeness, kept separate from source integrity

In the CDS hourly product, `00:00` UTC stores the previous UTC day's accumulated total and `01:00` UTC starts a new forecast accumulation. A drop at 01 UTC is therefore the documented cycle boundary, not missing rainfall. Daily totals continue to use the next-day `00:00` UTC value. Only unexpected mid-cycle decreases or significant negative steps raise `warning` / `requires_review`.

Quality dimensions:

- `source_integrity` — hourly file consistency after expected overlaps are reconciled
- `observation_validity` — validity of days that have observations; days with no source hours are `missing`, not `rejected`
- `period_completeness` — `complete` or `incomplete` against the processed calendar
- `integration_readiness` — `ready`, `limited`, or `not_ready` for unrestricted modelling
- `status` — worst of source integrity and observation validity (existing vocabulary)

Statuses: `valid`, `warning`, `rejected`, `requires_review`, and `missing` for absent source days. Temperature extremes generate warnings rather than automatic rejection. An incomplete three-year archive with valid downloaded months is not labelled corrupt.

Output: `data/processed/weather/<dataset_id>/quality_report.json`.

## 12. Storage layout

```text
data/raw/weather/<dataset_id>/
  manifest.json
  hourly/YYYY-MM.nc            # or .grib if CDS returns GRIB
  hourly/YYYY-MM.boundary.nc   # next-day 00:00 UTC

data/processed/weather/<dataset_id>/
  manifest.json
  daily_weather.csv            # required, no extra engine
  daily_weather.parquet        # optional; written only if pyarrow or fastparquet is installed
  quality_report.json
  monthly_summary.csv
  weather_timeseries.png

data/processed/integration/<satellite_dataset_id>/
  satellite_weather.csv
  satellite_weather.parquet    # optional
  integration_metadata.json
  integration_quality.json
  feature_catalog.json

CSV is the canonical processed table. Parquet is optional and is skipped when no parquet engine is installed. Do not add `pyarrow` unless you want that extra export.
```

GRIB bytes are never renamed to `.nc`. `data/raw/*` and `data/processed/*` remain gitignored.

## 13. Satellite-weather integration

Validated Sentinel-2 scenes are joined to ERA5-Land by study AOI and the acquisition's UTC calendar date. The continuous daily weather table is kept intact. NDVI is not interpolated onto weather-only dates.

One integrated row is produced per unique `scene_id`. Phase 3.1 dropped extra scenes that shared a calendar date; Phase 3.2 keeps distinct scenes acquired on the same UTC date. Duplicate `scene_id` values keep the first occurrence.

### UTC alignment contract

Canonical time is UTC. Sentinel-2 overpass time is preserved in `acquisition_timestamp_utc` when the processed scene metadata includes a datetime. Weather windows never assume the acquisition occurred at midnight.

For an acquisition whose UTC calendar date is **D**:

- Prior-N completed UTC days are **D−N through D−1 inclusive**.
- Acquisition-day weather (date D) is **excluded**, not truncated to hours before overpass. No as-of-time hourly cutoff is implemented.
- Weather from D+1 or later is never used.
- Naive timestamps without a timezone are interpreted as UTC.
- Date-only acquisition metadata still defines D, with `acquisition_time_precision = utc_date`.

A weather day is eligible only when it is a fully completed ERA5-Land UTC day: `quality_status` is not `missing` / `rejected` / `requires_review`, `hourly_records_available = 24` when that field is recorded, and the next-day 00:00 UTC boundary is not recorded as missing. Synthetic tests that omit hourly completeness still use precipitation presence as in Phase 3.1.

Missing daily values stay missing. They are never replaced with zero. A 30-day precipitation total is emitted only when all 30 expected days are present; 12 available days yield a null total plus `window_30d_observed_days = 12` and `window_30d_expected_days = 30`.

### Historical features

- rainfall in the previous 7 / 14 / 30 days (`precip_prev_*_mm`)
- mean temperature in the previous 7 / 30 days
- dry days in the previous 30 days (`precipitation < 1.0 mm`)
- mean RH and wind speed in the previous 7 days
- evaporation totals in the previous 7 / 30 days (`evap_prev_*_mm`), using the same complete-window rule. These are ERA5-Land `total_evaporation` daily millimetres after the documented positive-upward conversion. They are water-balance context, not soil-moisture labels.

Each window records expected, observed, and missing day counts and the UTC start/end dates. Feature definitions are written to `feature_catalog.json` and served at `GET /api/v1/integration/datasets/{id}/features`.

### Quality dimensions

These flags are independent and must not be collapsed into one `valid` field:

- `satellite_observation_valid`
- `weather_observation_valid` (native grid-cell provenance)
- `weather_feature_window_complete` (all 7/14/30 windows complete)
- `integrated_observation_complete`
- `suitable_for_modeling` — additionally requires weather `integration_readiness = ready` and satellite `supervised_soil_forecasting` readiness ready/suitable

A satellite scene remains in the table when its weather months have not been downloaded. Weather features are null and completeness flags are false.

Rerunning `integrate` always recomputes from the current daily weather table and satellite quality files. It does not duplicate `scene_id` rows, does not modify rasters or ERA5-Land NetCDF files, and records source SHA-256 fingerprints so stale outputs are not silently reused after new months are processed.

## 14. CLI commands

```bash
python -m scripts.weather_dataset check --config configs/weather_era5_land.yaml
python -m scripts.weather_dataset status --config configs/weather_era5_land.yaml
python -m scripts.weather_dataset download --config configs/weather_era5_land.yaml --month 2025-04 --dry-run
python -m scripts.weather_dataset download --config configs/weather_era5_land.yaml --month 2025-04
python -m scripts.weather_dataset download --config configs/weather_era5_land.yaml --start-month 2023-01 --end-month 2025-12 --dry-run
python -m scripts.weather_dataset download --config configs/weather_era5_land.yaml --start-month 2023-01 --end-month 2025-12 --resume
python -m scripts.weather_dataset process --config configs/weather_era5_land.yaml --full-period
python -m scripts.weather_dataset validate --config configs/weather_era5_land.yaml
python -m scripts.weather_dataset report --config configs/weather_era5_land.yaml
python -m scripts.weather_dataset integrate --config configs/weather_era5_land.yaml --satellite-dataset plovdiv_2023_2025
```

Historical expansion is sequential and month-by-month. `--dry-run` never contacts CDS. `--resume` skips complete months (including validated April 2025) and never overwrites files whose checksums match. A range download without `--resume` is refused so 35 jobs cannot start by accident. Each month still requests the next-day 00:00 UTC boundary using the expanded retrieval area.

## 15. REST API endpoints

All handlers read local processed files. They do not submit CDS jobs.

- `GET /api/v1/weather/datasets`
- `GET /api/v1/weather/datasets/{dataset_id}`
- `GET /api/v1/weather/datasets/{dataset_id}/daily`
- `GET /api/v1/weather/datasets/{dataset_id}/summary`
- `GET /api/v1/weather/datasets/{dataset_id}/quality`
- `GET /api/v1/weather/datasets/{dataset_id}/chart`
- `GET /api/v1/weather/datasets/{dataset_id}/satellite-integration`
- `GET /api/v1/integration/datasets`
- `GET /api/v1/integration/datasets/{dataset_id}`
- `GET /api/v1/integration/datasets/{dataset_id}/observations`
- `GET /api/v1/integration/datasets/{dataset_id}/quality`
- `GET /api/v1/integration/datasets/{dataset_id}/features`

The integration routes read prepared CSV/JSON only. They do not open rasters or NetCDF files. Filesystem paths are not returned. The weather `satellite-integration` route remains as a compact compatibility view.

Existing satellite routes and Swagger UI at `/api` are unchanged. UI contracts for a future combined analytics page are in `docs/integration_ui_1.2.md`.

## 16. Tests

Weather tests are offline. They use temporary directories, synthetic hourly fixtures, and a mocked CDS retrieve function. They do not require `~/.cdsapirc` or network access.

## 17. Known limitations

- Live CDS retrieval depends on an account, a token, and dataset-term acceptance. Those are not stored in the repository.
- ERA5-Land jobs can remain queued for a long time.
- One 9 km ERA5-Land cell represents the entire Plovdiv test AOI; weather features are not 10 m fields.
- UTC days do not coincide with Europe/Sofia civil days.
- Evaporation sign reversal follows ECMWF's documented positive-downward convention; users comparing with other products must read the metadata.
- Optional radiation / skin-temperature / potential-evaporation fields are not in the default request.
- Soil-moisture labels and supervised soil-moisture training remain out of scope. Phase 3.2 produces an observational join, not a training-ready soil-moisture dataset.
- Evaporation window totals are historical water-balance context from ERA5-Land. They are not in-situ evapotranspiration measurements.

## 18. Requirements for future forecasting models

The weather table is a historical covariate source. Training features must continue to use only information available before the prediction time. Do not train a soil-moisture or NDVI forecast against same-day or future ERA5-Land fields. Do not treat ERA5-Land as an operational forecast service. `suitable_for_modeling` stays false while the weather archive is incomplete or satellite supervised-soil-forecasting readiness is not ready, even if some scenes have complete 30-day windows.
