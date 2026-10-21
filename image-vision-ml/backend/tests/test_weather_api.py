from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import weather_service
from ml.analysis.weather_timeseries import write_daily_weather, write_weather_chart
from ml.ingestion.manifest import save_manifest, write_json_atomic
from ml.integration.satellite_weather import write_integration_outputs


client = TestClient(app)


def _configure(monkeypatch, tmp_path: Path):
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    integration = tmp_path / "integration"
    monkeypatch.setattr(weather_service, "RAW_ROOT", raw)
    monkeypatch.setattr(weather_service, "PROCESSED_ROOT", processed)
    monkeypatch.setattr(weather_service, "INTEGRATION_ROOT", integration)
    return raw, processed, integration


def _seed(raw: Path, processed: Path, integration: Path) -> None:
    dataset = raw / "plovdiv_weather_2023_2025"
    dataset.mkdir(parents=True)
    save_manifest(dataset / "manifest.json", {
        "dataset_id": "plovdiv_weather_2023_2025",
        "bbox": [24.65, 42.05, 24.68, 42.08],
        "period": {"start": "2025-04-01", "end": "2025-04-03"},
        "source": {"dataset": "reanalysis-era5-land"},
        "variables": ["2m_temperature", "total_precipitation"],
        "spatial": {"method": "nearest_grid_cell"},
        "months": {},
    })
    rows = [
        {
            "date_utc": "2025-04-01",
            "aoi_id": "plovdiv_test",
            "temperature_mean_c": 10.0,
            "temperature_min_c": 6.0,
            "temperature_max_c": 14.0,
            "dewpoint_mean_c": 4.0,
            "relative_humidity_mean_pct": 65.0,
            "precipitation_total_mm": 2.0,
            "wind_speed_mean_ms": 3.0,
            "evaporation_total_mm": 1.0,
            "hourly_records_expected": 24,
            "hourly_records_available": 24,
            "boundary_00utc_available": True,
            "quality_status": "valid",
            "source_dataset": "reanalysis-era5-land",
            "source_grid_id": "42.1,24.7",
        },
        {
            "date_utc": "2025-04-02",
            "aoi_id": "plovdiv_test",
            "temperature_mean_c": 12.0,
            "temperature_min_c": 7.0,
            "temperature_max_c": 16.0,
            "dewpoint_mean_c": 5.0,
            "relative_humidity_mean_pct": 60.0,
            "precipitation_total_mm": 0.0,
            "wind_speed_mean_ms": 2.0,
            "evaporation_total_mm": 1.5,
            "hourly_records_expected": 24,
            "hourly_records_available": 24,
            "boundary_00utc_available": True,
            "quality_status": "valid",
            "source_dataset": "reanalysis-era5-land",
            "source_grid_id": "42.1,24.7",
        },
        {
            "date_utc": "2025-04-03",
            "aoi_id": "plovdiv_test",
            "temperature_mean_c": None,
            "precipitation_total_mm": None,
            "hourly_records_expected": 24,
            "hourly_records_available": 0,
            "boundary_00utc_available": False,
            "quality_status": "rejected",
            "source_dataset": "reanalysis-era5-land",
            "source_grid_id": "42.1,24.7",
        },
    ]
    out = processed / "plovdiv_weather_2023_2025"
    write_daily_weather(rows, out)
    write_weather_chart(rows, out / "weather_timeseries.png")
    save_manifest(out / "manifest.json", {
        "dataset_id": "plovdiv_weather_2023_2025",
        "period_processed": {"start": "2025-04-01", "end": "2025-04-03"},
        "day_count": 3,
        "complete_days": 2,
        "quality_status": "warning",
        "spatial": {"method": "nearest_grid_cell", "source_latitude": 42.1},
    })
    write_json_atomic(out / "quality_report.json", {
        "dataset_id": "plovdiv_weather_2023_2025",
        "status": "warning",
        "daily": {"day_count": 3, "complete_days": 2, "missing_days": 1},
        "hourly": {"hourly_records": 48, "status": "valid"},
        "spatial": {"method": "nearest_grid_cell"},
    })
    write_integration_outputs(
        [{
            "satellite_dataset_id": "plovdiv_2023_2025",
            "weather_dataset_id": "plovdiv_weather_2023_2025",
            "scene_id": "S2B_35TLG_20250421_1_L2A",
            "observation_date_utc": "2025-04-21",
            "ndvi_mean": 0.42,
            "precip_prev_7d_mm": 4.0,
            "precip_prev_14d_mm": 8.0,
            "precip_prev_30d_mm": 12.0,
            "temp_mean_prev_7d_c": 11.0,
            "temp_mean_prev_30d_c": 10.0,
            "dry_days_prev_30d": 18,
            "rh_mean_prev_7d_pct": 62.0,
            "wind_mean_prev_7d_ms": 2.5,
            "window_7d_complete": True,
            "window_14d_complete": True,
            "window_30d_complete": False,
        }],
        integration / "plovdiv_2023_2025",
        metadata={
            "satellite_dataset_id": "plovdiv_2023_2025",
            "weather_dataset_id": "plovdiv_weather_2023_2025",
            "observation_count": 1,
        },
    )


