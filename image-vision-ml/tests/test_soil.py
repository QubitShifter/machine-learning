from datetime import date as date_cls, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from ml.forecasting.contracts import (
    MODE_OPERATIONAL,
    MODE_PERFECT_WEATHER,
    SOURCE_KIND_ARCHIVED_FORECAST,
    SOURCE_KIND_REANALYSIS,
    ForecastContractError,
    target_contract,
    validate_forecast_record,
)
from ml.ingestion.era5_land import extract_hourly_records
from ml.ingestion.soil_config import load_soil_config, validate_soil_config
from ml.ingestion.soil_pipeline import (
    check_soil_config,
    download_soil,
    generate_wetness_dataset,
    process_soil_dataset,
    soil_status,
)
from ml.ingestion.soilgrids import import_soilgrids_properties, soilgrids_availability
from ml.preprocessing.errors import SoilConfigError, WeatherDownloadError
from ml.preprocessing.soil import (
    ROOT_ZONE_WEIGHT_SUM,
    daily_mean_theta,
    plant_available_water_fraction,
    root_zone_theta_0_100,
)
from ml.analysis.soil_weather import align_soil_weather_wetness
from ml.preprocessing.wetness import (
    antecedent_precipitation_index,
    attach_wetness_features,
    consecutive_dry_days,
    days_since_rain,
    trailing_sum,
)
from ml.integration.satellite_weather import prior_window_dates
from ml.sources.registry import load_source_registry
from ml.validation.modeling_readiness import (
    TASK_INDEPENDENT_FIELD,
    TASK_SOIL,
    TASK_SOIL_HISTORICAL,
    assess_task_readiness,
)
from scripts.soil_dataset import main as soil_main


def _soil_config_payload(**overrides):
    payload = {
        "dataset_id": "plovdiv_soil_test",
        "source": {"dataset": "reanalysis-era5-land"},
        "area": {"name": "plovdiv_test", "bbox": [24.65, 42.05, 24.68, 42.08]},
        "period": {"start": "2023-01-01", "end": "2023-01-02"},
        "variables": [
            "volumetric_soil_water_layer_1",
            "volumetric_soil_water_layer_2",
            "volumetric_soil_water_layer_3",
            "volumetric_soil_water_layer_4",
        ],
        "spatial": {
            "retrieval_area": [42.20, 24.50, 41.90, 24.90],
        },
        "downloads": {"include_next_day_boundary": False},
    }
    payload.update(overrides)
    return payload


def _hourly_day(day: str, theta=(0.30, 0.28, 0.25, 0.22), missing_hour=None):
    start = datetime.fromisoformat(f"{day}T00:00:00+00:00")
    records = []
    for hour in range(24):
        if hour == missing_hour:
            continue
        stamp = start + timedelta(hours=hour)
        records.append({
            "timestamp_utc": stamp.isoformat().replace("+00:00", "Z"),
            "swvl1": theta[0],
            "swvl2": theta[1],
            "swvl3": theta[2],
            "swvl4": theta[3],
        })
    return records


def test_root_zone_weights_and_formula():
    assert ROOT_ZONE_WEIGHT_SUM == pytest.approx(1.0)
    assert root_zone_theta_0_100(0.30, 0.28, 0.25) == pytest.approx(0.2598)
    assert root_zone_theta_0_100(0.30, None, 0.25) is None
    assert daily_mean_theta([0.2] * 24) == pytest.approx(0.2)
    assert daily_mean_theta([0.2] * 23) is None
    assert daily_mean_theta([0.2] * 23 + [None]) is None
    assert plant_available_water_fraction(0.25, None, None) is None


def test_api_hand_verified_sequence():
    precip = [0.0, 10.0, 0.0, 0.0]
    api = antecedent_precipitation_index(precip, k=0.9, initial=0.0)
    assert api == pytest.approx([0.0, 10.0, 9.0, 8.1])
    with pytest.raises(ValueError):
        antecedent_precipitation_index(precip, k=0)
    missing = antecedent_precipitation_index([1.0, None, 2.0], k=0.9)
    assert missing[0] == pytest.approx(1.0)
    assert missing[1] is None
    assert missing[2] is None


def test_wetness_missing_and_windows_do_not_use_future():
    precip = [5.0, 0.0, None, 0.0, 8.0]
    assert consecutive_dry_days(precip)[2] is None
    assert days_since_rain(precip)[0] == 0
    assert days_since_rain(precip)[1] == 1
    assert days_since_rain(precip)[2] is None
    prev = trailing_sum(precip, 1, include_current=False)
    assert prev[0] is None
    assert prev[1] == pytest.approx(5.0)
    end = trailing_sum([1.0, 2.0, 3.0], 2, include_current=True)
    assert end[1] == pytest.approx(3.0)
    assert end[2] == pytest.approx(5.0)


