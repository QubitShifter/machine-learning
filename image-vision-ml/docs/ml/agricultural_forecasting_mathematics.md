# Agricultural forecasting mathematics (Phase 4.0)

This note is the central mathematical reference for the leakage-safe research dataset
`plovdiv_agricultural_ml_2023_2025`. It describes conventions used by
`ml/agricultural_ml/`. It is not a trained model and does not report agricultural skill.

Pipeline version: `4.0.0`. Last reviewed: `2026-10-22T17:14:17Z`.

## 1. Issue time

A research prediction issued on calendar day \(D\) is stamped at the start of that UTC day:

\[
t_D = \text{00:00 UTC on } D
\]

At \(t_D\), the last eligible completed daily observation is \(D-1\). Day \(D\) itself is still
incomplete at midnight, so rainfall, temperature, evaporation and soil moisture from \(D\) are
forbidden in features.

This is a **research historical cutoff**. It uses ERA5-Land observation dates. It is not proof that
the reanalysis product had been published at \(t_D\). Publication timestamps are unknown, so every
row stores `operational_availability_verified=false`.

Worked example: issue date 10 April 2024.

- `issue_time_utc` = 2024-04-10T00:00:00Z
- `last_observation_date_utc` = 2024-04-09
- `feature_cutoff_time_utc` = 2024-04-10T00:00:00Z

## 2. Daily lag operator

Write \(X_{D-i}\) for the complete UTC daily value of variable \(X\) on day \(D-i\).
The lag operator never includes \(D\) or later:

\[
L^i X_D = X_{D-i},\qquad i \ge 1
\]

Implementation: `ml.integration.satellite_weather.prior_window_dates` and
`ml.agricultural_ml.time_semantics.last_observation_date`.

## 3. Rolling windows

For window length \(N \in \{1,3,7,14,30\}\) the eligible dates are \(D-N,\ldots,D-1\).

Mean (used for soil moisture and temperature):

\[
\bar{X}^{(N)}_D = \frac{1}{N}\sum_{i=1}^{N} X_{D-i}
\]

Sum (used for precipitation and evaporation):

\[
S^{(N)}_D = \sum_{i=1}^{N} X_{D-i}
\]

If any of the \(N\) days is missing, incomplete, or invalid, the feature is **null**. The pipeline
does not average over a shorter window and still call it an \(N\)-day feature.

Worked example, issue 10 April 2024, previous 7-day rainfall:

- Eligible days: 3, 4, 5, 6, 7, 8, 9 April 2024
- 10 April rainfall is excluded
- 11 April rainfall is excluded

In the deterministic fixture that sets precipitation equal to the calendar day-of-month,
\(P_7=3+4+5+6+7+8+9=42\) mm. Including 10 April would yield 52 mm and is treated as leakage.

## 4. Soil-moisture history

Layers: swvl1 (0–7 cm), swvl2 (7–28 cm), swvl3 (28–100 cm), swvl4 (100–289 cm),
and the existing 0–100 cm profile mean

\[
\theta_{0-100}=0.07\theta_1+0.21\theta_2+0.72\theta_3
\]

Layer 4 is excluded from that profile. Previous-day change:

\[
\Delta\theta_{\mathrm{prev1}}(D)=\theta_{D-1}-\theta_{D-2}
\]

Slope over a complete \(N\)-day window (\(N\in\{3,7,14\}\)):

\[
\mathrm{slope}^{(N)}_D=\frac{\theta_{D-1}-\theta_{D-N}}{N-1}
\]

## 5. Antecedent precipitation index

The stored wetness API is an **end-of-day** quantity:

\[
\mathrm{API}_t = P_t + k\,\mathrm{API}_{t-1}
\]

with \(k\in\{0.85,0.90,0.95\}\) and \(\mathrm{API}_0=0\). Missing \(P_t\) makes \(\mathrm{API}_t\)
and all later values null. Warm-up is 30 valid days.

For a beginning-of-day issue at \(t_D\), the eligible API is the end-of-day value on \(D-1\):

\[
\mathrm{API}(D)=\mathrm{API}_{D-1}
\]

Joining API by the issue calendar date would include \(P_D\) and is leakage. Columns record
`api_k090_mm_source_date_utc = D-1`.

## 6. Persistence of soil moisture

The persistence baseline for every horizon \(h\) is the last completed historical state:

\[
\hat{\theta}_{D+h}=\theta_{D-1}
\]

It is **not** \(\theta_D\). Coefficients are not fitted in Phase 4.0. The value is stored as
`persistence_prediction` on each target row for later scoring.

## 7. Soil-moisture change

Absolute target (daily mean of the complete UTC day \(D+h\)):

