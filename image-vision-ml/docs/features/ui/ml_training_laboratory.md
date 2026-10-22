---
feature_id: ui.ml_training_laboratory
name: ML Training Laboratory
category: ui
status: implemented
mathematical_method: display of stored MAE/RMSE/skill; educational OLS, ridge closed form, and L(w)=(w-3)^2 gradient descent
input_datasets:
- plovdiv_soil_forecast_baselines_v1
source_code:
- frontend/src/pages/MLTrainingPage.tsx
- frontend/src/components/ml/ExperimentSelector.tsx
- frontend/src/components/ml/TrainingOverview.tsx
- frontend/src/components/ml/DatasetExplorer.tsx
- frontend/src/components/ml/AlgorithmExplorer.tsx
- frontend/src/components/ml/TrainingLifecycle.tsx
- frontend/src/components/ml/ModelEvaluation.tsx
- frontend/src/components/ml/MathematicsLab.tsx
- frontend/src/components/ml/ExperimentProvenancePanel.tsx
- frontend/src/components/ml/TrainingRunsPanel.tsx
- frontend/src/utils/mlLab.ts
- frontend/src/utils/mlDemos.ts
- backend/app/api/ml.py
- backend/app/services/ml_service.py
- backend/app/schemas/ml.py
configuration:
- configs/soil_forecasting_experiment.yaml
outputs:
- /ml/training research dashboard
- GET /api/v1/ml/experiments/{id}/dataset
- GET /api/v1/ml/experiments/{id}/features
- GET /api/v1/ml/experiments/{id}/training
- GET /api/v1/ml/experiments/{id}/provenance
- GET /api/v1/ml/experiments/{id}/runs
tests:
- frontend/src/pages/MLTrainingPage.test.tsx
- frontend/src/utils/mlLab.test.ts
- frontend/src/utils/mlDemos.test.ts
- frontend/src/app/App.test.tsx
- backend/tests/test_ml_api.py
documentation: docs/features/ui/ml_training_laboratory.md
last_verified: '2026-10-22T20:30:33Z'
related_bugs: []
---

## 1. Feature ID and name

`ui.ml_training_laboratory` — ML Training Laboratory.

## 2. Status and version

Status: `implemented`. Experiment pipeline remains `4.1.0`. Frozen-artifact display plus a Training Runs tab for separately recorded telemetry. Visiting the page still does not train models.

## 3. Purpose

Give researchers a dedicated page to inspect stored soil-moisture forecasting experiments, compare algorithms, and study the mathematics, without retraining on page visit and without presenting synthetic curves as experimental evidence.

## 4. Scientific background

Phase 4.1 fitted persistence, a training-year seasonal mean, Ridge, and HistGradientBoostingRegressor on ERA5-Land modeled `swvl1` (0–7 cm) with chronological 2023/2024/2025 splits. Labels are reanalysis, not field sensors. `suitable_for_modeling` remains false.

## 5. Mathematical formula or algorithm

Displayed scientific metrics are read from CSVs. Skill is \(1-\mathrm{MAE}_{model}/\mathrm{MAE}_{persistence}\) on matched rows.

Educational only:

- OLS slope \(\hat\beta=\sum(x-\bar x)(y-\bar y)/\sum(x-\bar x)^2\).
- Quadratic descent \(L(w)=(w-3)^2\), \(w\leftarrow w-\eta\cdot 2(w-3)\).
- Ridge closed form \((X^\top X+\alpha I_{\mathrm{no\ intercept}})\beta=X^\top y\) on synthetic correlated columns.

Production Ridge uses sklearn’s linear-system solver, not these demos.

## 6. Explanation of every variable and unit

- `horizon_days`: 1, 3, or 7.
- `feature_set`: A/B/C enabled; D not trained.
- `partition`: validation 2024 or test 2025.
- Sample `n`: complete-case rows for that horizon and set.
- MAE/RMSE: m³/m³.
- Skill: dimensionless.
- `swvl1`: volumetric soil water 0–7 cm.

## 7. Worked numerical example

