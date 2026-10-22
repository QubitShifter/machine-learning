---
feature_id: ml.algorithm_training_instrumentation
name: Algorithm-specific training instrumentation
category: ml
status: implemented
mathematical_method: truthful Ridge linear-system diagnostics; HGBR n_iter_ and post-fit staged_predict MSE; no fabricated epochs
input_datasets:
- plovdiv_soil_forecast_baselines_v1
source_code:
- ml/soil_forecasting/training_instrumentation.py
- ml/soil_forecasting/models.py
configuration:
- configs/soil_forecasting_experiment.yaml
outputs:
- model_artifacts/diagnostics.json
tests:
- tests/test_training_instrumentation.py
documentation: docs/features/ml/algorithm_training_instrumentation.md
last_verified: '2026-10-22T20:30:33Z'
related_bugs: []
---

## 1. Feature ID and name

`ml.algorithm_training_instrumentation` — Algorithm-specific training instrumentation.

## 2. Status and version

Status: `implemented`. Uses sklearn 1.9.x `Ridge` and `HistGradientBoostingRegressor` as already configured (`early_stopping=False`).

## 3. Purpose

Record what each algorithm actually exposes during a research-development fit.

## 4. Scientific background

Persistence and seasonal baselines are not optimizers. Ridge typically solves a linear system (`solver=auto`). HGBR fits boosting stages. Native score arrays are empty when early stopping is off.

## 5. Mathematical formula or algorithm

Persistence: \(\hat\theta_{D+h}=\theta_{D-1}\). Seasonal: training-year monthly mean. Ridge: `StandardScaler` then \(\min \|y-X\beta\|^2+\alpha\|\beta\|^2\). HGBR: stagewise trees; post-fit `training_mse_m = mean((y_{train}-F_m(X_{train}))^2)` via `staged_predict`.

## 6. Explanation of every variable and unit

`n_iter_` is boosting stages, not neural epochs. `training_mse` unit is \((m^3/m^3)^2\). MAE unit is \(m^3/m^3\). `used_for_fitting` is false for staged_predict.

## 7. Worked numerical example

Development HGBR h=1 C recorded `n_iter_=50` and 50 staged training-MSE points. Ridge recorded coefficients and `iteration_history_available=false`. Persistence recorded `training_iterations=0`.

## 8. Source datasets and provenance

2023 training / 2024 validation complete-case rows. Label `telemetry_development_run`.

## 9. Input requirements

Existing estimators in `models.py`. No SGD substitute for Ridge. No randomized early stopping.

## 10. Processing steps

Fit on training. Predict train and validation after fit. Emit only events that occurred.

## 11. Implementation paths and functions

`_fit_persistence`, `_fit_seasonal`, `_fit_ridge`, `_fit_boosting`.

## 12. Configuration parameters

Ridge `--alpha` (default 1.0). HGBR `--max-iter`, `--max-depth`, `--learning-rate`, `--seed`. `early_stopping` stays false.

## 13. Outputs and units

Diagnostics JSON, optional coefficients, staged metric events, validation MAE/RMSE/skill.

## 14. Validation criteria

No invented persistence/seasonal iterations. Ridge has no fabricated epoch history. HGBR uses actual `n_iter_`. Runtime durations are measured.

## 15. Missing-value handling

Missing native score arrays are explained, not filled.

## 16. Temporal leakage considerations

Chronological training/validation split unchanged. Internal HGBR validation remains disabled.

## 17. Tests and expected assertions

`test_persistence_has_no_invented_iterations`, `test_ridge_records_fit_metadata_without_epoch_curve`, `test_gradient_boosting_records_actual_n_iter_and_staged_history`.

## 18. Scientific limitations

Staged_predict is a post-fit diagnostic, not native `train_score_`. Development validation MAE is not a new 2025 skill claim.

## 19. Related feature dependencies

- [`ml.ridge_soil_moisture_forecast`](ridge_soil_moisture_forecast.md)
- [`ml.gradient_boosting_soil_forecast`](gradient_boosting_soil_forecast.md)
- [`ml.training_event_recorder`](training_event_recorder.md)

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T20:30:33Z`
