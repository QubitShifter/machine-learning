from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import soil_service
from ml.analysis.soil_timeseries import write_daily_soil
from ml.ingestion.manifest import save_manifest, write_json_atomic


client = TestClient(app)


def _configure(monkeypatch, tmp_path: Path):
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    wetness = tmp_path / "wetness"
    monkeypatch.setattr(soil_service, "RAW_ROOT", raw)
    monkeypatch.setattr(soil_service, "PROCESSED_ROOT", processed)
    monkeypatch.setattr(soil_service, "WETNESS_ROOT", wetness)
    return raw, processed, wetness


def test_soil_list_detail_daily_and_quality(monkeypatch, tmp_path: Path):
    raw, processed, _wetness = _configure(monkeypatch, tmp_path)
    dataset = raw / "plovdiv_soil_2023_2025"
    dataset.mkdir(parents=True)
    save_manifest(dataset / "manifest.json", {
        "dataset_id": "plovdiv_soil_2023_2025",
        "bbox": [24.65, 42.05, 24.68, 42.08],
        "period": {"start": "2023-01-01", "end": "2023-01-01"},
        "source": {"dataset": "reanalysis-era5-land"},
        "variables": ["volumetric_soil_water_layer_1"],
        "spatial": {"method": "nearest_grid_cell"},
        "months": {},
    })
    out = processed / "plovdiv_soil_2023_2025"
    rows = [{
        "date_utc": "2023-01-01",
        "aoi_id": "plovdiv_test",
        "unit": "m3 m-3",
        "observation_kind": "modeled_volumetric_soil_moisture",
        "is_ground_truth": False,
        "is_measured_soil_moisture": False,
        "swvl1_mean": 0.3,
        "swvl2_mean": 0.28,
        "swvl3_mean": 0.25,
        "swvl4_mean": 0.22,
        "theta_root_zone_0_100": 0.2598,
        "hourly_records_expected": 24,
        "hourly_records_available": 24,
        "complete_day": True,
        "quality_status": "valid",
        "source_dataset": "reanalysis-era5-land",
        "source_grid_id": "42.1,24.7",
    }]
    write_daily_soil(rows, out)
    save_manifest(out / "manifest.json", {
        "dataset_id": "plovdiv_soil_2023_2025",
        "day_count": 1,
        "complete_days": 1,
        "quality_status": "valid",
        "observation_kind": "modeled_volumetric_soil_moisture",
        "is_ground_truth": False,
        "period_processed": {"start": "2023-01-01", "end": "2023-01-01"},
        "spatial": {"source_longitude": 24.7, "source_latitude": 42.1},
    })
    write_json_atomic(out / "quality_report.json", {
        "dataset_id": "plovdiv_soil_2023_2025",
        "status": "valid",
        "observation_kind": "modeled_volumetric_soil_moisture",
        "is_ground_truth": False,
        "suitable_for_modeling": False,
        "modeled_soil_readiness": "limited",
        "daily": {"complete_days": 1, "day_count": 1},
        "hourly": {},
        "quality_notes": ["ERA5-Land soil water is not in-situ ground truth."],
    })

    listing = client.get("/api/v1/soil/datasets")
    assert listing.status_code == 200
    assert listing.json()["datasets"][0]["is_ground_truth"] is False
    detail = client.get("/api/v1/soil/datasets/plovdiv_soil_2023_2025")
    assert detail.status_code == 200
    assert detail.json()["suitable_for_modeling"] is False
    daily = client.get("/api/v1/soil/datasets/plovdiv_soil_2023_2025/daily")
    assert daily.status_code == 200
    assert daily.json()["records"][0]["theta_root_zone_0_100"] == 0.2598
    quality = client.get("/api/v1/soil/datasets/plovdiv_soil_2023_2025/quality")
    assert quality.status_code == 200
    assert quality.json()["is_measured_soil_moisture"] is False
    sources = client.get("/api/v1/soil/sources")
    assert sources.status_code == 200
    assert sources.json()["counts"]["total"] >= 8
    monthly = client.get("/api/v1/soil/datasets/plovdiv_soil_2023_2025/monthly")
    assert monthly.status_code == 200
    assert monthly.json()["aggregation"] == "monthly_mean_of_complete_days"
    assert monthly.json()["months"][0]["swvl1_mean"] == 0.3
    assert monthly.json()["is_ground_truth"] is False


