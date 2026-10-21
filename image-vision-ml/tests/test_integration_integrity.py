from datetime import date, timedelta
from pathlib import Path

import pytest
import yaml

from ml.analysis.weather_timeseries import read_daily_weather, write_daily_weather
from ml.ingestion.manifest import write_json_atomic
from ml.ingestion.weather_pipeline import integrate_weather_dataset
from ml.integration.satellite_weather import (
    INTEGRATION_VERSION,
    integrate_satellite_weather,
)
from ml.integration.validate import validate_integrated_observations


def _complete_day(day: date, rain: float = 1.0) -> dict:
    return {
        "date_utc": day.isoformat(),
        "aoi_id": "plovdiv_test",
        "temperature_mean_c": 10.0,
        "relative_humidity_mean_pct": 50.0,
        "wind_speed_mean_ms": 2.0,
        "precipitation_total_mm": rain,
        "evaporation_total_mm": 0.4,
        "hourly_records_expected": 24,
        "hourly_records_available": 24,
        "boundary_00utc_available": True,
        "quality_status": "valid",
        "source_grid_id": "42.1,24.7",
    }


def _weather_range(start: str, days: int, rain: float = 1.0) -> list[dict]:
    first = date.fromisoformat(start)
    return [_complete_day(first + timedelta(days=offset), rain) for offset in range(days)]


def test_no_future_leakage_and_window_boundaries():
    weather = _weather_range("2024-03-01", 45, rain=1.0)
    weather[-1]["precipitation_total_mm"] = 999.0
    rows = integrate_satellite_weather(
        weather,
        [{"scene_id": "S1", "date": "2024-04-01T09:18:47Z", "mean": 0.42, "quality_status": "valid"}],
        weather_dataset_id="weather",
        satellite_dataset_id="sat",
        aoi_id="plovdiv_test",
        spatial={
            "method": "nearest_grid_cell",
            "source_latitude": 42.1,
            "source_longitude": 24.7,
            "distance_km": 4.8,
        },
    )
    row = rows[0]
    assert row["window_7d_start_utc"] == "2024-03-25"
    assert row["window_7d_end_utc"] == "2024-03-31"
    assert row["precip_prev_7d_mm"] == 7.0
    assert row["acquisition_timestamp_utc"].startswith("2024-04-01T09:18:47")
    report = validate_integrated_observations(rows, weather_rows=weather)
    assert report["duplicate_scene_ids"] == []
    leak = [issue for issue in report["issues"] if issue["code"] == "future_temporal_leakage"]
    assert leak == []
    mismatch = [issue for issue in report["issues"] if issue["code"] == "reprocessing_inconsistency"]
    assert mismatch == []


def test_quality_flags_are_separate_dimensions():
    rows = integrate_satellite_weather(
        [],
        [{"scene_id": "S1", "date": "2024-04-01", "mean": 0.4, "quality_status": "valid"}],
        weather_dataset_id="weather",
        satellite_dataset_id="sat",
        aoi_id="plovdiv_test",
        weather_integration_readiness="limited",
        satellite_supervised_readiness="not_ready",
    )
    row = rows[0]
    assert row["satellite_observation_valid"] is True
    assert row["weather_observation_valid"] is False
    assert row["weather_feature_window_complete"] is False
    assert row["integrated_observation_complete"] is False
    assert row["suitable_for_modeling"] is False
    assert row["quality_status"] == "valid"


def test_invalid_ndvi_and_incompatible_quality_are_flagged():
    rows = integrate_satellite_weather(
        _weather_range("2024-03-01", 40),
        [
            {
                "scene_id": "BAD",
                "date": "2024-04-01",
                "mean": 1.4,
                "ndvi_minimum": 0.2,
                "ndvi_maximum": 0.1,
                "quality_status": "requires_review",
            }
        ],
        weather_dataset_id="weather",
        satellite_dataset_id="sat",
        aoi_id="plovdiv_test",
    )
    assert rows[0]["satellite_observation_valid"] is False
    report = validate_integrated_observations(rows, weather_rows=_weather_range("2024-03-01", 40))
    codes = {issue["code"] for issue in report["issues"]}
    assert "invalid_ndvi_mean" in codes
    assert "invalid_ndvi_range" in codes


