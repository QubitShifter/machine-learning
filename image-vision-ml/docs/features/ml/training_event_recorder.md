---
feature_id: ml.training_event_recorder
name: Training event recorder
category: ml
status: implemented
mathematical_method: append-only JSONL; strictly increasing sequence; monotonic elapsed_ms
input_datasets:
- plovdiv_soil_forecast_baselines_v1
source_code:
- ml/soil_forecasting/telemetry.py
configuration:
- configs/soil_forecasting_experiment.yaml
outputs:
- training_events.jsonl
- telemetry_validation.json
tests:
- tests/test_training_telemetry.py
documentation: docs/features/ml/training_event_recorder.md
last_verified: '2026-10-22T20:30:33Z'
related_bugs: []
---

## 1. Feature ID and name

`ml.training_event_recorder` — Training event recorder.

## 2. Status and version

Status: `implemented`. Schema `1.0`.

## 3. Purpose

Record genuine training lifecycle events with UTC timestamps and monotonic durations.

## 4. Scientific background

Wall-clock subtraction is not a duration measurement. Incomplete JSON must not become a fabricated event.

## 5. Mathematical formula or algorithm

`elapsed_ms = floor(1000 * (monotonic() - t0))`, nondecreasing. `sequence_{i+1} > sequence_i`.

## 6. Explanation of every variable and unit

`timestamp_utc` is ISO-8601 UTC. `elapsed_ms` is milliseconds. `event_type` is from a closed set. Metric units are explicit (`m3_per_m3`, `squared_m3_per_m3`).

## 7. Worked numerical example

A Ridge development run wrote 20 valid JSONL events including `run_created` and `run_completed`, with no `training_iteration` lines.

## 8. Source datasets and provenance

Events belong to one `run_id`. They are not the frozen experiment history.

## 9. Input requirements

A writer lock (O_EXCL) per run directory.

## 10. Processing steps

Validate event, append one JSON line, flush, fsync. On completion mark immutable and write `telemetry_validation.json`.

## 11. Implementation paths and functions

`EventWriter`, `validate_event`, `read_jsonl_events`, `validate_event_log`.

## 12. Configuration parameters

Schema version `1.0`. No extra YAML.

## 13. Outputs and units

`training_events.jsonl`, `telemetry_validation.json`.

## 14. Validation criteria

Valid JSON, schema version, increasing sequences, nondecreasing elapsed time, finite metrics, no secrets, completed-run integrity.

## 15. Missing-value handling

Nullable iteration/metric fields. Truncated last line skipped.

## 16. Temporal leakage considerations

Recorder does not load data. Instrumentation must not emit test-partition metrics in development mode.

## 17. Tests and expected assertions

Writer sequence/UTC/JSONL, immutability, concurrent isolation, truncated-line skip, invalid transitions.

## 18. Scientific limitations

Not crash-proof durability across power loss beyond flush/fsync. Not a live stream.

## 19. Related feature dependencies

- [`ml.training_run_tracking`](training_run_tracking.md)
- [`ml.algorithm_training_instrumentation`](algorithm_training_instrumentation.md)

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T20:30:33Z`
