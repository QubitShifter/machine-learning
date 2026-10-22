from pathlib import Path

from ml.ingestion.config import load_dataset_config, validate_dataset_config


def test_legacy_timeseries_config_still_valid():
    config = validate_dataset_config({
        "dataset_id": "plovdiv_2025",
        "source": {"collection": "sentinel-2-l2a"},
        "area": {"bbox": [24.65, 42.05, 24.68, 42.08]},
        "period": {"start": "2025-01-01", "end": "2025-12-31"},
    })
    assert config["discovery"]["max_scene_cloud_cover"] == 20.0
    assert config["quality"]["calibration_policy"] == "verified_only"
    assert config["downloads"]["selection_strategy"] == "stratified_seasonal"
    assert config["readiness"]["vegetation_forecast_max_gap_days"] == 90


def test_multiyear_config_file():
    path = Path("configs/satellite_multiyear.yaml")
    config = load_dataset_config(path)
    assert config["dataset_id"] == "plovdiv_2023_2025"
    assert config["period"]["start"] == "2023-01-01"
    assert config["period"]["end"] == "2025-12-31"
    assert config["area"]["bbox"] == (24.65, 42.05, 24.68, 42.08)
    assert config["discovery"]["min_footprint_overlap_pct"] == 95.0
    assert config["quality"]["min_valid_ndvi_pct"] == 70.0
