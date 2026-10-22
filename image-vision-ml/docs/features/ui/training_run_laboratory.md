---
feature_id: ui.training_run_laboratory
name: Training Runs laboratory views
category: ui
status: implemented
mathematical_method: historical event playback from stored JSONL; metric points plotted without interpolation
input_datasets:
- plovdiv_soil_forecast_baselines_v1
source_code:
- frontend/src/pages/MLTrainingPage.tsx
- frontend/src/components/ml/TrainingRunsPanel.tsx
- frontend/src/components/ml/TrainingRunSelector.tsx
- frontend/src/components/ml/TrainingRunOverview.tsx
- frontend/src/components/ml/TrainingRunTimeline.tsx
- frontend/src/components/ml/TrainingMetricsChart.tsx
- frontend/src/components/ml/TrainingEventExplorer.tsx
- frontend/src/components/ml/TrainingPlayback.tsx
- frontend/src/components/ml/TrainingRunComparison.tsx
- frontend/src/components/ml/TrainingDiagnostics.tsx
- frontend/src/utils/runTelemetry.ts
configuration:
- configs/soil_forecasting_experiment.yaml
outputs:
- /ml/training Training Runs tab
tests:
- frontend/src/pages/MLTrainingPage.test.tsx
- frontend/src/utils/runTelemetry.test.ts
documentation: docs/features/ui/training_run_laboratory.md
last_verified: '2026-10-22T20:30:33Z'
related_bugs: []
---

## 1. Feature ID and name

`ui.training_run_laboratory` — Training Runs laboratory views.

## 2. Status and version

Status: `implemented`. Route `/ml/training`, tab **Training Runs**. Not live monitoring.

## 3. Purpose

Inspect recorded telemetry runs: selector, KPIs, timeline, metric history, historical playback, diagnostics, comparison.

## 4. Scientific background

Frozen Phase 4.1 evaluation has no iteration log. New runs are separate. Educational Mathematics demos remain labeled synthetic.

## 5. Mathematical formula or algorithm

Playback index `i` shows events `0…i` only. Charts plot recorded `(iteration, value)` pairs with `connectNulls=false`. Comparison requires matching horizon and validation row count before an unqualified ranking.

## 6. Explanation of every variable and unit

Duration in ms or s. MAE/RMSE in m³/m³. Iterations: “Not applicable” for persistence/seasonal, “Not recorded” for Ridge without solver history, integer `n_iter_` for HGBR.

## 7. Worked numerical example

Selecting the Ridge development run shows no metric chart and the linear-system explanation. Selecting the HGBR run plots staged `training_mse` points 1…n without extra interpolated vertices.

## 8. Source datasets and provenance

GET run APIs. Provenance panel repeats `research_reanalysis` and false operational flags.

## 9. Input requirements

An experiment ID. Empty run lists render an informative empty state.

## 10. Processing steps

User opens Training Runs, filters, selects a run, inspects timeline/events, optionally plays back, optionally compares completed runs.

## 11. Implementation paths and functions

`TrainingRunsPanel`, `formatDurationMs`, `metricHistoryPoints`, `comparisonCompatibility`, `TrainingPlayback` timer cleanup.

## 12. Configuration parameters

None beyond existing experiment YAML. Playback speeds 0.5×, 1×, 2×, 4×.

## 13. Outputs and units

DOM visualizations. No downloaded joblib.

## 14. Validation criteria

No fabricated curve points. Playback never retrains. Comparison warns on mismatched horizons/n. Research labels visible. Loading/error/empty states covered.

## 15. Missing-value handling

Missing history explained per algorithm. Unavailable metrics are not shown as 0.

## 16. Temporal leakage considerations

UI does not request 2025 test metrics for these runs. Development runs declare `test_targets_accessed=false`.

## 17. Tests and expected assertions

Run listing, Ridge missing curve, playback step/reset, comparison, boosting recorded points, empty state, API error.

## 18. Scientific limitations

No live stream. Development validation MAE is not a 2025 holdout update. ERA5-Land modeled targets.

## 19. Related feature dependencies

- [`ui.ml_training_laboratory`](ml_training_laboratory.md)
- [`ml.training_run_api`](../ml/training_run_api.md)
- [`ml.algorithm_training_instrumentation`](../ml/algorithm_training_instrumentation.md)

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T20:30:33Z`