def test_soil_config_rejects_precipitation_boundary_and_missing_layers():
    with pytest.raises(SoilConfigError):
        validate_soil_config(_soil_config_payload(downloads={"include_next_day_boundary": True}))
    with pytest.raises(SoilConfigError):
        validate_soil_config(_soil_config_payload(variables=["volumetric_soil_water_layer_1"]))
    config = load_soil_config(Path("configs/soil_era5_land.yaml"))
    assert config["dataset_id"] == "plovdiv_soil_2023_2025"
    assert config["downloads"]["include_next_day_boundary"] is False
    assert config["source"]["observation_kind"] == "modeled_volumetric_soil_moisture"


def test_soil_dry_run_skips_boundary_and_retrieve(tmp_path: Path):
    called = []

    def retrieve(*args, **kwargs):
        called.append(args)

    result = download_soil(
        Path("configs/soil_era5_land.yaml"),
        month="2023-01",
        dry_run=True,
        raw_root=tmp_path,
        retrieve=retrieve,
    )
    assert result["status"] == "dry_run"
    assert result["boundary_request"] is None
    assert result["include_next_day_boundary"] is False
    assert "volumetric_soil_water_layer_1" in result["request"]["variable"]
    assert called == []


def test_json_extract_keeps_soil_layers(tmp_path: Path):
    path = tmp_path / "2023-01.json"
    path.write_text(
        '{"hours": [{"timestamp_utc": "2023-01-01T00:00:00Z", "swvl1": 0.3, '
        '"swvl2": 0.28, "swvl3": 0.25, "swvl4": 0.22}], '
        '"spatial": {"method": "nearest_grid_cell", "source_longitude": 24.7, '
        '"source_latitude": 42.1, "distance_km": 4.846579998487036}}',
        encoding="utf-8",
    )
    records, spatial = extract_hourly_records(
        path, bbox=(24.65, 42.05, 24.68, 42.08)
    )
    assert records[0]["swvl1"] == 0.3
    assert spatial["source_longitude"] == 24.7


def test_process_fixture_month_and_incomplete_day(tmp_path: Path):
    import json

    from ml.ingestion.manifest import save_manifest

    config_path = tmp_path / "soil.yaml"
    payload = _soil_config_payload()
    config_path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    hours = _hourly_day("2023-01-01") + _hourly_day("2023-01-02", missing_hour=12)
    raw = tmp_path / "raw" / "plovdiv_soil_test"
    hourly = raw / "hourly"
    hourly.mkdir(parents=True)
    (hourly / "2023-01.json").write_text(json.dumps({
        "hours": hours,
        "spatial": {
            "method": "nearest_grid_cell",
            "source_longitude": 24.7,
            "source_latitude": 42.1,
            "distance_km": 4.846579998487036,
            "query_longitude": 24.665,
            "query_latitude": 42.065,
            "native_resolution_deg": 0.1,
        },
    }), encoding="utf-8")
    save_manifest(raw / "manifest.json", {
        "dataset_id": "plovdiv_soil_test",
        "bbox": [24.65, 42.05, 24.68, 42.08],
        "retrieval_area": [42.20, 24.50, 41.90, 24.90],
        "area_crs": "EPSG:4326",
        "area_name": "plovdiv_test",
        "period": {"start": "2023-01-01", "end": "2023-01-02"},
        "source": {"dataset": "reanalysis-era5-land"},
        "variables": payload["variables"],
        "spatial": {"method": "nearest_grid_cell"},
        "months": {
            "2023-01": {
                "status": "downloaded",
                "filename": "2023-01.json",
                "format": "json",
            }
        },
    })
    result = process_soil_dataset(
        config_path,
        raw_root=tmp_path / "raw",
        processed_root=tmp_path / "processed",
        full_period=True,
    )
    assert result["day_count"] == 2
    assert result["complete_days"] == 1
    assert result["is_ground_truth"] is False
    assert result["suitable_for_modeling"] is False
    daily = (tmp_path / "processed" / "plovdiv_soil_test" / "daily_soil.csv").read_text(encoding="utf-8")
    assert "modeled_volumetric_soil_moisture" in daily
    assert "0.2598" in daily or "0.259" in daily


