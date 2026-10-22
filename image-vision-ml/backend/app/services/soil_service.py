"""Service layer for modeled ERA5-Land soil-moisture datasets."""

from __future__ import annotations

import re
from pathlib import Path

from backend.app.schemas.soil import (
    CombinedSoilWeatherResponse,
    CombinedSoilWeatherRow,
    DailySoilResponse,
    DailySoilRow,
    MonthlySoilResponse,
    MonthlySoilRow,
    SoilDatasetDetailResponse,
    SoilDatasetListResponse,
    SoilDatasetSummary,
    SoilQualityResponse,
    SourceRegistryResponse,
    WetnessResponse,
    WetnessRow,
)
from ml.analysis.soil_timeseries import monthly_soil_summary, read_daily_soil
from ml.analysis.soil_weather import align_soil_weather_wetness
from ml.analysis.weather_timeseries import read_daily_weather
from ml.ingestion.manifest import read_manifest, validate_safe_id
from ml.ingestion.soil_pipeline import (
    default_soil_processed_root,
    default_soil_raw_root,
    default_wetness_processed_root,
    soil_paths,
)
from ml.ingestion.weather_download import default_weather_processed_root
from ml.preprocessing.errors import (
    DatasetNotFoundError,
    InvalidImageIdError,
    MissingProcessedOutputError,
)
from ml.preprocessing.raster import read_json
from ml.sources.registry import load_source_registry


IMAGE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")

RAW_ROOT = default_soil_raw_root()
PROCESSED_ROOT = default_soil_processed_root()
WETNESS_ROOT = default_wetness_processed_root()
WEATHER_ROOT = default_weather_processed_root()


def list_datasets() -> SoilDatasetListResponse:
    datasets = []
    raw_root = Path(RAW_ROOT)
    if not raw_root.is_dir():
        return SoilDatasetListResponse(datasets=[])
    for entry in sorted(raw_root.iterdir()):
        if not entry.is_dir() or not (entry / "manifest.json").is_file():
            continue
        try:
            validate_safe_id(entry.name, "dataset_id")
            manifest = read_manifest(entry / "manifest.json")
        except (ValueError, FileNotFoundError):
            continue
        datasets.append(_summary(entry.name, manifest))
    return SoilDatasetListResponse(datasets=datasets)


def get_dataset(dataset_id: str) -> SoilDatasetDetailResponse:
    raw = _require_raw_manifest(dataset_id)
    processed = _processed_manifest(dataset_id) or {}
    quality = _quality_payload(dataset_id)
    period = processed.get("period_processed") or raw.get("period")
    return SoilDatasetDetailResponse(
        dataset_id=dataset_id,
        bbox=raw.get("bbox"),
        period=period,
        timezone="UTC",
        source=raw.get("source"),
        spatial=processed.get("spatial") or raw.get("spatial"),
        variables=list(raw.get("variables") or []),
        layers=(quality or {}).get("layers") or raw.get("layers"),
        day_count=int(processed.get("day_count") or 0),
        complete_days=int(processed.get("complete_days") or 0),
        quality_status=(None if quality is None else quality.get("status"))
        or processed.get("quality_status"),
        observation_kind=processed.get("observation_kind")
        or (None if quality is None else quality.get("observation_kind")),
        is_ground_truth=False,
        is_measured_soil_moisture=False,
        suitable_for_modeling=False,
    )


def get_daily(
    dataset_id: str,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    offset: int = 0,
    limit: int = 100,
) -> DailySoilResponse:
    rows = _require_daily(dataset_id)
    filtered = [row for row in rows if _in_range(row.get("date_utc"), start_date, end_date)]
    offset = max(offset, 0)
    limit = min(max(limit, 1), 2000)
    page = filtered[offset:offset + limit]
    return DailySoilResponse(
        dataset_id=dataset_id,
        total=len(filtered),
        offset=offset,
        limit=limit,
        records=[DailySoilRow.model_validate(item) for item in page],
        is_ground_truth=False,
    )


def get_monthly(dataset_id: str) -> MonthlySoilResponse:
    rows = _require_daily(dataset_id)
    path = Path(PROCESSED_ROOT) / dataset_id / "monthly_summary.csv"
    if path.is_file():
        monthly = read_daily_weather(path)
    else:
        monthly = monthly_soil_summary(rows)
    records = []
    for item in monthly:
        payload = dict(item)
        payload["aggregation"] = "monthly_mean_of_complete_days"
        payload["unit"] = "m3 m-3"
        payload["observation_kind"] = "modeled_volumetric_soil_moisture"
        records.append(MonthlySoilRow.model_validate(payload))
    return MonthlySoilResponse(dataset_id=dataset_id, months=records)


def get_combined(
    soil_dataset_id: str,
    weather_dataset_id: str,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    offset: int = 0,
    limit: int = 100,
) -> CombinedSoilWeatherResponse:
    soil_rows = _require_daily(soil_dataset_id)
    weather_id = _validate_id(weather_dataset_id)
    weather_path = Path(WEATHER_ROOT) / weather_id / "daily_weather.csv"
    weather_rows = read_daily_weather(weather_path) if weather_path.is_file() else []
    wetness_path = Path(WETNESS_ROOT) / weather_id / "wetness_indicators.csv"
    wetness_rows = read_daily_weather(wetness_path) if wetness_path.is_file() else []
    aligned = align_soil_weather_wetness(soil_rows, weather_rows, wetness_rows)
    filtered = [row for row in aligned if _in_range(row.get("date_utc"), start_date, end_date)]
    offset = max(offset, 0)
    limit = min(max(limit, 1), 2000)
    page = filtered[offset:offset + limit]
    processed = _processed_manifest(soil_dataset_id) or {}
    return CombinedSoilWeatherResponse(
        soil_dataset_id=soil_dataset_id,
        weather_dataset_id=weather_id,
        spatial=processed.get("spatial"),
        total=len(filtered),
        offset=offset,
        limit=limit,
        records=[CombinedSoilWeatherRow.model_validate(item) for item in page],
    )