On the laboratory page with experiment `plovdiv_soil_forecast_baselines_v1`, feature set C, horizon 1, algorithm persistence, Overview shows training/validation/test counts from `prepared_summary.json` (350 / 365 / 364 in the Phase 4.1 C tables) and Validation MAE from stored persistence metrics. Switching horizon to 7 updates those counts from the same table. The Mathematics gradient-descent demo with \(\eta=0.2\), \(w_0=0\), 40 steps converges to \(w\approx 3\); \(\eta=1.2\) diverges.

## 8. Source datasets and provenance

Read-only experiment directory `data/processed/ml/experiments/plovdiv_soil_forecast_baselines_v1/`. APIs sanitize identifiers and strip local paths. Fingerprint, freeze time, git revision, Python, and scikit-learn versions come from freeze and training summaries.

## 9. Input requirements

A frozen experiment directory with `experiment_summary.json` or config snapshot. Dataset, features, training, and provenance endpoints return `available=false` when files are missing rather than inventing counts.

## 10. Processing steps

1. List experiments; select experiment, horizon, algorithm, feature set, partition.
2. Fetch detail, dataset, features, training, provenance, and metrics over GET.
3. Fetch predictions only on the Evaluation tab.
4. Render Overview, Dataset, Algorithms, Training Process, Evaluation, Mathematics, or Provenance.
5. Educational sliders recompute in the browser.

## 11. Implementation paths and functions

`MLTrainingPage`, `ExperimentSelector`, `TrainingOverview`, `DatasetExplorer`, `AlgorithmExplorer`, `TrainingLifecycle`, `ModelEvaluation`, `MathematicsLab`, `ExperimentProvenancePanel`, `mlLab.ts`, `mlDemos.ts`, `ml_service.experiment_dataset/features/training/provenance`.

## 12. Configuration parameters

No new YAML. Selectors read `horizons_days` and enabled `feature_sets` from the experiment snapshot. Predictions `limit` default 400, max 2000.

## 13. Outputs and units

DOM page `/ml/training`. Charts in m³/m³. JSON APIs listed above. Demo MSE is synthetic and unlabeled as agricultural.

## 14. Validation criteria

Nav entry **ML Training Lab**. Counts match artifacts. Missing telemetry is explicit. Feature set D is not offered as trained. Ridge is not described as epoch GD. Demos carry the educational banner. Flags stay false. GET does not rewrite experiment files.

## 15. Missing-value handling

Unavailable metrics render **Unavailable**, never a fabricated 0. Null rainfall in source tables remains null. Empty experiment list is an empty state.

## 16. Temporal leakage considerations

The UI does not join future weather or satellite into features. It explains chronological splits and issue-time cutoff \(D-1\). Predictions charts use stored issue dates only.

## 17. Tests and expected assertions

Horizon-specific counts, derived 2025 winners, missing `training_events.jsonl`, untrained D, Ridge vs GD copy, demo banner, API 500, GET does not write files.

- `frontend/src/pages/MLTrainingPage.test.tsx`
- `frontend/src/utils/mlLab.test.ts`
- `frontend/src/utils/mlDemos.test.ts`
- `backend/tests/test_ml_api.py`

## 18. Scientific limitations

Research reanalysis only. No operational forecast. No field ground truth. No live training monitor. Educational GD/boosting stumps are not the fitted sklearn objects.

## 19. Related feature dependencies

- [`ml.soil_forecast_experiment`](../ml/soil_forecast_experiment.md)
- [`ml.persistence_soil_forecast`](../ml/persistence_soil_forecast.md)
- [`ml.ridge_soil_moisture_forecast`](../ml/ridge_soil_moisture_forecast.md)
- [`ml.gradient_boosting_soil_forecast`](../ml/gradient_boosting_soil_forecast.md)
- [`ml.final_holdout_evaluation`](../ml/final_holdout_evaluation.md)
- [`ui.training_run_laboratory`](training_run_laboratory.md)
- [`ml.training_run_api`](../ml/training_run_api.md)

## 20. Related bug/fix IDs

None opened for this UI. Fingerprint repair remains [`BUG-0012`](../../bugs/BUG-0012.md).

## 21. Last reviewed timestamp in UTC

`2026-10-22T20:30:33Z`
