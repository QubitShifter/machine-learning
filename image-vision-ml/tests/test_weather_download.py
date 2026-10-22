from pathlib import Path

import pytest
import yaml

from ml.ingestion.era5_land import detect_file_format
from ml.ingestion.weather_config import load_weather_config, validate_weather_config
from ml.ingestion.weather_download import (
    download_weather_month,
    download_weather_range,
)
from scripts.weather_dataset import main
from ml.ingestion.weather_pipeline import (
    check_weather_config,
    process_weather_dataset,
    weather_status,
)
from ml.preprocessing.errors import (
    CdsAuthenticationError,
    PermanentCdsRequestError,
    WeatherDownloadError,
)


def _config():
    return validate_weather_config({
        "dataset_id": "plovdiv_weather_test",
        "source": {"dataset": "reanalysis-era5-land"},
        "area": {"name": "plovdiv_test", "bbox": [24.65, 42.05, 24.68, 42.08]},
        "period": {"start": "2025-04-01", "end": "2025-04-02"},
        "variables": [
            "2m_temperature",
            "2m_dewpoint_temperature",
            "total_precipitation",
            "10m_u_component_of_wind",
            "10m_v_component_of_wind",
            "total_evaporation",
        ],
        "downloads": {"retries": 3},
    })


def test_dry_run_does_not_call_retrieve(tmp_path: Path):
    called = []

    def retrieve(*args, **kwargs):
        called.append(args)

    result = download_weather_month(
        _config(),
        "2025-04",
        dry_run=True,
        raw_root=tmp_path,
        retrieve=retrieve,
    )
    assert result["status"] == "dry_run"
    assert result["request"]["month"] == ["04"]
    assert result["boundary_request"]["month"] == ["05"]
    assert result["study_aoi"] == [24.65, 42.05, 24.68, 42.08]
    assert result["retrieval_area"] == result["request"]["area"]
    assert result["request"]["area"] != [42.08, 24.65, 42.05, 24.68]
    assert result["boundary_request"]["area"] == result["request"]["area"]
    assert called == []


def test_dry_run_uses_configured_retrieval_area():
    config = load_weather_config(Path("configs/weather_era5_land.yaml"))
    result = download_weather_month(config, "2025-04", dry_run=True)
    assert result["study_aoi"] == [24.65, 42.05, 24.68, 42.08]
    assert result["retrieval_area"] == [42.20, 24.50, 41.90, 24.90]
    assert result["request"]["area"] == [42.20, 24.50, 41.90, 24.90]
    assert result["boundary_request"]["area"] == [42.20, 24.50, 41.90, 24.90]
    assert result["boundary_request"]["month"] == ["05"]
    assert result["boundary_request"]["day"] == ["01"]


def test_missing_credentials_block_live_download(monkeypatch, tmp_path: Path):
    from ml.ingestion import weather_download

    def missing():
        raise CdsAuthenticationError("CDS credentials are not configured.")

    monkeypatch.setattr(weather_download, "require_cds_auth", missing)
    with pytest.raises(CdsAuthenticationError):
        download_weather_month(_config(), "2025-04", raw_root=tmp_path, retrieve=lambda *a: None)


def _write_netcdf_header(path: Path) -> None:
    path.write_bytes(b"CDF\x01" + b"\x00" * 32)


def test_mocked_download_resume_and_manifest(monkeypatch, tmp_path: Path):
    from ml.ingestion import weather_download

    monkeypatch.setattr(weather_download, "require_cds_auth", lambda: {"configured": True})
    calls = []

    def retrieve(dataset, request, target):
        calls.append((dataset, request["month"], request["day"], request["time"]))
        _write_netcdf_header(Path(target))

    first = download_weather_month(
        _config(),
        "2025-04",
        raw_root=tmp_path,
        retrieve=retrieve,
    )
    assert first["status"] == "downloaded"
    assert first["filename"] == "2025-04.nc"
    assert first["format"] == "netcdf"
    second = download_weather_month(
        _config(),
        "2025-04",
        raw_root=tmp_path,
        retrieve=retrieve,
    )
    assert second["status"] == "skipped"
    assert len(calls) == 2
    manifest = (tmp_path / "plovdiv_weather_test" / "manifest.json")
    payload = manifest.read_text(encoding="utf-8")
    assert "key" not in payload.lower() or "checksum" in payload
    assert "SUPER_SECRET" not in payload
    assert '"status": "downloaded"' in payload


