"""Service layer for local ERA5-Land weather datasets."""

from __future__ import annotations

import re
from pathlib import Path

from backend.app.schemas.weather import (
    DailyWeatherResponse,
    DailyWeatherRow,
    MonthlyWeatherResponse,
    MonthlyWeatherRow,
    SatelliteWeatherResponse,
    SatelliteWeatherRow,
    WeatherDatasetDetailResponse,
    WeatherDatasetListResponse,
    WeatherDatasetSummary,
    WeatherQualityResponse,
    WeatherSummaryResponse,
)
from ml.analysis.weather_timeseries import monthly_weather_summary, read_daily_weather
from ml.ingestion.manifest import read_manifest, validate_safe_id
from ml.ingestion.weather_download import (
    default_weather_processed_root,
    default_weather_raw_root,
    weather_paths,
)
from ml.integration.satellite_weather import default_integration_root
from ml.preprocessing.errors import (
    DatasetNotFoundError,
    InvalidImageIdError,
    InvalidMetadataError,
    MissingProcessedOutputError,
)
from ml.preprocessing.raster import read_json
from ml.preprocessing.weather import _maybe_float


IMAGE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")

RAW_ROOT = default_weather_raw_root()
PROCESSED_ROOT = default_weather_processed_root()
INTEGRATION_ROOT = default_integration_root()


def list_datasets() -> WeatherDatasetListResponse:
    datasets = []
    raw_root = Path(RAW_ROOT)
    if not raw_root.is_dir():
        return WeatherDatasetListResponse(datasets=[])
    for entry in sorted(raw_root.iterdir()):
        if not entry.is_dir() or not (entry / "manifest.json").is_file():
            continue
        try:
            validate_safe_id(entry.name, "dataset_id")
            manifest = read_manifest(entry / "manifest.json")
        except (ValueError, FileNotFoundError):
            continue
        datasets.append(_summary(entry.name, manifest))
    return WeatherDatasetListResponse(datasets=datasets)


def get_dataset(dataset_id: str) -> WeatherDatasetDetailResponse:
    raw = _require_raw_manifest(dataset_id)
    processed = _processed_manifest(dataset_id) or {}
    quality = _quality_payload(dataset_id)
    period = processed.get("period_processed") or raw.get("period")
    return WeatherDatasetDetailResponse(
        dataset_id=dataset_id,
        bbox=raw.get("bbox"),
        period=period,
        timezone="UTC",
        source=raw.get("source"),
        spatial=processed.get("spatial") or raw.get("spatial"),
        variables=list(raw.get("variables") or []),
        day_count=int(processed.get("day_count") or 0),
        complete_days=int(processed.get("complete_days") or 0),
        quality_status=(
            None if quality is None else quality.get("status")
        ) or processed.get("quality_status"),
    )


def get_daily(
    dataset_id: str,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    offset: int = 0,
    limit: int = 100,
) -> DailyWeatherResponse:
    rows = _require_daily(dataset_id)
    filtered = [
        row
        for row in rows
        if _in_range(row.get("date_utc"), start_date, end_date)
    ]
    offset = max(offset, 0)
    limit = min(max(limit, 1), 2000)
    page = filtered[offset:offset + limit]
    return DailyWeatherResponse(
        dataset_id=dataset_id,
        total=len(filtered),
        offset=offset,
        limit=limit,
        records=[DailyWeatherRow.model_validate(item) for item in page],
    )