\[
y_{D,h}=\bar{\theta}_{D+h}
\]

Change target, using the same depth and units:

\[
\Delta\theta_{D,h}=\bar{\theta}_{D+h}-\bar{\theta}_{D-1}
\]

The baseline is \(D-1\), not \(D\).

## 8. Forecast target horizons

\[
h\in\{1,3,7\}
\]

Target period for the daily mean of \(D+h\):

- start (inclusive): \(D+h\) 00:00 UTC
- end (exclusive): \(D+h+1\) 00:00 UTC

This is a daily mean state, not an instantaneous midnight value.

Worked example, issue 10 April 2024:

| Horizon | Target date | Period |
|---|---|---|
| 1 | 11 April 2024 | [2024-04-11T00:00:00Z, 2024-04-12T00:00:00Z) |
| 3 | 13 April 2024 | [2024-04-13T00:00:00Z, 2024-04-14T00:00:00Z) |
| 7 | 17 April 2024 | [2024-04-17T00:00:00Z, 2024-04-18T00:00:00Z) |

If the archive ends 31 December 2025, an issue on 30 December 2025 has a complete \(h=1\) target
and a missing \(h=7\) target with reason `future_target_outside_dataset_period`. Fake values are
not created.

ERA5-Land targets are modeled reanalysis: `target_source_kind=modeled_reanalysis`. They are not
independent ground truth.

## 9. Seasonal calendar features

Known at issue time and therefore permitted:

\[
d_{\sin}=\sin\left(2\pi\frac{d-1}{L}\right),\qquad
d_{\cos}=\cos\left(2\pi\frac{d-1}{L}\right)
\]

where \(d\) is the day of year of the **issue date** and \(L=366\) in leap years (2024) else 365.
1 March 2024 has \(d=61\); 1 March 2023 has \(d=60\).

## 10. Chronological splitting and purging

Random train/test splits are forbidden. Initial holdout:

| Partition | Issue-date period |
|---|---|
| Training | 2023-01-01 … 2023-12-31 |
| Validation | 2024-01-01 … 2024-12-31 |
| Test | 2025-01-01 … 2025-12-31 |

A training label must not fall in the validation target period. For horizon 7, issue 25 December 2023
has target date 1 January 2024 and is `excluded_purge`. Issue 24 December 2023 has target 31 December 2023
and remains training.

Validation features may use December 2023 weather and soil as historical context. That is not leakage.
The restriction is on **future** information and on **labels** crossing the next partition.

Warm-up rows in early January 2023 lack a 30-day history and stay in the table with null window
features and `history_window_complete=false`.

## 11. Error metrics (contracts only)

\[
\mathrm{MAE}=\frac{1}{N}\sum_i |y_i-\hat{y}_i|
\]

\[
\mathrm{RMSE}=\sqrt{\frac{1}{N}\sum_i (y_i-\hat{y}_i)^2}
\]

\[
\mathrm{MBE}=\frac{1}{N}\sum_i (\hat{y}_i-y_i)
\]

\[
R^2=1-\frac{\sum_i (y_i-\hat{y}_i)^2}{\sum_i (y_i-\bar{y})^2}
\]

If the denominator of \(R^2\) is zero: return 1 when residuals are also zero, otherwise null.
These functions are tested on fixtures. Fixture numbers are not agricultural skill.

## 12. Skill versus persistence

\[
\mathrm{Skill}=1-\frac{\mathrm{MAE}_{\mathrm{model}}}{\mathrm{MAE}_{\mathrm{persistence}}}
\]

Positive: better than persistence. Zero: equal. Negative: worse. If persistence MAE is 0 and model
MAE is not, skill is null rather than undefined or infinite.

Moisture-change metrics are separate from absolute-moisture metrics. Wetting/drying direction uses a
configurable tolerance around \(\Delta\theta=0\).

## 13. Satellite recency

Sentinel-2 is optional. A scene is eligible only when quality is `valid`, calibration is `verified`,
and acquisition time precedes \(t_D\). Date-only timestamps are treated as not available at 00:00 UTC
on the acquisition date. NDVI is never invented on unobserved days and is never unbounded forward-filled.
If age exceeds `max_age_days` (default 14; 30 is an alternate research policy, not an optimum), NDVI
fields are null and `satellite_stale=true`.

## 14. Phase 4.1 model baselines

Trained persistence, training-year seasonal, Ridge and gradient-boosting experiments are documented
in [`soil_forecasting_model_baselines.md`](soil_forecasting_model_baselines.md). Those models predict
ERA5-Land **modeled** `swvl1` and are labeled `research_reanalysis`. They are not operational
forecasts and are not independently validated field predictions.