def test_retry_then_success(monkeypatch, tmp_path: Path):
    from ml.ingestion import weather_download

    monkeypatch.setattr(weather_download, "require_cds_auth", lambda: {"configured": True})
    monkeypatch.setattr(weather_download.time, "sleep", lambda *_: None)
    attempts = {"n": 0}

    def retrieve(dataset, request, target):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise RuntimeError("CDS queued then failed")
        _write_netcdf_header(Path(target))

    result = download_weather_month(
        _config(),
        "2025-04",
        raw_root=tmp_path,
        retrieve=retrieve,
    )
    assert result["status"] == "downloaded"
    assert attempts["n"] >= 3


def test_permanent_spatial_error_is_not_retried(monkeypatch, tmp_path: Path):
    from ml.ingestion import weather_download

    monkeypatch.setattr(weather_download, "require_cds_auth", lambda: {"configured": True})
    monkeypatch.setattr(weather_download.time, "sleep", lambda *_: None)
    attempts = {"n": 0}

    def retrieve(dataset, request, target):
        attempts["n"] += 1
        raise RuntimeError(
            "HTTP 400: MultiAdaptorNoDataError: Area: non-empty area crop/mask"
        )

    with pytest.raises(PermanentCdsRequestError):
        download_weather_month(_config(), "2025-04", raw_root=tmp_path, retrieve=retrieve)
    assert attempts["n"] == 1


def test_corrupt_and_invalid_format(monkeypatch, tmp_path: Path):
    from ml.ingestion import weather_download

    monkeypatch.setattr(weather_download, "require_cds_auth", lambda: {"configured": True})
    monkeypatch.setattr(weather_download.time, "sleep", lambda *_: None)

    def retrieve(dataset, request, target):
        Path(target).write_bytes(b"not-weather")

    with pytest.raises(WeatherDownloadError):
        download_weather_month(_config(), "2025-04", raw_root=tmp_path, retrieve=retrieve)
    with pytest.raises(WeatherDownloadError):
        detect_file_format(tmp_path / "empty.bin") if False else detect_file_format(
            _write_invalid(tmp_path)
        )


def _write_invalid(tmp_path: Path) -> Path:
    path = tmp_path / "invalid.bin"
    path.write_bytes(b"not-weather")
    return path