def test_idempotent_reintegration_and_refresh_after_new_weather(tmp_path: Path):
    config_path = tmp_path / "weather.yaml"
    config_path.write_text(yaml.safe_dump({
        "dataset_id": "wx",
        "source": {"dataset": "reanalysis-era5-land"},
        "area": {"name": "plovdiv_test", "bbox": [24.65, 42.05, 24.68, 42.08]},
        "period": {"start": "2025-04-01", "end": "2025-04-30"},
        "variables": [
            "2m_temperature",
            "2m_dewpoint_temperature",
            "total_precipitation",
            "10m_u_component_of_wind",
            "10m_v_component_of_wind",
            "total_evaporation",
        ],
        "spatial": {
            "method": "nearest_grid_cell",
            "retrieval_area": [42.20, 24.50, 41.90, 24.90],
        },
        "features": {"dry_day_precipitation_mm": 1.0, "windows_days": [7, 14, 30]},
    }), encoding="utf-8")

    weather_processed = tmp_path / "weather"
    satellite_root = tmp_path / "satellite"
    integration_root = tmp_path / "integration"
    daily_dir = weather_processed / "wx"
    write_daily_weather(_weather_range("2025-04-10", 11, rain=2.0), daily_dir)
    write_json_atomic(daily_dir / "quality_report.json", {
        "dataset_id": "wx",
        "integration_readiness": "limited",
        "spatial": {
            "method": "nearest_grid_cell",
            "source_longitude": 24.7,
            "source_latitude": 42.1,
            "distance_km": 4.8,
        },
    })
    quality_dir = satellite_root / "sat" / "quality"
    quality_dir.mkdir(parents=True)
    write_json_atomic(quality_dir / "dataset_quality.json", {
        "dataset_id": "sat",
        "scenes": [{
            "scene_id": "S2A_35TLG_20250421_0_L2A",
            "acquisition_date": "2025-04-21",
            "quality_status": "valid",
            "ndvi_mean": 0.41,
            "ndvi_minimum": 0.1,
            "ndvi_maximum": 0.8,
            "ndvi_median": 0.4,
            "valid_ndvi_pct": 97.0,
            "cloud_shadow_fraction_pct": 0.0,
        }],
        "dataset": {"spatial_grid_consistency": {"expected": {"crs": "EPSG:32635", "resolution": [10.0, 10.0]}}},
        "training_readiness": {"supervised_soil_forecasting": "not_ready"},
    })
    scene_dir = satellite_root / "sat" / "scenes" / "S2A_35TLG_20250421_0_L2A"
    scene_dir.mkdir(parents=True)
    write_json_atomic(scene_dir / "processing_metadata.json", {
        "acquisition_date": "2025-04-21T09:18:47Z",
        "processing_version": "1.1.0",
        "processing_settings": {"target_grid": {"crs": "EPSG:32635", "resolution": [10.0, 10.0]}},
    })

    first = integrate_weather_dataset(
        config_path,
        satellite_dataset_id="sat",
        processed_root=weather_processed,
        satellite_root=satellite_root,
        integration_root=integration_root,
    )
    assert first["observation_count"] == 1
    first_row = first["rows"][0]
    assert first_row["precip_prev_7d_mm"] == pytest.approx(14.0)
    assert first_row["window_7d_complete"] is True
    assert first_row["window_30d_complete"] is False
    assert first_row["precip_prev_30d_mm"] is None
    assert first_row["ndvi_mean"] == pytest.approx(0.41)
    assert first_row["source_crs"] == "EPSG:32635"

    second = integrate_weather_dataset(
        config_path,
        satellite_dataset_id="sat",
        processed_root=weather_processed,
        satellite_root=satellite_root,
        integration_root=integration_root,
    )
    assert second["rows"][0]["precip_prev_7d_mm"] == first_row["precip_prev_7d_mm"]
    assert second["rows"][0]["integration_version"] == INTEGRATION_VERSION
    csv_rows = read_daily_weather(integration_root / "sat" / "satellite_weather.csv")
    assert len(csv_rows) == 1

    write_daily_weather(_weather_range("2025-03-22", 30, rain=2.0), daily_dir)
    refreshed = integrate_weather_dataset(
        config_path,
        satellite_dataset_id="sat",
        processed_root=weather_processed,
        satellite_root=satellite_root,
        integration_root=integration_root,
    )
    refreshed_row = refreshed["rows"][0]
    assert refreshed_row["window_30d_complete"] is True
    assert refreshed_row["precip_prev_30d_mm"] == pytest.approx(60.0)
    assert refreshed_row["weather_feature_window_complete"] is True
    assert refreshed_row["suitable_for_modeling"] is False
    meta = (integration_root / "sat" / "integration_metadata.json").read_text(encoding="utf-8")
    assert "sources_changed" in meta


def test_requires_review_scene_is_not_loaded(tmp_path: Path):
    from ml.integration.satellite_weather import load_validated_satellite_observations

    quality_dir = tmp_path / "sat" / "quality"
    quality_dir.mkdir(parents=True)
    write_json_atomic(quality_dir / "dataset_quality.json", {
        "scenes": [
            {"scene_id": "VALID", "acquisition_date": "2025-04-21", "quality_status": "valid", "ndvi_mean": 0.4},
            {"scene_id": "REVIEW", "acquisition_date": "2025-04-22", "quality_status": "requires_review", "ndvi_mean": 0.9},
        ],
        "dataset": {},
    })
    loaded = load_validated_satellite_observations("sat", processed_root=tmp_path)
    assert [item["scene_id"] for item in loaded] == ["VALID"]
