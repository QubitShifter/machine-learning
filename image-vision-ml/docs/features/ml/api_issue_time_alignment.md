---
feature_id: ml.api_issue_time_alignment
name: API alignment at issue time
category: ml
status: implemented
mathematical_method: 'API_t=P_t+k API_{t-1} evaluated at t=D-1'
input_datasets:
- plovdiv_weather_2023_2025
- plovdiv_soil_2023_2025
- plovdiv_2023_2025
source_code:
- ml/agricultural_ml/pipeline.py
- ml/agricultural_ml/features.py
- ml/agricultural_ml/targets.py
- ml/agricultural_ml/time_semantics.py
- ml/agricultural_ml/splits.py
- ml/agricultural_ml/leakage.py
- ml/agricultural_ml/satellite.py
- ml/agricultural_ml/readiness.py
- ml/agricultural_ml/metrics.py
- ml/agricultural_ml/baselines.py
- scripts/agricultural_ml_dataset.py
configuration:
- configs/agricultural_ml_dataset.yaml
outputs:
- data/processed/ml/plovdiv_agricultural_ml_2023_2025/
tests:
- tests/test_agricultural_ml_dataset.py
documentation: docs/features/ml/api_issue_time_alignment.md
last_verified: '2026-10-22T17:14:17Z'
related_bugs: []
---

## 1. Feature ID and name

`ml.api_issue_time_alignment` — API alignment at issue time.

## 2. Status and version

Status: `implemented`. Agricultural ML pipeline version 4.0.0. No trained forecasting model.

## 3. Purpose

Use end-of-day antecedent precipitation at D-1 for a beginning-of-day issue, instead of joining wetness by issue date.

## 4. Scientific background

Existing wetness CSV stores API including P_t on calendar date t. Blindly joining on issue date D would include rainfall from D.

## 5. Mathematical formula or algorithm

\(\mathrm{API}_t=P_t+k\mathrm{API}_{t-1}\) with k in {0.85, 0.90, 0.95}, API_0=0, warmup 30 valid days. Missing P breaks the series. Feature API(D)=API_{D-1}.

## 6. Explanation of every variable and unit

api_k085_mm, api_k090_mm, api_k095_mm in mm; source_date_utc; warmup flag.

## 7. Worked numerical example

Issue 2024-04-10 uses API source date 2024-04-09. Issue 2024-04-11 uses 2024-04-10 and a different API value.

## 8. Source datasets and provenance

Daily precipitation from plovdiv_weather_2023_2025. Wetness CSV is not joined by calendar date.

## 9. Input requirements

Complete precipitation series through D-1. Warm-up days are flagged, not silently treated as mature API.

## 10. Processing steps

`build_api_lookup` then index at last_observation_date. Reuses `antecedent_precipitation_index`.

## 11. Implementation paths and functions

`ml.agricultural_ml.features.build_api_lookup`; `ml.preprocessing.wetness.antecedent_precipitation_index`.

Source files:

- [`ml/agricultural_ml/`](../../../ml/agricultural_ml/)
- [`scripts/agricultural_ml_dataset.py`](../../../scripts/agricultural_ml_dataset.py)
- [`configs/agricultural_ml_dataset.yaml`](../../../configs/agricultural_ml_dataset.yaml)

## 12. Configuration parameters

api.k_factors, api.warmup_days=30, api.alignment=end_of_day_on_D-1.

## 13. Outputs and units

API columns on features_daily.csv.

## 14. Validation criteria

api source date < issue date. Future-rainfall fixture fails if April 10 rain enters prev-7 or API.

## 15. Missing-value handling

Null after a precipitation gap. Warm-up does not invent history before 2023-01-01.

## 16. Temporal leakage considerations

Joining wetness_indicators.csv on issue_date would leak P_D.

## 17. Tests and expected assertions

[`tests/test_agricultural_ml_dataset.py`](../../../tests/test_agricultural_ml_dataset.py)

test_api_uses_end_of_day_on_d_minus_1_not_issue_date.

## 18. Scientific limitations

API is a rainfall-memory proxy, not soil moisture.

## 19. Related feature dependencies

- [`weather.antecedent_precipitation_index`](../weather/antecedent_precipitation_index.md)
- [`weather.drying_and_wetness_indicators`](../weather/drying_and_wetness_indicators.md)

- [`docs/ml/agricultural_forecasting_mathematics.md`](../../ml/agricultural_forecasting_mathematics.md)
- [`docs/ml/scientific_decision_log.md`](../../ml/scientific_decision_log.md)

## 20. Related bug/fix IDs

None created for Phase 4.0. Leakage risks were prevented by construction rather than discovered as production defects.

## 21. Last reviewed timestamp in UTC

`2026-10-22T17:14:17Z`
