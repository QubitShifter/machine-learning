# Training telemetry

Research instrumentation for isolated soil-forecasting training runs. Last reviewed: `2026-10-22T20:30:33Z`.

This is **not** live monitoring. There are no WebSockets, background workers, automatic retraining, or operational `/predict` endpoints. GET APIs never start training.

## Architecture

| Concept | Meaning |
|---|---|
| Experiment | Scientific objective and frozen Phase 4.1 configuration (`plovdiv_soil_forecast_baselines_v1`). |
| Run | One explicit `train-run` execution with its own directory and ID. |
| Event | One JSONL record of something that actually occurred. |
| Metric | A numbered result with partition, unit, method, and whether it was an optimization objective. |
| Artifact | A file written under `runs/<run_id>/` (manifest, events, diagnostics, optional joblib). |

New runs **do not** overwrite frozen experiment files. They read `joined_modeling_frame.csv` and write only under `data/processed/ml/experiments/<experiment_id>/runs/<run_id>/` (gitignored via `data/processed/*`).

Code:

- `ml/soil_forecasting/telemetry.py` — schema 1.0, `EventWriter`, JSONL validation
- `ml/soil_forecasting/run_registry.py` — run IDs, exclusive directories, manifests
- `ml/soil_forecasting/training_instrumentation.py` — `execute_train_run`
- `scripts/soil_forecasting_experiment.py` — `train-run`
- Read-only API in `backend/app/api/ml.py` and `backend/app/services/ml_service.py`

## Run identification

Format: `run_YYYYMMDDTHHMMSSZ_<6 hex chars>`, for example `run_20261022T202822Z_d188d7`.

UTC creation time is in the ID. Uniqueness also uses `secrets.token_hex(3)`. The ID is stable after directory creation. Collision on `mkdir` is rejected.

## Schema version

Event and run-manifest `schema_version` is `1.0`. Pipeline version of the parent experiment remains `4.1.0`. Telemetry does not bump the scientific pipeline.

## Event JSONL

File: `training_events.jsonl`. One JSON object per line. Writer: single owner, append, flush + `fsync`. Completed runs are immutable. Readers skip an incomplete final line instead of inventing an event.

Required fields: `schema_version`, `run_id`, `sequence`, `timestamp_utc`, `elapsed_ms`, `event_type`, `phase`.

- `timestamp_utc` is timezone-aware UTC (`…Z`).
- `elapsed_ms` comes from `time.monotonic()`, not wall-clock subtraction.
- Sequence numbers strictly increase from 1.
- Metric values must be finite. Secret-looking keys are rejected.

## Lifecycle

Statuses: `created` → `preparing` → `training` → `validating` → `saving` → `completed`. Any non-terminal state may go to `failed`. Invalid transitions are rejected. A missing writer lock on a non-terminal run is inferred as `interrupted` by readers; training is not resumed.

A completed run requires a valid manifest, `run_completed`, event-log integrity, and `telemetry_validation.json` with `ok: true`. Failed runs emit `run_failed` and must not be shown as completed.

## Measurement methodology

Wall-clock stage timings use the monotonic clock. Separate keys may include dataset loading, validation, feature preparation, split verification, fitting, validation prediction, metric calculation, artifact serialization, and total run duration. CPU time and RAM are not collected.

## Metric semantics

Optimization objectives stay separate from evaluation metrics.

- Ridge minimizes regularized squared error. Reported MAE/RMSE/R²/skill are **evaluation** metrics.
- Histogram gradient boosting minimizes squared error. Stagewise `training_mse` from `staged_predict` after fit is labeled `calculation_method=staged_predict_after_fit` and `used_for_fitting=false`. Native `train_score_` is empty because `early_stopping=False`.
- Persistence and seasonal models have no training loss.

Validation MAE is not plotted as training loss.

## Algorithm limitations

| Algorithm | Recorded | Not recorded |
|---|---|---|
| Persistence | Lifecycle, sample counts, duration, validation metrics | Iterations, optimizer, loss curve |
| Seasonal | Monthly means, group counts, missing months, duration | Optimization curve |
| Ridge | Alpha, solver, scaler, coefficients, fit duration, train/val evaluation metrics | Epoch loss (`iteration_history_available=false`, reason `not_exposed_by_estimator`) |
| HGBR | `n_iter_`, hyperparameters, early-stopping=false, post-fit staged training MSE | Native `train_score_` / randomized early-stopping validation |

Do not enable sklearn randomized early stopping on a chronological training partition merely to draw a validation curve. Do not swap Ridge for SGD to invent epochs.

## Frozen artifact protection

`train-run` snapshots SHA-256 of experiment files outside `runs/` before work and asserts they are unchanged after. It never calls `prepare`, `train`, `validate`, `compare`, or `evaluate-test`. It never partitions `split=="test"` and refuses 2025 issue dates in development partitions.

## CLI

```bash
.venv/bin/python -m scripts.soil_forecasting_experiment train-run \
  --config configs/soil_forecasting_experiment.yaml \
  --model ridge --horizon 1 --feature-set C --telemetry
```

`--telemetry` is required. Default mode is `research_development` / `telemetry_development_run`. Training does not start on application boot or GET.

## API

Read-only, bounded, deterministic order:

- `GET /api/v1/ml/experiments/{id}/runs`
- `GET /api/v1/ml/experiments/{id}/runs/{run_id}`
- `GET /api/v1/ml/experiments/{id}/runs/{run_id}/events`
- `GET /api/v1/ml/experiments/{id}/runs/{run_id}/metrics`
- `GET /api/v1/ml/experiments/{id}/runs/{run_id}/artifacts`

Filters: model, horizon, feature set, status, start date, limit. Events: type, phase, `sequence_after`, limit ≤ 2000. Empty run lists are `[]`, not errors. Run IDs are validated; path traversal and symlink escapes return 404. Joblib is listed, never deserialized. Absolute private paths are stripped.

## Security

Safe IDs, resolve-under-root checks, no secret fields, no arbitrary file download, no training side effects.

## Testing

```bash
.venv/bin/python -m pytest tests/test_training_telemetry.py tests/test_training_instrumentation.py backend/tests/test_ml_api.py
```

## Future streaming

A later phase could tail `training_events.jsonl` or add SSE. This phase stores history only. Do not describe the UI as live monitoring.
