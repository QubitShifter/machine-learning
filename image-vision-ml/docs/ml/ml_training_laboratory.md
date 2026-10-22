# ML Training Laboratory

Research UI for inspecting stored Phase 4.1 soil-moisture forecasting experiments and for teaching the mathematics of the fitted algorithms. Route: `/ml/training`. Sidebar label: **ML Training Lab**.

Last reviewed: `2026-10-22T20:30:33Z`.

Visiting the page **does not train models**. GET requests are read-only. Educational simulations are labeled and are not experiment telemetry.

## Page purpose

The laboratory is a scientific and educational dashboard for:

1. Real experiment metadata from `data/processed/ml/experiments/{experiment_id}/`.
2. Training, validation, and test sample counts.
3. Model comparison on stored metrics.
4. Training-process status from artifact presence.
5. Mathematical explanations of persistence, seasonal baseline, Ridge, gradient descent (educational), and histogram gradient boosting.
6. Client-side educational demonstrations.
7. Residual and forecast-versus-target charts from stored predictions.
8. Reproducibility and research-readiness flags.
9. **Training Runs**: separately recorded research-development telemetry, historical playback, and run comparison. This is not live monitoring.

It is not an operational forecast console. Predictions navigation remains disabled.

## Data sources

Experiment `plovdiv_soil_forecast_baselines_v1`, pipeline `4.1.0`, dataset `plovdiv_agricultural_ml_2023_2025` v4.0.0.

| UI value | Source |
|---|---|
| Experiment list / freeze / test-evaluated | `experiment_summary.json`, `frozen_experiment.json`, `final_test_metrics.csv` presence |
| Sample counts | `prepared_summary.json` `counts` |
| Feature catalog | `feature_selection.json` |
| Selected models, seed, timestamps | `frozen_experiment.json`, `training_summary.json` |
| Validation metrics | `model_comparison.csv` |
| Test metrics | `final_test_metrics.csv` |
| Prediction series | `selected_validation_predictions.csv` or `final_test_predictions.csv` |
| Ridge coefficients | joblib under `models/` (load only, no fit) |
| Seasonal monthly means | seasonal JSON artifacts |
| Provenance | freeze, fingerprint, training git/versions |
| Training telemetry | `training_events.jsonl` if present; otherwise unavailable |

Chronological years 2023 / 2024 / 2025 are the Phase 4.0 holdout convention recorded in the experiment snapshot. Target: ERA5-Land modeled `swvl1` (0–7 cm). Unit: m³/m³. Not field-sensor measurements.

## Algorithms

Displayed only when present in the frozen `selected` list:

- Persistence: \(\hat\theta_{D+h}=\theta_{D-1}\). No fit.
- Training-year seasonal monthly mean of 2023 targets. Not climatology.
- Ridge: `StandardScaler` then `Ridge` linear-system solver. Not gradient-descent epochs.
- Histogram gradient boosting: `HistGradientBoostingRegressor` stagewise trees. Not neural backpropagation.

Feature set D (satellite) is listed as **not trained**.

## Mathematical explanations

The Algorithms tab states the prediction formula, what is learned, and the optimizer. Gradient descent is a separate educational card: \(\theta\leftarrow\theta-\eta\nabla L\). It is not how Phase 4.1 Ridge was fitted.

The Mathematics tab has synthetic demos (fixed seeds):

- Ordinary least squares on noisy points.
- Gradient descent on \(L(w)=(w-3)^2\).
- Ridge on two correlated synthetic features.
- Sequential stumps on synthetic step data.

Banner: **Educational simulation — not training telemetry from the agricultural model.**

## Training, validation, and test

- Training (2023): complete-case rows used to fit scalers, seasonal means, Ridge, and boosting.
- Validation (2024): hyperparameter selection by MAE. Coefficients are not refit on validation.
- Test (2025): frozen holdout scored once. Shown only when `test_evaluated` is true.

Random shuffling is not used. Leakage is any information unavailable at issue time 00:00 UTC (features stop at D−1). Preprocessors are training-only. Missing rainfall is never filled with 0.