def get_quality(dataset_id: str) -> SoilQualityResponse:
    payload = _quality_payload(dataset_id)
    if payload is None:
        raise MissingProcessedOutputError("Soil quality report is not available yet.")
    return SoilQualityResponse(
        dataset_id=dataset_id,
        status=payload.get("status"),
        observation_kind=payload.get("observation_kind"),
        is_ground_truth=False,
        is_measured_soil_moisture=False,
        suitable_for_modeling=False,
        source_integrity=payload.get("source_integrity"),
        observation_validity=payload.get("observation_validity"),
        period_completeness=payload.get("period_completeness"),
        modeled_soil_readiness=payload.get("modeled_soil_readiness"),
        modeled_soil_readiness_reason=payload.get("modeled_soil_readiness_reason"),
        daily=payload.get("daily") or {},
        hourly=payload.get("hourly") or {},
        spatial=payload.get("spatial"),
        grid_comparison=payload.get("grid_comparison"),
        coverage=payload.get("coverage"),
        issues=list(payload.get("issues") or []),
        quality_notes=list(payload.get("quality_notes") or []),
    )


def get_sources() -> SourceRegistryResponse:
    payload = load_source_registry()
    return SourceRegistryResponse(
        title=payload.get("title"),
        verified_at_utc=payload.get("verified_at_utc"),
        counts=payload.get("counts") or {},
        sources=list(payload.get("sources") or []),
    )


def get_wetness(
    weather_dataset_id: str,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    offset: int = 0,
    limit: int = 100,
) -> WetnessResponse:
    weather_dataset_id = _validate_id(weather_dataset_id)
    path = Path(WETNESS_ROOT) / weather_dataset_id / "wetness_indicators.csv"
    if not path.is_file():
        raise MissingProcessedOutputError("Wetness indicators are not available yet.")
    rows = read_daily_weather(path)
    filtered = [row for row in rows if _in_range(row.get("date_utc"), start_date, end_date)]
    offset = max(offset, 0)
    limit = min(max(limit, 1), 2000)
    page = filtered[offset:offset + limit]
    return WetnessResponse(
        weather_dataset_id=weather_dataset_id,
        total=len(filtered),
        offset=offset,
        limit=limit,
        observation_kinds=[
            "rainfall_history_indicator",
            "weather_derived_wetness_proxy",
        ],
        is_measured_soil_moisture=False,
        records=[WetnessRow.model_validate(item) for item in page],
    )


def _summary(dataset_id: str, raw_manifest: dict) -> SoilDatasetSummary:
    processed = _processed_manifest(dataset_id) or {}
    quality = _quality_payload(dataset_id)
    period = processed.get("period_processed") or raw_manifest.get("period") or {}
    paths = soil_paths(dataset_id, raw_root=Path(RAW_ROOT), processed_root=Path(PROCESSED_ROOT))
    return SoilDatasetSummary(
        dataset_id=dataset_id,
        period_start=(period or {}).get("start"),
        period_end=(period or {}).get("end"),
        day_count=int(processed.get("day_count") or 0),
        complete_days=int(processed.get("complete_days") or 0),
        has_daily=paths["daily_csv"].is_file(),
        quality_status=(None if quality is None else quality.get("status"))
        or processed.get("quality_status"),
        observation_kind=processed.get("observation_kind"),
        is_ground_truth=False,
    )


def _require_daily(dataset_id: str) -> list[dict]:
    dataset_id = _validate_id(dataset_id)
    _require_raw_manifest(dataset_id)
    path = Path(PROCESSED_ROOT) / dataset_id / "daily_soil.csv"
    if not path.is_file():
        raise MissingProcessedOutputError("Daily soil table is not available yet.")
    return read_daily_soil(path)


def _require_raw_manifest(dataset_id: str) -> dict:
    dataset_id = _validate_id(dataset_id)
    path = Path(RAW_ROOT) / dataset_id / "manifest.json"
    if not path.is_file():
        raise DatasetNotFoundError(f"Unknown soil dataset: {dataset_id}")
    return read_manifest(path)


def _processed_manifest(dataset_id: str) -> dict | None:
    path = Path(PROCESSED_ROOT) / dataset_id / "manifest.json"
    if not path.is_file():
        return None
    return read_manifest(path)


def _quality_payload(dataset_id: str) -> dict | None:
    path = Path(PROCESSED_ROOT) / dataset_id / "quality_report.json"
    if not path.is_file():
        return None
    return read_json(path)


def _validate_id(dataset_id: str) -> str:
    if not IMAGE_ID_PATTERN.fullmatch(dataset_id):
        raise InvalidImageIdError("dataset_id is invalid.")
    return validate_safe_id(dataset_id, "dataset_id")


def _in_range(value: str | None, start: str | None, end: str | None) -> bool:
    if not value:
        return False
    day = str(value)[:10]
    if start and day < start:
        return False
    if end and day > end:
        return False
    return True
