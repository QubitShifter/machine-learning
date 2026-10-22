# Soil-moisture model baselines (Phase 4.1)

Companion to [`agricultural_forecasting_mathematics.md`](agricultural_forecasting_mathematics.md).
This document describes the models actually fitted in experiment
`plovdiv_soil_forecast_baselines_v1`. Labels are ERA5-Land **modeled** volumetric
soil water (`swvl1`, 0–7 cm), not field-sensor observations.

Pipeline version: `4.1.0`. Last reviewed: `2026-10-22T19:26:01Z`.

The read-only **ML Training Lab** at `/ml/training` displays these artifacts. See [`ml_training_laboratory.md`](ml_training_laboratory.md). Educational simulations on that page are not experiment telemetry.

## 1. Persistence

\[
\hat\theta_{D+h}=\theta_{D-1}
\]

No coefficients. The last complete historical daily mean is reused for every horizon.
Derived change \(\hat\theta_{D+h}-\theta_{D-1}\) is identically zero. Persistence is the
benchmark. Skill is defined only against this model on the **same rows**.

## 2. Training-year seasonal reference

\[
\hat\theta_{D+h}=\mu_{\mathrm{train},\,month(D+h)}
\]

\(\mu_{\mathrm{train},m}\) is the mean of training-partition absolute targets whose
**target date** falls in calendar month \(m\). Validation and test labels are never used.
This is a single-year monthly reference, not a climatology. February 29 uses February’s
training mean when month 2 exists; otherwise the prediction is null.

## 3. Ridge regression

\[
\hat y=\beta_0+\sum_{j=1}^{p}\beta_j x_j
\]

with L2 penalty \(\alpha\|\beta\|_2^2\). Implementation: `StandardScaler` then `Ridge`,
both fitted on the **training** partition only. No imputation; incomplete selected
windows are dropped. Alpha is chosen from \(\{0.01,0.1,1,10,100\}\) by validation MAE.

## 4. Gradient boosting

`HistGradientBoostingRegressor` on the same complete-case predictors. Small grid over
`max_depth` ∈ {2,3}, `learning_rate` ∈ {0.05,0.1}, `max_iter` ∈ {50,100}, seed 42,
`early_stopping=false`. Selected by validation MAE. One training year is not a licence
for deep trees.

## 5. Absolute and derived-change targets

The trained target is \(y_{D,h}=\bar\theta_{D+h}\). Derived change uses the same D−1
baseline as persistence. Change MAE equals absolute MAE under that transformation and
is not a second independent win.

## 6. Validation-only selection and 2025 holdout

Fit on 2023 training rows (horizon-aware purge respected). Select on 2024. Freeze
`frozen_experiment.json`. Evaluate 2025 **once** without refitting. Repeats preserve the
original `final_test_metrics.csv`. A changed config fingerprint invalidates the freeze.

## 7. Skill

\[
\mathrm{Skill}_{MAE}=1-\frac{\mathrm{MAE}_{model}}{\mathrm{MAE}_{persistence}}
\]

If persistence MAE is 0 and the model is not perfect, skill is null.

## 8. Physical range

Predictions are **not** clipped before scoring. Counts of \(\hat\theta<0\), \(\hat\theta>1\),
nonfinite values, and \(|\hat\theta-\theta_{D-1}|>0.15\) are reported. 0–1 is a generic
volumetric bound, not field capacity.

## 9. Interpretation

ERA5-Land weather and soil share modeling ancestry. Skill on this dataset is not
independent field skill and is not operational forecast skill. Coefficients describe
associations in the reanalysis, not proven irrigation causality.

Worked issue example: 10 April 2024, h=1. Features may use soil and weather through
9 April only. The target is the daily mean on 11 April. Persistence predicts the
9 April swvl1 mean.
