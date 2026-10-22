---
feature_id: forecasting.issue_valid_time_contracts
name: Forecast issue and valid-time contracts
category: forecasting
status: partial
mathematical_method: lead_time_hours = valid_time − issue_time; operational vs perfect-weather modes
input_datasets:
- None ingested; ECMWF Open Data not downloaded
source_code:
- ml/forecasting/contracts.py
configuration: []
outputs:
- validated forecast record dictionaries
tests:
- tests/test_soil.py
documentation: docs/features/forecasting/issue_valid_time_contracts.md
last_verified: '2026-10-22T08:49:05Z'
related_bugs: []
---

## 1. Feature ID and name

`forecasting.issue_valid_time_contracts` — Forecast issue and valid-time contracts.

## 2. Status and version

Status: `partial`. Contract version 3.4.0. No live ECMWF Open Data download.

## 3. Purpose

Define leakage-safe metadata so a later forecasting phase can separate operational replay from oracle/perfect-weather experiments.

## 4. Scientific background

A forecast issued at t may use data available at or before t. Observed rainfall at t+h must not enter an operational prediction issued at t. ECMWF Open Data has short rolling retention; a complete 2023–2025 forecast archive is not assumed.

## 5. Mathematical formula or algorithm

lead_time_hours = (forecast_valid_time_utc − forecast_issue_time_utc) in hours.

θ̂_{t+h} is the state at UTC date t+h, not a trailing h-day mean, unless a target document says otherwise. Horizons: 1, 3, 7 days.

## 6. Explanation of every variable and unit

Required fields: `forecast_issue_time_utc`, `forecast_valid_time_utc`, `lead_time_hours`, `provider`, `forecast_model`, `model_version`, `variable`, `unit`, `source_grid`, `retrieved_at_utc`, `source_kind`. Modes: `operational_forecast_replay`, `retrospective_perfect_weather`.

## 7. Worked numerical example

Issue 2025-04-10T00:00:00Z, valid 2025-04-17T00:00:00Z → lead_time_hours = 168. Using observed 2025-04-17 rainfall in operational mode is rejected.

## 8. Source datasets and provenance

No forecast archive is stored. Source kinds: historical_reanalysis, archived_forecast, live_forecast.

## 9. Input requirements

Complete metadata. Reanalysis is forbidden in operational mode.

## 10. Processing steps

`validate_forecast_record`. No network call.

## 11. Implementation paths and functions

`ml/forecasting/contracts.py`: `validate_forecast_record`, `target_contract`, `PREDICTION_TARGETS`.

Source files:
- [`ml/forecasting/contracts.py`](../../../ml/forecasting/contracts.py)

## 12. Configuration parameters

None. ECMWF Open Data is not configured for retrieval.

## 13. Outputs and units

Normalized record plus `oracle_weather_used`. Target catalogue entries are contracts, not trained models.

## 14. Validation criteria

Valid time ≥ issue time. Lead time matches. Operational mode rejects reanalysis-as-forecast and future observed weather.

## 15. Missing-value handling

Missing required fields raise `ForecastContractError`. No silent defaults for issue/valid times.

## 16. Temporal leakage considerations

This feature exists to prevent leakage. Perfect-weather results must never be presented as operational skill.

## 17. Tests and expected assertions

[`tests/test_soil.py`](../../../tests/test_soil.py) `test_forecast_contract_blocks_reanalysis_and_future_obs`.

## 18. Scientific limitations

No archived 2023–2025 open-data forecast cycle is ingested. Contracts are not forecasts.

## 19. Related feature dependencies

- [`forecasting.agricultural_forecasting`](agricultural_forecasting.md)
- [`integration.temporal_leakage_prevention`](../integration/temporal_leakage_prevention.md)

## 20. Related bug/fix IDs

None.

## 21. Last reviewed timestamp in UTC

`2026-10-22T08:49:05Z`
