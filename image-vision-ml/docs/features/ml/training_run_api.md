---
feature_id: ml.training_run_api
name: Read-only training-run API
category: ml
status: implemented
mathematical_method: safe-ID validation; resolve-under-root; bounded JSONL pagination
input_datasets:
- plovdiv_soil_forecast_baselines_v1
source_code:
- backend/app/api/ml.py
- backend/app/services/ml_service.py
- backend/app/schemas/ml.py
configuration:
- configs/soil_forecasting_experiment.yaml
outputs:
- GET /api/v1/ml/experiments/{id}/runs
tests:
- backend/tests/test_ml_api.py
documentation: docs/features/ml/training_run_api.md
last_verified: '2026-10-22T20:30:33Z'
related_bugs: []
---

## 1. Feature ID and name

`ml.training_run_api` — Read-only training-run API.

## 2. Status and version

Status: `implemented`. FastAPI on port 9000. No training side effects.

## 3. Purpose

Expose stored run metadata, events, metrics, and artifact names to the Training Laboratory.

## 4. Scientific background

Researchers inspect recorded fits. GET must not refit models or deserialize pickle payloads in request handlers.

## 5. Mathematical formula or algorithm

`run_dir = resolve(experiments_root / experiment_id / runs / run_id)` must remain under `experiments_root / experiment_id / runs`. Symlinks are rejected.

## 6. Explanation of every variable and unit

Query filters: `model`, `horizon_days`, `feature_set`, `status`, `start_date`, `limit` (1–500). Events: `event_type`, `phase`, `sequence_after`, `limit` (1–2000).

## 7. Worked numerical example

An experiment with no `runs/` directory returns `{total: 0, runs: []}`. Invalid `../` IDs return 404.

## 8. Source datasets and provenance

Reads `run_manifest.json`, `training_events.jsonl`, `metrics.json`. Does not read test prediction CSVs for these endpoints.

## 9. Input requirements

Valid `experiment_id` (`SAFE_ID_PATTERN`) and `run_id` (`run_YYYYMMDDTHHMMSSZ_<hex6>`).

## 10. Processing steps

Locate experiment, list run dirs skipping symlinks, sanitize payloads (drop absolute paths), paginate events.

## 11. Implementation paths and functions

`list_training_runs`, `training_run_detail`, `training_run_events`, `training_run_metrics`, `training_run_artifacts`.

## 12. Configuration parameters

`EXPERIMENTS_ROOT = data/processed/ml/experiments`.

## 13. Outputs and units

JSON schemas in `backend/app/schemas/ml.py`. Artifact listing includes names and sizes; `deserializable=false`.

## 14. Validation criteria

No GET training. No joblib load. Path traversal 404. Empty list not an error. Research flags false.

## 15. Missing-value handling

Missing runs 404. Missing event file yields empty events. Truncated JSONL last line omitted.

## 16. Temporal leakage considerations

These endpoints do not score 2025. They return stored development-run validation metrics only.

## 17. Tests and expected assertions

`test_training_run_api_list_detail_events_metrics_and_filters`, `test_training_run_api_rejects_invalid_ids_and_escapes`, GET `/runs` does not rewrite files.

## 18. Scientific limitations

No live streaming. No artifact binary download. Displayed metrics are not operational skill.

## 19. Related feature dependencies

- [`ml.training_run_tracking`](training_run_tracking.md)
- [`ui.training_run_laboratory`](../ui/training_run_laboratory.md)

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T20:30:33Z`
