# Scientific decision log — Phase 4.0 agricultural ML dataset

Assumptions and design choices for `plovdiv_agricultural_ml_2023_2025`. These are not verified
empirical findings. Last reviewed: `2026-10-22T17:14:17Z`.

## Issue cutoff is D 00:00 UTC

A conservative daily research convention. At midnight UTC on day \(D\), the UTC day \(D\) has not
ended, so its daily mean precipitation, temperature, evaporation and soil moisture are not complete.
Using \(D-1\) as the latest eligible observation matches the existing Sentinel-2 weather window
`D-N … D-1`.

This cutoff is **not** an ERA5-Land publication time.

## D−1 is the latest completed daily observation

ERA5-Land daily totals in this repository already use complete UTC days with the next-day 00:00
boundary. The ML dataset reuses those daily rows. Same-day incomplete soil moisture is never a
feature.

## ERA5-Land targets are modeled

swvl1–4 are reanalysis volumetric soil water, not in-situ probes. `target_source_kind` is
`modeled_reanalysis`. `is_ground_truth` remains false. The existing observation-level flag
`suitable_for_modeling` stays false; it is the supervised field-forecasting gate from earlier
phases and is not flipped because a research table exists.

## Satellite variables are optional

The archive has 15 validated Sentinel-2 observations, two calibration-review scenes, and one
rejected January 2025 scene. Filling every historical day with NDVI would fabricate observations.
Experiment A (weather + soil history) is the primary daily table. Experiment B adds recency
features where a quality-gated scene precedes the cutoff and is not older than `max_age_days`.
Fourteen days is a research policy, not an optimum.

Acquisition timestamps in the quality report are often date-only. Date-only scenes are not treated
as available at 00:00 UTC on the acquisition date. Operational satellite availability is unverified.

## Random train/test splitting is forbidden

Daily soil moisture and weather are serially correlated. Overlapping 1-, 3- and 7-day targets would
leak across random folds. The initial design is a chronological holdout: 2023 train, 2024
validation, 2025 test. Three calendar years are not statistically robust generalization.

## Training targets cannot cross split boundaries

A 7-day target issued on 25 December 2023 uses 1 January 2024 soil moisture. If that row stayed in
training, validation labels would contaminate training. Horizon-aware purging marks such rows
`excluded_purge`. Historical context may still look backward across a boundary.

## Operational availability is unverified

ERA5-Land publication/delivery times were not independently verified. No publication delays were
invented. Mode `research_reanalysis` is the default. `operational_replay` and
`perfect_weather_hindcast` are named but not enabled. Rows must not be labeled operationally
deployable.

## Perfect-weather hindcasts stay separate

Using future realized meteorology would measure an oracle, not an operational forecast. Phase 4.0
does not emit those rows in the default dataset.

## No models are trained in this phase

Baselines (persistence, training-only seasonal mean, rainfall-memory linear form) are contracts.
Evaluation metrics are implemented on fixtures. Descriptive correlations in
`dataset_diagnostics.json` are flagged as not skill and must not be reused as fitted preprocessing
parameters.

# Scientific decision log — Phase 4.1 soil-forecasting baselines

Assumptions for experiment `plovdiv_soil_forecast_baselines_v1`. Last reviewed: `2026-10-22T18:47:21Z`.

## Satellite timestamps stay out of training

Quality-report scenes do not carry `acquisition_datetime`. The dataset synthesizes midnight UTC from
date-only strings. Feature set D remains disabled. That is a provenance exclusion, not a finding that
satellite NDVI is uninformative.

## `plovdiv_test` is the canonical AOI ID

It matches the study AOI registry. Source weather, soil and satellite archives were not rewritten.

## Catalog completeness is required before fitting

`temp_mean_prev_7d_c` and `day_of_year_cos` were present in the Phase 4.0 table but missing from the
catalog. They were documented in `catalog.py` before any model used them. Undocumented predictors
remain forbidden.

## Persistence is the scientific benchmark

A learned model is useful on this dataset only if it beats \(\hat\theta_{D+h}=\theta_{D-1}\) on matched
rows. One training year of monthly means is a `training_year_seasonal_reference`, not a climatology.

## Validation may select; 2025 may not

Ridge alpha and boosting grids are chosen on 2024 MAE. The 2025 holdout is scored once after freeze.
Repeats preserve the original test record. Re-running `compare` after the holdout is consulted is
forbidden.

## Weather features are historical only

Feature set C uses rainfall, API, temperature and evaporation through \(D-1\). Future rainfall subsets
in error analysis are retrospective diagnostics, not model inputs.

## Negative or mixed transfer is a valid result

Modest 2024 Ridge skill did not hold at h=1 and h=3 on 2025. That does not license enlarging the
search after inspecting the test year. Independent soil-sensor labels would be a different scientific
question.

## Static soil properties remain unavailable

Soil texture, bulk density, SOC, elevation, slope, land cover and crop identity appear in the
agricultural source registry but are not ingested. Columns exist as null with status `unavailable`.