def test_weather_dataset_discovery_and_detail(monkeypatch, tmp_path: Path):
    raw, processed, integration = _configure(monkeypatch, tmp_path)
    _seed(raw, processed, integration)

    listing = client.get("/api/v1/weather/datasets")
    assert listing.status_code == 200
    assert listing.json()["datasets"][0]["dataset_id"] == "plovdiv_weather_2023_2025"

    detail = client.get("/api/v1/weather/datasets/plovdiv_weather_2023_2025")
    assert detail.status_code == 200
    assert detail.json()["bbox"] == [24.65, 42.05, 24.68, 42.08]
    assert detail.json()["day_count"] == 3


def test_daily_filter_pagination_summary_quality_chart(monkeypatch, tmp_path: Path):
    raw, processed, integration = _configure(monkeypatch, tmp_path)
    _seed(raw, processed, integration)

    daily = client.get(
        "/api/v1/weather/datasets/plovdiv_weather_2023_2025/daily",
        params={"start_date": "2025-04-01", "end_date": "2025-04-02", "limit": 1, "offset": 1},
    )
    assert daily.status_code == 200
    payload = daily.json()
    assert payload["total"] == 2
    assert payload["records"][0]["date_utc"] == "2025-04-02"

    summary = client.get("/api/v1/weather/datasets/plovdiv_weather_2023_2025/summary")
    assert summary.status_code == 200
    assert summary.json()["day_count"] == 3
    assert summary.json()["precipitation_total_mm"] == 2.0

    quality = client.get("/api/v1/weather/datasets/plovdiv_weather_2023_2025/quality")
    assert quality.status_code == 200
    assert quality.json()["daily"]["complete_days"] == 2

    monthly = client.get("/api/v1/weather/datasets/plovdiv_weather_2023_2025/monthly")
    assert monthly.status_code == 200
    months = monthly.json()["months"]
    assert months[0]["month"] == "2025-04"
    assert months[0]["complete_days"] == 2
    assert months[0]["precipitation_total_mm"] == 2.0

    chart = client.get("/api/v1/weather/datasets/plovdiv_weather_2023_2025/chart")
    assert chart.status_code == 200
    assert chart.headers["content-type"].startswith("image/png")

    joined = client.get(
        "/api/v1/weather/datasets/plovdiv_weather_2023_2025/satellite-integration"
    )
    assert joined.status_code == 200
    assert joined.json()["records"][0]["precip_prev_7d_mm"] == 4.0


def test_unknown_and_invalid_weather_dataset(monkeypatch, tmp_path: Path):
    _configure(monkeypatch, tmp_path)
    assert client.get("/api/v1/weather/datasets/missing").status_code == 404
    response = client.get("/api/v1/weather/datasets/../secret")
    assert response.status_code in {400, 404, 422}


def test_existing_satellite_endpoints_and_swagger_include_weather():
    assert client.get("/health").status_code == 200
    assert client.get("/api").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/satellite/images" in paths
    assert "/api/v1/satellite/datasets" in paths
    assert "/api/v1/weather/datasets" in paths
    assert "/api/v1/weather/datasets/{dataset_id}/daily" in paths
    assert "/api/v1/weather/datasets/{dataset_id}/monthly" in paths
    assert "/api/v1/weather/datasets/{dataset_id}/summary" in paths
    assert "/api/v1/weather/datasets/{dataset_id}/quality" in paths
    assert "/api/v1/weather/datasets/{dataset_id}/chart" in paths
    assert "/api/v1/weather/datasets/{dataset_id}/satellite-integration" in paths