def test_zero_byte_and_checksum_reuse_weather_safeguards(tmp_path: Path, monkeypatch):
    from ml.ingestion import weather_download
    from ml.ingestion.soil_config import validate_soil_config
    from ml.ingestion.weather_download import download_weather_month

    monkeypatch.setattr(weather_download, "require_cds_auth", lambda: {"configured": True})
    config = validate_soil_config(_soil_config_payload())
    dest_dir = tmp_path / "plovdiv_soil_test" / "hourly"
    dest_dir.mkdir(parents=True)
    existing = dest_dir / "2023-01.nc"
    existing.write_bytes(b"CDF\x01" + b"\x00" * 64)

    def retrieve(dataset, request, target):
        Path(target).write_bytes(b"CDF\x01" + b"\x01" * 64)

    from ml.ingestion.manifest import save_manifest
    save_manifest(tmp_path / "plovdiv_soil_test" / "manifest.json", {
        "dataset_id": "plovdiv_soil_test",
        "bbox": [24.65, 42.05, 24.68, 42.08],
        "retrieval_area": [42.20, 24.50, 41.90, 24.90],
        "area_crs": "EPSG:4326",
        "area_name": "plovdiv_test",
        "period": {"start": "2023-01-01", "end": "2023-01-02"},
        "source": {"dataset": "reanalysis-era5-land"},
        "variables": config["variables"],
        "spatial": config["spatial"],
        "months": {
            "2023-01": {
                "status": "downloaded",
                "filename": "2023-01.nc",
                "checksum": "deadbeef",
            }
        },
    })
    with pytest.raises(WeatherDownloadError, match="checksum"):
        download_weather_month(config, "2023-01", raw_root=tmp_path, retrieve=retrieve)


def test_wetness_generation_from_weather_csv(tmp_path: Path):
    from ml.analysis.weather_timeseries import write_daily_weather
    from ml.ingestion.manifest import save_manifest

    weather_cfg = tmp_path / "weather.yaml"
    weather_cfg.write_text(
        Path("configs/weather_era5_land.yaml").read_text(encoding="utf-8").replace(
            "plovdiv_weather_2023_2025", "wetness_weather_test"
        ).replace("2023-01-01", "2025-04-01").replace("2025-12-31", "2025-04-05"),
        encoding="utf-8",
    )
    processed = tmp_path / "weather" / "wetness_weather_test"
    processed.mkdir(parents=True)
    rows = []
    precip = [0.0, 10.0, 0.0, 0.0, 2.0]
    for index, value in enumerate(precip):
        rows.append({
            "date_utc": f"2025-04-0{index + 1}",
            "aoi_id": "plovdiv_test",
            "precipitation_total_mm": value,
            "evaporation_total_mm": 1.0,
            "temperature_mean_c": 12.0,
            "hourly_records_available": 24,
            "quality_status": "valid",
        })
    write_daily_weather(rows, processed)
    save_manifest(processed / "manifest.json", {"dataset_id": "wetness_weather_test"})
    result = generate_wetness_dataset(
        weather_cfg,
        processed_root=tmp_path / "weather",
        output_root=tmp_path / "wetness",
    )
    assert result["row_count"] == 5
    table = (tmp_path / "wetness" / "wetness_weather_test" / "wetness_indicators.csv").read_text()
    assert "api_k090_mm" in table
    assert "not_estimated" in table
    attached = attach_wetness_features(rows)
    assert attached[1]["api_k090_mm"] == pytest.approx(10.0)
    assert attached[3]["api_k090_mm"] == pytest.approx(8.1)
    assert attached[3]["precip_prev_1d_mm"] == pytest.approx(0.0)
    assert attached[3]["precip_trailing_1d_end_of_day_mm"] == pytest.approx(0.0)


def test_forecast_contract_blocks_reanalysis_and_future_obs():
    base = {
        "forecast_issue_time_utc": "2025-04-10T00:00:00Z",
        "forecast_valid_time_utc": "2025-04-17T00:00:00Z",
        "lead_time_hours": 168,
        "provider": "ecmwf",
        "forecast_model": "ifs",
        "model_version": "unknown",
        "variable": "total_precipitation",
        "unit": "m",
        "source_grid": "0.25deg",
        "retrieved_at_utc": "2026-10-22T00:00:00Z",
        "source_kind": SOURCE_KIND_ARCHIVED_FORECAST,
    }
    ok = validate_forecast_record(base, evaluation_mode=MODE_OPERATIONAL)
    assert ok["oracle_weather_used"] is False
    with pytest.raises(ForecastContractError):
        validate_forecast_record(
            {**base, "source_kind": SOURCE_KIND_REANALYSIS},
            evaluation_mode=MODE_OPERATIONAL,
        )
    with pytest.raises(ForecastContractError):
        validate_forecast_record(
            {**base, "observed_valid_time_utc": "2025-04-17T00:00:00Z"},
            evaluation_mode=MODE_OPERATIONAL,
        )
    perfect = validate_forecast_record(
        {**base, "source_kind": SOURCE_KIND_REANALYSIS},
        evaluation_mode=MODE_PERFECT_WEATHER,
    )
    assert perfect["oracle_weather_used"] is True
    assert target_contract("root_zone_soil_moisture")["ground_truth_allowed"] is False