def test_combined_soil_weather_aligns_dates_without_filling_gaps(monkeypatch, tmp_path: Path):
    raw, processed, wetness = _configure(monkeypatch, tmp_path)
    weather = tmp_path / "weather"
    monkeypatch.setattr(soil_service, "WEATHER_ROOT", weather)
    dataset = raw / "plovdiv_soil_2023_2025"
    dataset.mkdir(parents=True)
    save_manifest(dataset / "manifest.json", {
        "dataset_id": "plovdiv_soil_2023_2025",
        "bbox": [24.65, 42.05, 24.68, 42.08],
        "period": {"start": "2023-01-01", "end": "2023-01-03"},
        "source": {"dataset": "reanalysis-era5-land"},
        "variables": ["volumetric_soil_water_layer_1"],
        "spatial": {"method": "nearest_grid_cell"},
        "months": {},
    })
    out = processed / "plovdiv_soil_2023_2025"
    write_daily_soil([
        {
            "date_utc": "2023-01-01",
            "swvl1_mean": 0.30,
            "swvl2_mean": 0.28,
            "swvl3_mean": 0.25,
            "swvl4_mean": 0.22,
            "theta_root_zone_0_100": 0.26,
            "complete_day": True,
            "quality_status": "valid",
            "observation_kind": "modeled_volumetric_soil_moisture",
            "source_grid_id": "42.1,24.7",
        },
        {
            "date_utc": "2023-01-03",
            "swvl1_mean": 0.31,
            "theta_root_zone_0_100": 0.27,
            "complete_day": True,
            "quality_status": "valid",
            "observation_kind": "modeled_volumetric_soil_moisture",
        },
    ], out)
    weather.mkdir()
    (weather / "plovdiv_weather_2023_2025").mkdir()
    (weather / "plovdiv_weather_2023_2025" / "daily_weather.csv").write_text(
        "date_utc,precipitation_total_mm,evaporation_total_mm,observation_kind,quality_status\n"
        "2023-01-01,1.5,0.4,era5_land_reanalysis,valid\n"
        "2023-01-02,,0.3,missing,missing\n",
        encoding="utf-8",
    )
    (wetness / "plovdiv_weather_2023_2025").mkdir(parents=True)
    (wetness / "plovdiv_weather_2023_2025" / "wetness_indicators.csv").write_text(
        "date_utc,api_k090_mm,consecutive_dry_days,precip_minus_evap_7d_mm\n"
        "2023-01-01,1.5,0,\n",
        encoding="utf-8",
    )
    combined = client.get(
        "/api/v1/soil/combined/plovdiv_soil_2023_2025/plovdiv_weather_2023_2025"
    )
    assert combined.status_code == 200
    payload = combined.json()
    assert payload["unit_soil"] == "m3 m-3"
    assert payload["unit_precipitation"] == "mm"
    assert payload["is_ground_truth"] is False
    dates = [row["date_utc"] for row in payload["records"]]
    assert dates == ["2023-01-01", "2023-01-02", "2023-01-03"]
    by_date = {row["date_utc"]: row for row in payload["records"]}
    assert by_date["2023-01-01"]["precipitation_total_mm"] == 1.5
    assert by_date["2023-01-01"]["swvl1_mean"] == 0.3
    assert by_date["2023-01-02"]["precipitation_total_mm"] is None
    assert by_date["2023-01-02"]["swvl1_mean"] is None
    assert by_date["2023-01-02"]["soil_present"] is False
    assert by_date["2023-01-03"]["weather_present"] is False
    assert by_date["2023-01-03"]["precipitation_total_mm"] is None
    assert by_date["2023-01-01"]["is_forecast"] is False
