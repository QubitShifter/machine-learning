---
feature_id: weather.antecedent_precipitation_index
name: Antecedent precipitation index
category: weather
status: implemented
mathematical_method: API_t = P_t + k API_{t-1}
input_datasets:
- Daily ERA5-Land precipitation_total_mm
source_code:
- ml/preprocessing/wetness.py
- ml/ingestion/soil_pipeline.py
configuration:
- configs/weather_era5_land.yaml
outputs:
- api_k085_mm
- api_k090_mm
- api_k095_mm
tests:
- tests/test_soil.py
documentation: docs/features/weather/antecedent_precipitation_index.md
last_verified: '2026-10-22T08:49:05Z'
related_bugs: []
---

## 1. Feature ID and name

`weather.antecedent_precipitation_index` — Antecedent precipitation index.

## 2. Status and version

Status: `implemented`. Wetness version 3.4.0.

## 3. Purpose

Summarise decaying rainfall history as a rainfall-history indicator, not as measured soil moisture.

## 4. Scientific background

API is a linear reservoir of precipitation. k is a retention/decay factor, not a universal soil constant. Default exploratory factors are 0.85, 0.90 and 0.95. Calibration to local soils is later work.

## 5. Mathematical formula or algorithm

API_t = P_t + k API_{t-1}

API_0 = 0 before the first day of the series. 0 < k ≤ 1. If P_t is missing, API_t and all later values are null. End-of-day API includes P_t.

## 6. Explanation of every variable and unit

- P_t: daily precipitation (mm).
- k: dimensionless decay in (0, 1].
- API_t: millimetres of retained antecedent precipitation (same unit as P).
- warmup: true while the number of valid precipitation days so far is ≤ 30.

## 7. Worked numerical example

P = [0, 10, 0, 0], k = 0.9, API_0 = 0 → API = [0, 10, 9, 8.1].

## 8. Source datasets and provenance

Processed daily weather `plovdiv_weather_2023_2025`. Kind: `rainfall_history_indicator`.

## 9. Input requirements

`precipitation_total_mm` from daily weather CSV. Missing precipitation must remain null.

## 10. Processing steps

`python -m scripts.soil_dataset wetness --weather-config configs/weather_era5_land.yaml` writes `data/processed/wetness/<weather_id>/wetness_indicators.csv` without modifying `daily_weather.csv`.

## 11. Implementation paths and functions

`ml/preprocessing/wetness.py`: `antecedent_precipitation_index`, `attach_wetness_features`.

Source files:
- [`ml/preprocessing/wetness.py`](../../../ml/preprocessing/wetness.py)

## 12. Configuration parameters

Default k factors (0.85, 0.90, 0.95), warmup_days=30, dry_day_mm from weather config (1.0 mm).

## 13. Outputs and units

`api_k085_mm`, `api_k090_mm`, `api_k095_mm` and `*_warmup` flags.

## 14. Validation criteria

k outside (0, 1] raises. Missing P does not become 0. Hand-verified sequence in tests.

## 15. Missing-value handling

Missing P_t → API_t = None thereafter. No restart from zero after a gap.

## 16. Temporal leakage considerations

API_t uses P_t and earlier days only. Future precipitation is not used. Satellite-aligned `precip_prev_N` still excludes date D.

## 17. Tests and expected assertions

[`tests/test_soil.py`](../../../tests/test_soil.py) `test_api_hand_verified_sequence`.

## 18. Scientific limitations

Not soil moisture. k is not calibrated to Plovdiv soils. Warm-up days are exploratory.

## 19. Related feature dependencies

- [`weather.precipitation_aggregation`](precipitation_aggregation.md)
- [`weather.drying_and_wetness_indicators`](drying_and_wetness_indicators.md)
- [`weather.historical_rolling_features`](historical_rolling_features.md)

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T08:49:05Z`