def test_soilgrids_does_not_fabricate_properties():
    availability = soilgrids_availability()
    assert availability["rest_api_status"] == "paused"
    assert availability["network_executed"] is False
    imported = import_soilgrids_properties()
    assert imported["records"] == []
    assert imported["plant_available_water_status"] == "not_estimated"


def test_source_registry_distinguishes_implemented_and_planned():
    payload = load_source_registry()
    ids = {item["source_id"] for item in payload["sources"]}
    assert "era5_land_soil_water" in ids
    assert "isric_soilgrids" in ids
    soil = next(item for item in payload["sources"] if item["source_id"] == "era5_land_soil_water")
    assert soil["live_download_executed"] is False
    grids = next(item for item in payload["sources"] if item["source_id"] == "isric_soilgrids")
    assert grids["integration_status"] == "paused"


def test_modeled_soil_does_not_flip_supervised_eligibility():
    report = assess_task_readiness(
        quality={
            "validated_observations": 15,
            "observations_by_year": {"2023": 5, "2024": 6, "2025": 4},
            "ground_truth_soil_moisture_available": False,
            "modeled_soil_complete_days": 1096,
            "calibration_consistency": False,
            "coverage": {
                "summary": {
                    "validated_observations": 15,
                    "observations_by_year": {"2023": 5, "2024": 6, "2025": 4},
                    "months_with_validated_observation": 15,
                    "months_in_period": 36,
                    "longest_observation_gap_days": 210,
                }
            },
        }
    )
    assert report["by_task"][TASK_SOIL]["status"] == "not_ready"
    assert report["by_task"][TASK_INDEPENDENT_FIELD]["status"] == "not_ready"
    assert report["by_task"][TASK_SOIL_HISTORICAL]["status"] == "ready"
    assert "missing_ground_truth_soil_moisture" in report["by_task"][TASK_SOIL]["reasons"]


def test_satellite_windows_still_exclude_date_d():
    days = prior_window_dates(date_cls(2025, 4, 10), 7)
    assert days[0] == date_cls(2025, 4, 3)
    assert days[-1] == date_cls(2025, 4, 9)
    assert date_cls(2025, 4, 10) not in days


def test_negative_theta_is_flagged_not_clamped():
    from ml.preprocessing.soil import aggregate_daily_soil, physical_flags

    assert "negative_volumetric_soil_water" in physical_flags(-0.01)
    hours = _hourly_day("2023-01-01", theta=(-0.01, 0.2, 0.2, 0.2))
    rows = aggregate_daily_soil(
        hours,
        period_start="2023-01-01",
        period_end="2023-01-01",
        aoi_id="plovdiv_test",
        source_dataset="reanalysis-era5-land",
        spatial={"source_longitude": 24.7, "source_latitude": 42.1},
    )
    assert rows[0]["swvl1_mean"] == pytest.approx(-0.01)
    assert rows[0]["quality_status"] == "requires_review"


def test_cli_check_and_dry_run():
    assert soil_main(["check", "--config", "configs/soil_era5_land.yaml"]) == 0
    assert soil_main([
        "download",
        "--config",
        "configs/soil_era5_land.yaml",
        "--month",
        "2023-01",
        "--dry-run",
    ]) == 0
    assert soil_main(["sources"]) == 0


def test_soil_weather_alignment_keeps_missing_and_units_separate():
    aligned = align_soil_weather_wetness(
        [{"date_utc": "2023-01-01", "swvl1_mean": 0.3, "theta_root_zone_0_100": 0.26, "complete_day": True}],
        [
            {"date_utc": "2023-01-01", "precipitation_total_mm": 2.0, "observation_kind": "era5_land_reanalysis"},
            {"date_utc": "2023-01-02", "precipitation_total_mm": None, "observation_kind": "missing"},
        ],
        [{"date_utc": "2023-01-01", "api_k090_mm": 2.0}],
    )
    assert [row["date_utc"] for row in aligned] == ["2023-01-01", "2023-01-02"]
    assert aligned[0]["precipitation_total_mm"] == 2.0
    assert aligned[0]["swvl1_mean"] == 0.3
    assert aligned[0]["is_forecast"] is False
    assert aligned[1]["swvl1_mean"] is None
    assert aligned[1]["precipitation_total_mm"] is None
    assert aligned[1]["soil_present"] is False