## Training telemetry limitations

The frozen Phase 4.1 experiment still has **no** `training_events.jsonl` in its root. The Training Process tab shows:

**Training history unavailable — this experiment recorded final metrics but not per-iteration telemetry.**

Final MAE is never reconstructed into a loss curve for that frozen evaluation. Persistence and seasonal models have no epochs. Ridge used a linear-system solver. Boosting stages were not logged on the original freeze. `live_training` is always false. No job control.

### Training Runs tab

Phase 4.1-Telemetry adds isolated development runs under `runs/<run_id>/`. The Training Runs tab lists those runs, shows a timeline from recorded events, plots only stored metric points, and offers **Historical training playback**. Missing histories are explained per algorithm. See [`training_telemetry.md`](training_telemetry.md).

Educational Mathematics demos remain labeled **Educational simulation — not training telemetry from the agricultural model.** Real Ridge coefficients and HGBR `n_iter_` from a telemetry run are shown on Training Runs, not mixed into the synthetic GD demo.

## Evaluation metrics

MAE, RMSE, bias, R², skill \(1-\mathrm{MAE}_{model}/\mathrm{MAE}_{persistence}\) on matched rows. Lower MAE/RMSE is better; higher skill is better. The optimization objective may differ (Ridge/HGBR squared error vs reported MAE).

Interpretation lines are derived from the loaded metric table, not hardcoded winners. For the stored 2025 C holdout the artifacts show persistence lowest MAE at 1 and 3 days and a small Ridge skill at 7 days. Seasonal is weak. Gradient boosting did not consistently beat persistence. These are ERA5-Land modeled-target results only.

## Educational simulations

Client-side only. No backend training. Seeds are fixed or slider-controlled. Do not treat demo MSE, coefficients, or trees as agricultural evidence.

## Scientific limitations

- `research_reanalysis`
- `operational_availability_verified=false`
- `is_ground_truth=false`
- `suitable_for_modeling=false`
- `operational_forecast=false`

Trained research models do not change these flags. Weather and soil share ERA5-Land ancestry. One training year is not climatology. Validation/test differences are not proof of a single cause such as overfitting. No irrigation advice. No `/predict`.

## API contracts

Read-only. Experiment IDs are sanitized; path escape returns 404. Local source directories and environment variables are stripped.

- `GET /api/v1/ml/experiments`
- `GET /api/v1/ml/experiments/{id}`
- `GET /api/v1/ml/experiments/{id}/metrics?partition=validation|test`
- `GET /api/v1/ml/experiments/{id}/predictions` (`horizon_days`, `model_id`, `feature_set`, `limit` ≤ 2000)
- `GET /api/v1/ml/experiments/{id}/dataset`
- `GET /api/v1/ml/experiments/{id}/features`
- `GET /api/v1/ml/experiments/{id}/training`
- `GET /api/v1/ml/experiments/{id}/provenance`
- `GET /api/v1/ml/experiments/{id}/runs`
- `GET /api/v1/ml/experiments/{id}/runs/{run_id}`
- `GET /api/v1/ml/experiments/{id}/runs/{run_id}/events`
- `GET /api/v1/ml/experiments/{id}/runs/{run_id}/metrics`
- `GET /api/v1/ml/experiments/{id}/runs/{run_id}/artifacts`

Unavailable telemetry and missing files are explicit states, not zeros.

## Testing instructions

```bash
.venv/bin/python -m pytest backend/tests/test_ml_api.py tests/test_soil_forecasting_experiment.py tests/test_agricultural_ml_dataset.py
cd frontend && npm test && npm run typecheck && npm run build
```

Frontend laboratory tests cover experiment load, sample counts, horizon filter, validation/test selection, missing telemetry, feature set D unavailable, algorithm explanations, synthetic demo labeling, empty artifacts, and API errors. Demo unit tests cover OLS, seeded linear data, quadratic GD convergence/divergence, Ridge L2 shrinkage, and boosting MSE drop.

Do not claim live-browser verification unless `/ml/training` was opened at desktop and mobile widths against the running API.
