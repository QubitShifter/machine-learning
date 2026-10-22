---
feature_id: ml.training_run_tracking
name: ML training run tracking
category: ml
status: implemented
mathematical_method: unique run_YYYYMMDDTHHMMSSZ_<hex6> identifiers; isolated run directories; SHA-256 frozen-artifact snapshots
input_datasets:
- plovdiv_soil_forecast_baselines_v1
source_code:
- ml/soil_forecasting/run_registry.py
- ml/soil_forecasting/training_instrumentation.py
- scripts/soil_forecasting_experiment.py
configuration:
- configs/soil_forecasting_experiment.yaml
outputs:
- data/processed/ml/experiments/plovdiv_soil_forecast_baselines_v1/runs/
tests:
- tests/test_training_telemetry.py
- tests/test_training_instrumentation.py
documentation: docs/features/ml/training_run_tracking.md
last_verified: '2026-10-22T20:30:33Z'
related_bugs: []
---

## 1. Feature ID and name

`ml.training_run_tracking` — ML training run tracking.

## 2. Status and version

Status: `implemented`. Telemetry schema `1.0`. Parent scientific pipeline remains `4.1.0`.

## 3. Purpose

Give each explicit research-development training session a unique ID, manifest, and isolated artifact directory without mutating the frozen Phase 4.1 experiment.

## 4. Scientific background

An experiment defines the modeling contract. A run is one execution. Conflating them would mix frozen 2025 holdout results with later development fits.

## 5. Mathematical formula or algorithm

`run_id = run_ + UTC(YYYYMMDDTHHMMSSZ) + _ + token_hex(3)`. Directory creation uses exclusive `mkdir`. Frozen files outside `runs/` are hashed before and after the run.

## 6. Explanation of every variable and unit

UTC is timezone-aware. The hex suffix is 6 lowercase characters. Manifests store sample counts, fingerprints, git commit/dirty, Python and scikit-learn versions, and `test_targets_accessed`.

## 7. Worked numerical example

`run_20261022T202822Z_d188d7` is a completed Ridge h=1 C development run with 350 training rows and 365 validation rows. It is not the frozen Phase 4.1 Ridge artifact.

## 8. Source datasets and provenance

Reads the existing joined modeling frame. Provenance label `telemetry_development_run`. Execution mode `research_development`.

## 9. Input requirements

`joined_modeling_frame.csv` must already exist. `train-run` will not call prepare.

## 10. Processing steps

Create `runs/<run_id>/`, write `run_manifest.json` and `run_config.yaml`, fit on training only, score validation, write artifacts, validate events, assert frozen hashes.

## 11. Implementation paths and functions

`new_run_id`, `create_run_directory`, `snapshot_frozen_artifacts`, `execute_train_run`.

## 12. Configuration parameters

`--model`, `--horizon`, `--feature-set`, `--telemetry` (required), optional `--alpha`, `--max-iter`, `--max-depth`, `--learning-rate`, `--seed`.

## 13. Outputs and units

Gitignored run directories with manifests, summaries, metrics JSON, optional joblib under `model_artifacts/`.

## 14. Validation criteria

IDs unique. Overwrite refused. Frozen checksums unchanged. 2025 test split unused. `suitable_for_modeling` remains false.

## 15. Missing-value handling

Unavailable solver iteration counts are null, not zero, for Ridge.

## 16. Temporal leakage considerations

Features remain D−1. Training-only fitting. No test-target access in this command.

## 17. Tests and expected assertions

`test_run_ids_are_unique_utc_and_collision_resistant`, `test_create_run_directory_refuses_overwrite`, `test_development_run_does_not_access_test_split`.

## 18. Scientific limitations

New runs are not generalization evidence. ERA5-Land targets. 2025 holdout already consulted historically.

## 19. Related feature dependencies

- [`ml.training_event_recorder`](training_event_recorder.md)
- [`ml.soil_forecast_experiment`](soil_forecast_experiment.md)

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T20:30:33Z`