def get_summary(
    dataset_id: str,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> WeatherSummaryResponse:
    rows = [
        row
        for row in _require_daily(dataset_id)
        if _in_range(row.get("date_utc"), start_date, end_date)
    ]
    observed = [
        row
        for row in rows
        if row.get("hourly_records_available") == 24
        and row.get("boundary_00utc_available")
    ]
    return WeatherSummaryResponse(
        dataset_id=dataset_id,
        start_date=start_date or (rows[0]["date_utc"] if rows else None),
        end_date=end_date or (rows[-1]["date_utc"] if rows else None),
        day_count=len(rows),
        complete_days=len(observed),
        temperature_mean_c=_mean(observed, "temperature_mean_c"),
        temperature_min_c=_min(observed, "temperature_min_c"),
        temperature_max_c=_max(observed, "temperature_max_c"),
        precipitation_total_mm=_sum(observed, "precipitation_total_mm"),
        relative_humidity_mean_pct=_mean(observed, "relative_humidity_mean_pct"),
        wind_speed_mean_ms=_mean(observed, "wind_speed_mean_ms"),
        evaporation_total_mm=_sum(observed, "evaporation_total_mm"),
    )


def get_quality(dataset_id: str) -> WeatherQualityResponse:
    payload = _quality_payload(dataset_id)
    if payload is None:
        raise MissingProcessedOutputError(
            "Weather quality report is not available yet."
        )
    return WeatherQualityResponse(
        dataset_id=dataset_id,
        status=payload.get("status"),
        source_integrity=payload.get("source_integrity"),
        observation_validity=payload.get("observation_validity"),
        period_completeness=payload.get("period_completeness"),
        integration_readiness=payload.get("integration_readiness"),
        daily=payload.get("daily") or {},
        hourly=payload.get("hourly") or {},
        accumulation=payload.get("accumulation") or (payload.get("hourly") or {}).get("accumulation"),
        spatial=payload.get("spatial"),
        coverage=payload.get("coverage"),
        issues=list(payload.get("issues") or []),
    )


def get_monthly(dataset_id: str) -> MonthlyWeatherResponse:
    dataset_id = _validate_id(dataset_id)
    _require_raw_manifest(dataset_id)
    path = Path(PROCESSED_ROOT) / dataset_id / "monthly_summary.csv"
    quality = _quality_payload(dataset_id) or {}
    downloaded = (quality.get("coverage") or {}).get("downloaded_months")
    if path.is_file():
        rows = read_daily_weather(path)
    else:
        rows = monthly_weather_summary(
            _require_daily(dataset_id),
            downloaded_months=downloaded,
        )
    return MonthlyWeatherResponse(
        dataset_id=dataset_id,
        months=[MonthlyWeatherRow.model_validate(item) for item in rows],
    )


def get_chart_path(dataset_id: str) -> Path:
    dataset_id = _validate_id(dataset_id)
    path = Path(PROCESSED_ROOT) / dataset_id / "weather_timeseries.png"
    if not path.is_file():
        raise MissingProcessedOutputError(
            "Weather time-series chart is not available yet."
        )
    return path


def get_satellite_integration(dataset_id: str) -> SatelliteWeatherResponse:
    dataset_id = _validate_id(dataset_id)
    _require_raw_manifest(dataset_id)
    processed = _processed_manifest(dataset_id) or {}
    satellite_id = None
    root = Path(INTEGRATION_ROOT)
    payload = None
    target = None
    if root.is_dir():
        for entry in sorted(root.iterdir()):
            meta_path = entry / "integration_metadata.json"
            csv_path = entry / "satellite_weather.csv"
            if not meta_path.is_file() or not csv_path.is_file():
                continue
            try:
                meta = read_json(meta_path)
            except Exception:
                continue
            if meta.get("weather_dataset_id") == dataset_id:
                payload = meta
                target = csv_path
                satellite_id = meta.get("satellite_dataset_id")
                break
    if payload is None or target is None:
        raise MissingProcessedOutputError(
            "Satellite-weather integration is not available yet."
        )
    rows = read_daily_weather(target)
    return SatelliteWeatherResponse(
        dataset_id=dataset_id,
        satellite_dataset_id=satellite_id,
        weather_dataset_id=dataset_id,
        observation_count=len(rows),
        records=[SatelliteWeatherRow.model_validate(item) for item in rows],
    )


def _summary(dataset_id: str, manifest: dict) -> WeatherDatasetSummary:
    processed = _processed_manifest(dataset_id) or {}
    quality = _quality_payload(dataset_id)
    period = processed.get("period_processed") or manifest.get("period") or {}
    daily = Path(PROCESSED_ROOT) / dataset_id / "daily_weather.csv"
    return WeatherDatasetSummary(
        dataset_id=dataset_id,
        period_start=period.get("start"),
        period_end=period.get("end"),
        day_count=int(processed.get("day_count") or 0),
        complete_days=int(processed.get("complete_days") or 0),
        has_daily=daily.is_file(),
        quality_status=(
            None if quality is None else quality.get("status")
        ) or processed.get("quality_status"),
    )


def _require_raw_manifest(dataset_id: str) -> dict:
    dataset_id = _validate_id(dataset_id)
    path = Path(RAW_ROOT) / dataset_id / "manifest.json"
    if not path.is_file():
        raise DatasetNotFoundError(f"Unknown weather dataset: {dataset_id}")
    try:
        return read_manifest(path)
    except ValueError as exc:
        raise InvalidMetadataError("Weather dataset manifest is invalid.") from exc


def _processed_manifest(dataset_id: str) -> dict | None:
    path = Path(PROCESSED_ROOT) / dataset_id / "manifest.json"
    if not path.is_file():
        return None
    try:
        return read_manifest(path)
    except ValueError:
        return None


def _quality_payload(dataset_id: str) -> dict | None:
    path = Path(PROCESSED_ROOT) / dataset_id / "quality_report.json"
    if not path.is_file():
        return None
    return read_json(path)


def _require_daily(dataset_id: str) -> list[dict]:
    dataset_id = _validate_id(dataset_id)
    _require_raw_manifest(dataset_id)
    path = Path(PROCESSED_ROOT) / dataset_id / "daily_weather.csv"
    if not path.is_file():
        raise MissingProcessedOutputError(
            "Daily weather records are not available yet."
        )
    return read_daily_weather(path)


def _validate_id(dataset_id: str) -> str:
    if not IMAGE_ID_PATTERN.fullmatch(dataset_id or ""):
        raise InvalidImageIdError(
            "Dataset ID must be a local name and cannot contain path separators."
        )
    return dataset_id


def _in_range(value: str | None, start: str | None, end: str | None) -> bool:
    if not value:
        return False
    day = str(value)[:10]
    if start and day < start[:10]:
        return False
    if end and day > end[:10]:
        return False
    return True


def _mean(rows: list[dict], field: str) -> float | None:
    values = [_maybe_float(item.get(field)) for item in rows]
    finite = [value for value in values if value is not None]
    return None if not finite else float(sum(finite) / len(finite))


def _sum(rows: list[dict], field: str) -> float | None:
    values = [_maybe_float(item.get(field)) for item in rows]
    finite = [value for value in values if value is not None]
    return None if not finite else float(sum(finite))


def _min(rows: list[dict], field: str) -> float | None:
    values = [_maybe_float(item.get(field)) for item in rows]
    finite = [value for value in values if value is not None]
    return None if not finite else float(min(finite))


def _max(rows: list[dict], field: str) -> float | None:
    values = [_maybe_float(item.get(field)) for item in rows]
    finite = [value for value in values if value is not None]
    return None if not finite else float(max(finite))