def test_process_json_fixtures_and_check_command(tmp_path: Path):
    config_path = tmp_path / "weather.yaml"
    config_path.write_text(
        yaml.safe_dump({
            "dataset_id": "fixture_weather",
            "source": {"dataset": "reanalysis-era5-land"},
            "area": {"name": "plovdiv_test", "bbox": [24.65, 42.05, 24.68, 42.08]},
            "period": {"start": "2025-04-01", "end": "2025-04-01"},
            "variables": [
                "2m_temperature",
                "2m_dewpoint_temperature",
                "total_precipitation",
                "10m_u_component_of_wind",
                "10m_v_component_of_wind",
                "total_evaporation",
            ],
        }),
        encoding="utf-8",
    )
    check = check_weather_config(config_path, cds_config_path=tmp_path / "missing")
    assert check["authentication"]["configured"] is False
    assert main(["check", "--config", str(config_path)]) == 0
    assert main([
        "download",
        "--config",
        str(config_path),
        "--month",
        "2025-04",
        "--dry-run",
    ]) == 0

    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    hourly = raw / "fixture_weather" / "hourly"
    hourly.mkdir(parents=True)
    import json
    from datetime import datetime, timezone

    hours = []
    for hour in range(24):
        hours.append({
            "timestamp_utc": datetime(2025, 4, 1, hour, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
            "t2m": 283.15,
            "d2m": 278.15,
            "u10": 0.0,
            "v10": 1.0,
            "tp": 0.001 * hour,
            "e": -0.0001 * hour,
        })
    hours.append({
        "timestamp_utc": "2025-04-02T00:00:00Z",
        "t2m": 284.15,
        "d2m": 279.15,
        "u10": 0.0,
        "v10": 1.0,
        "tp": 0.006,
        "e": -0.002,
    })
    (hourly / "2025-04.json").write_text(
        json.dumps({
            "hours": hours,
            "spatial": {
                "method": "nearest_grid_cell",
                "source_latitude": 42.1,
                "source_longitude": 24.7,
                "native_resolution_deg": 0.1,
            },
        }),
        encoding="utf-8",
    )
    from ml.ingestion.manifest import save_manifest

    save_manifest(raw / "fixture_weather" / "manifest.json", {
        "dataset_id": "fixture_weather",
        "area": {"name": "plovdiv_test", "bbox": [24.65, 42.05, 24.68, 42.08]},
        "period": {"start": "2025-04-01", "end": "2025-04-01"},
        "source": {"dataset": "reanalysis-era5-land"},
        "variables": [],
        "months": {
            "2025-04": {
                "status": "downloaded",
                "filename": "2025-04.json",
            }
        },
    })
    result = process_weather_dataset(
        config_path,
        raw_root=raw,
        processed_root=processed,
        full_period=True,
    )
    assert result["day_count"] == 1
    assert result["complete_days"] == 1
    daily = (processed / "fixture_weather" / "daily_weather.csv").read_text(encoding="utf-8")
    assert "2025-04-01" in daily
    assert "6.0" in daily or "6" in daily
    assert "2025-04" in result["coverage"]["downloaded_months"]


def test_range_dry_run_does_not_contact_cds_or_overwrite(monkeypatch, tmp_path: Path):
    from ml.ingestion import weather_download

    monkeypatch.setattr(weather_download, "require_cds_auth", lambda: {"configured": True})
    calls = []

    def retrieve(dataset, request, target):
        calls.append(request["month"])
        _write_netcdf_header(Path(target))

    download_weather_month(_config(), "2025-04", raw_root=tmp_path, retrieve=retrieve)
    april_path = tmp_path / "plovdiv_weather_test" / "hourly" / "2025-04.nc"
    checksum = april_path.read_bytes()
    plan = download_weather_range(
        _config(),
        start_month="2025-03",
        end_month="2025-05",
        dry_run=True,
        raw_root=tmp_path,
        retrieve=retrieve,
    )
    by_month = {item["month"]: item for item in plan["months"]}
    assert plan["execute"] is False
    assert plan["study_aoi"] == [24.65, 42.05, 24.68, 42.08]
    assert by_month["2025-04"]["action"] == "skip"
    assert by_month["2025-03"]["action"] == "download"
    assert by_month["2025-05"]["action"] == "download"
    assert by_month["2025-04"]["boundary_date"] == "2025-05-01"
    assert calls == [["04"], ["05"]]
    assert april_path.read_bytes() == checksum


def test_range_without_resume_is_refused(tmp_path: Path):
    with pytest.raises(WeatherDownloadError, match="--resume"):
        download_weather_range(
            _config(),
            start_month="2025-03",
            end_month="2025-04",
            dry_run=False,
            resume=False,
            raw_root=tmp_path,
            retrieve=lambda *a: None,
        )


def test_resume_skips_complete_and_downloads_pending(monkeypatch, tmp_path: Path):
    from ml.ingestion import weather_download

    monkeypatch.setattr(weather_download, "require_cds_auth", lambda: {"configured": True})
    calls = []

    def retrieve(dataset, request, target):
        calls.append((request["year"][0], request["month"][0], request["day"]))
        _write_netcdf_header(Path(target))

    download_weather_month(_config(), "2025-04", raw_root=tmp_path, retrieve=retrieve)
    april = tmp_path / "plovdiv_weather_test" / "hourly" / "2025-04.nc"
    original = april.read_bytes()
    result = download_weather_range(
        _config(),
        start_month="2025-04",
        end_month="2025-05",
        resume=True,
        raw_root=tmp_path,
        retrieve=retrieve,
    )
    statuses = {item.get("month") or item.get("status"): item.get("status") for item in result["results"]}
    assert any(item.get("month") == "2025-04" and item.get("status") == "skipped" for item in result["results"])
    assert any(item.get("month") == "2025-05" and item.get("status") == "downloaded" for item in result["results"])
    assert april.read_bytes() == original
    assert ("2025", "04") not in {(year, month) for year, month, _ in calls[2:]}


def test_empty_files_are_replaceable_but_complete_files_are_not(monkeypatch, tmp_path: Path):
    from ml.ingestion import weather_download
    from ml.ingestion.weather_download import _commit_downloaded_file, month_integrity

    monkeypatch.setattr(weather_download, "require_cds_auth", lambda: {"configured": True})
    hourly_dir = tmp_path / "hourly"
    hourly_dir.mkdir()
    empty = hourly_dir / "2024-07.boundary.nc"
    empty.write_bytes(b"")
    integrity = month_integrity(
        hourly_dir,
        {"filename": "2024-07.nc", "boundary_filename": "2024-07.boundary.nc"},
        require_boundary=True,
    )
    assert "empty_boundary_file" in integrity["reasons"] or "missing_hourly_file" in integrity["reasons"]
    replacement = hourly_dir / "2024-07.boundary.download"
    _write_netcdf_header(replacement)
    _commit_downloaded_file(replacement, empty)
    assert empty.stat().st_size > 0

    complete = hourly_dir / "2024-07.nc"
    _write_netcdf_header(complete)
    incoming = hourly_dir / "2024-07.download"
    _write_netcdf_header(incoming)
    with pytest.raises(WeatherDownloadError, match="Refusing to overwrite"):
        _commit_downloaded_file(incoming, complete)

    empty_hourly = hourly_dir / "2024-08.nc"
    empty_hourly.write_bytes(b"")
    record = {"filename": "2024-08.nc", "status": "downloaded", "checksum": "abc"}
    empty_integrity = month_integrity(hourly_dir, record, require_boundary=False)
    assert empty_integrity["complete"] is False
    assert "empty_hourly_file" in empty_integrity["reasons"]
    assert "invalid_format" not in empty_integrity["reasons"]


def test_checksum_mismatch_is_not_overwritten(monkeypatch, tmp_path: Path):
    from ml.ingestion import weather_download

    monkeypatch.setattr(weather_download, "require_cds_auth", lambda: {"configured": True})
    download_weather_month(
        _config(),
        "2025-04",
        raw_root=tmp_path,
        retrieve=lambda dataset, request, target: _write_netcdf_header(Path(target)),
    )
    hourly = tmp_path / "plovdiv_weather_test" / "hourly" / "2025-04.nc"
    hourly.write_bytes(b"CDF\x01" + b"\xff" * 32)
    with pytest.raises(WeatherDownloadError, match="Refusing to overwrite"):
        download_weather_month(
            _config(),
            "2025-04",
            raw_root=tmp_path,
            retrieve=lambda dataset, request, target: _write_netcdf_header(Path(target)),
        )


def test_status_and_cli_dry_run_plan():
    status = weather_status(Path("configs/weather_era5_land.yaml"))
    assert status["study_aoi"] == [24.65, 42.05, 24.68, 42.08]
    assert status["retrieval_area"] == [42.20, 24.50, 41.90, 24.90]
    assert status["month_count"] == 36
    assert status["counts"]["downloaded"] >= 1
    assert sum(status["counts"].values()) == 36
    downloaded = [
        item["month"]
        for item in status["months"]
        if item["action"] == "skip"
    ]
    assert "2025-04" in downloaded
    april = next(item for item in status["months"] if item["month"] == "2025-04")
    assert april["action"] == "skip"
    assert main(["status", "--config", "configs/weather_era5_land.yaml"]) == 0
    assert main([
        "download",
        "--config",
        "configs/weather_era5_land.yaml",
        "--start-month",
        "2023-01",
        "--end-month",
        "2025-12",
        "--dry-run",
    ]) == 0
