from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import integration_service
from ml.integration.features import feature_metadata
from ml.integration.satellite_weather import write_integration_outputs


client = TestClient(app)


def _configure(monkeypatch, tmp_path: Path) -> Path:
    root = tmp_path / "integration"
    monkeypatch.setattr(integration_service, "INTEGRATION_ROOT", root)
    return root


def _seed(root: Path) -> None:
    rows = [
        {
            "satellite_dataset_id": "plovdiv_2023_2025",
            "weather_dataset_id": "plovdiv_weather_2023_2025",
            "scene_id": "S2A_35TLG_20250421_0_L2A",
            "acquisition_timestamp_utc": "2025-04-21T09:18:47Z",
            "observation_date_utc": "2025-04-21",
            "ndvi_mean": 0.42,
            "precip_prev_7d_mm": 4.0,
            "precip_prev_14d_mm": None,
            "precip_prev_30d_mm": None,
            "window_7d_complete": True,
            "window_14d_complete": False,
            "window_30d_complete": False,
            "window_7d_observed_days": 7,
            "window_14d_observed_days": 4,
            "window_30d_observed_days": 4,
            "weather_feature_window_complete": False,
            "satellite_observation_valid": True,
            "integrated_observation_complete": False,
            "suitable_for_modeling": False,
            "quality_warnings": "incomplete_weather_window_14d;incomplete_weather_window_30d",
        },
        {
            "satellite_dataset_id": "plovdiv_2023_2025",
            "weather_dataset_id": "plovdiv_weather_2023_2025",
            "scene_id": "S2B_35TLG_20230722_0_L2A",
            "acquisition_timestamp_utc": "2023-07-22T09:06:11Z",
            "observation_date_utc": "2023-07-22",
            "ndvi_mean": 0.59,
            "precip_prev_7d_mm": 8.0,
            "precip_prev_14d_mm": 12.0,
            "precip_prev_30d_mm": 20.0,
            "window_7d_complete": True,
            "window_14d_complete": True,
            "window_30d_complete": True,
            "window_7d_observed_days": 7,
            "window_14d_observed_days": 14,
            "window_30d_observed_days": 30,
            "weather_feature_window_complete": True,
            "satellite_observation_valid": True,
            "integrated_observation_complete": True,
            "suitable_for_modeling": False,
            "quality_warnings": "",
        },
    ]
    write_integration_outputs(
        rows,
        root / "plovdiv_2023_2025",
        metadata={
            "satellite_dataset_id": "plovdiv_2023_2025",
            "weather_dataset_id": "plovdiv_weather_2023_2025",
            "observation_count": 2,
            "integration_version": "3.2.0",
            "leakage_policy": "previous_completed_utc_days_only",
            "same_day_weather": "excluded",
            "windows_days": [7, 14, 30],
            "integrated_observation_complete_count": 1,
            "weather_feature_window_complete_count": 1,
            "suitable_for_modeling_count": 0,
        },
        quality={
            "satellite_dataset_id": "plovdiv_2023_2025",
            "weather_dataset_id": "plovdiv_weather_2023_2025",
            "observation_count": 2,
            "satellite_observation_valid_count": 2,
            "weather_observation_valid_count": 2,
            "weather_feature_window_complete_count": 1,
            "integrated_observation_complete_count": 1,
            "suitable_for_modeling_count": 0,
            "window_7d_complete_count": 2,
            "window_14d_complete_count": 1,
            "window_30d_complete_count": 1,
            "issues": [],
            "leakage_policy": "previous_completed_utc_days_only",
            "same_day_weather": "excluded",
        },
        catalog=feature_metadata(),
    )


def test_integration_api_lists_filters_and_serializes_missing(monkeypatch, tmp_path: Path):
    root = _configure(monkeypatch, tmp_path)
    _seed(root)

    listing = client.get("/api/v1/integration/datasets")
    assert listing.status_code == 200
    assert listing.json()["datasets"][0]["dataset_id"] == "plovdiv_2023_2025"

    detail = client.get("/api/v1/integration/datasets/plovdiv_2023_2025")
    assert detail.status_code == 200
    assert detail.json()["leakage_policy"] == "previous_completed_utc_days_only"
    assert "data/" not in str(detail.json())

    missing = client.get(
        "/api/v1/integration/datasets/plovdiv_2023_2025/observations",
        params={"scene_id": "S2A_35TLG_20250421_0_L2A"},
    )
    assert missing.status_code == 200
    record = missing.json()["records"][0]
    assert record["precip_prev_14d_mm"] is None
    assert record["precip_prev_7d_mm"] == 4.0
    assert record["suitable_for_modeling"] is False
    assert "incomplete_weather_window_30d" in record["quality_warnings"]

    complete = client.get(
        "/api/v1/integration/datasets/plovdiv_2023_2025/observations",
        params={"availability": "complete"},
    )
    assert complete.json()["total"] == 1
    assert complete.json()["records"][0]["scene_id"] == "S2B_35TLG_20230722_0_L2A"

    ranged = client.get(
        "/api/v1/integration/datasets/plovdiv_2023_2025/observations",
        params={"start_date": "2025-01-01", "end_date": "2025-12-31"},
    )
    assert ranged.json()["total"] == 1

    quality = client.get("/api/v1/integration/datasets/plovdiv_2023_2025/quality")
    assert quality.status_code == 200
    assert quality.json()["suitable_for_modeling_count"] == 0
    assert "data/" not in str(quality.json())

    features = client.get("/api/v1/integration/datasets/plovdiv_2023_2025/features")
    assert features.status_code == 200
    ids = {item["id"] for item in features.json()["features"]}
    assert "precip_prev_7d_mm" in ids
    assert features.json()["same_day_weather"] == "excluded"


def test_integration_openapi_and_invalid_ids(monkeypatch, tmp_path: Path):
    _configure(monkeypatch, tmp_path)
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/integration/datasets" in paths
    assert "/api/v1/integration/datasets/{dataset_id}/observations" in paths
    assert "/api/v1/integration/datasets/{dataset_id}/quality" in paths
    assert "/api/v1/integration/datasets/{dataset_id}/features" in paths
    assert client.get("/api/v1/integration/datasets/missing").status_code == 404
    assert client.get("/api/v1/integration/datasets/../secret").status_code in {400, 404, 422}
