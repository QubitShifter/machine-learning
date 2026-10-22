"""Read-only service for prepared satellite–weather integration outputs."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from backend.app.schemas.integration import (
    IntegrationDatasetDetailResponse,
    IntegrationDatasetListResponse,
    IntegrationDatasetSummary,
    IntegrationFeatureCatalogResponse,
    IntegrationObservation,
    IntegrationObservationListResponse,
    IntegrationQualityResponse,
)
from ml.analysis.weather_timeseries import read_daily_weather
from ml.ingestion.manifest import validate_safe_id
from ml.integration.features import feature_metadata
from ml.integration.satellite_weather import default_integration_root
from ml.preprocessing.errors import (
    DatasetNotFoundError,
    InvalidImageIdError,
    MissingProcessedOutputError,
)
from ml.preprocessing.raster import read_json


IMAGE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
INTEGRATION_ROOT = default_integration_root()


def list_datasets() -> IntegrationDatasetListResponse:
    root = Path(INTEGRATION_ROOT)
    if not root.is_dir():
        return IntegrationDatasetListResponse(datasets=[])
    datasets = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        try:
            validate_safe_id(entry.name, "dataset_id")
        except ValueError:
            continue
        meta_path = entry / "integration_metadata.json"
        csv_path = entry / "satellite_weather.csv"
        if not meta_path.is_file() or not csv_path.is_file():
            continue
        try:
            metadata = read_json(meta_path)
        except Exception:
            continue
        datasets.append(_summary(entry.name, metadata))
    return IntegrationDatasetListResponse(datasets=datasets)


def get_dataset(dataset_id: str) -> IntegrationDatasetDetailResponse:
    metadata = _require_metadata(dataset_id)
    return IntegrationDatasetDetailResponse(
        dataset_id=dataset_id,
        satellite_dataset_id=metadata.get("satellite_dataset_id") or dataset_id,
        weather_dataset_id=metadata.get("weather_dataset_id"),
        aoi_id=metadata.get("aoi_id"),
        timezone="UTC",
        integration_version=metadata.get("integration_version"),
        leakage_policy=metadata.get("leakage_policy"),
        same_day_weather=metadata.get("same_day_weather"),
        window_rule=metadata.get("window_rule"),
        observation_count=int(metadata.get("observation_count") or 0),
        satellite_observation_valid_count=metadata.get("satellite_observation_valid_count"),
        weather_feature_window_complete_count=metadata.get(
            "weather_feature_window_complete_count"
        ),
        integrated_observation_complete_count=metadata.get(
            "integrated_observation_complete_count"
        ),
        suitable_for_modeling_count=metadata.get("suitable_for_modeling_count"),
        weather_integration_readiness=metadata.get("weather_integration_readiness"),
        satellite_supervised_soil_forecasting=metadata.get(
            "satellite_supervised_soil_forecasting"
        ),
        dry_day_precipitation_mm=metadata.get("dry_day_precipitation_mm"),
        windows_days=list(metadata.get("windows_days") or []),
        created_at=metadata.get("created_at"),
        updated_at=metadata.get("updated_at"),
        sources_changed=metadata.get("sources_changed"),
    )


def get_observations(
    dataset_id: str,
    *,
    scene_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    window_complete: bool | None = None,
    availability: str | None = None,
    offset: int = 0,
    limit: int = 100,
) -> IntegrationObservationListResponse:
    rows = _require_rows(dataset_id)
    filtered = [
        row
        for row in rows
        if _matches(row, scene_id, start_date, end_date, window_complete, availability)
    ]
    offset = max(offset, 0)
    limit = min(max(limit, 1), 2000)
    page = filtered[offset:offset + limit]
    return IntegrationObservationListResponse(
        dataset_id=dataset_id,
        total=len(filtered),
        offset=offset,
        limit=limit,
        records=[_observation(item) for item in page],
    )


def get_quality(dataset_id: str) -> IntegrationQualityResponse:
    dataset_id = _validate_id(dataset_id)
    _require_metadata(dataset_id)
    path = Path(INTEGRATION_ROOT) / dataset_id / "integration_quality.json"
    if not path.is_file():
        raise MissingProcessedOutputError(
            "Integration quality report is not available yet."
        )
    payload = read_json(path)
    return IntegrationQualityResponse(
        dataset_id=dataset_id,
        satellite_dataset_id=payload.get("satellite_dataset_id") or dataset_id,
        weather_dataset_id=payload.get("weather_dataset_id"),
        integration_version=payload.get("integration_version"),
        leakage_policy=payload.get("leakage_policy"),
        same_day_weather=payload.get("same_day_weather"),
        window_rule=payload.get("window_rule"),
        observation_count=int(payload.get("observation_count") or 0),
        satellite_observation_valid_count=int(
            payload.get("satellite_observation_valid_count") or 0
        ),
        weather_observation_valid_count=int(
            payload.get("weather_observation_valid_count") or 0
        ),
        weather_feature_window_complete_count=int(
            payload.get("weather_feature_window_complete_count") or 0
        ),
        integrated_observation_complete_count=int(
            payload.get("integrated_observation_complete_count") or 0
        ),
        suitable_for_modeling_count=int(payload.get("suitable_for_modeling_count") or 0),
        window_7d_complete_count=payload.get("window_7d_complete_count"),
        window_14d_complete_count=payload.get("window_14d_complete_count"),
        window_30d_complete_count=payload.get("window_30d_complete_count"),
        weather_integration_readiness=payload.get("weather_integration_readiness"),
        satellite_training_readiness=payload.get("satellite_training_readiness"),
        task_readiness=payload.get("task_readiness"),
        suitable_for_modeling_meaning=payload.get("suitable_for_modeling_meaning"),
        weather_spatial=payload.get("weather_spatial"),
        issues=list(payload.get("issues") or []),
        sources_changed=payload.get("sources_changed"),
        created_at=payload.get("created_at"),
        updated_at=payload.get("updated_at"),
    )


def get_features(dataset_id: str) -> IntegrationFeatureCatalogResponse:
    dataset_id = _validate_id(dataset_id)
    metadata = _require_metadata(dataset_id)
    path = Path(INTEGRATION_ROOT) / dataset_id / "feature_catalog.json"
    if path.is_file():
        payload = read_json(path)
    else:
        payload = feature_metadata(
            dry_day_mm=float(metadata.get("dry_day_precipitation_mm") or 1.0),
            windows=tuple(metadata.get("windows_days") or (7, 14, 30)),
        )
    return IntegrationFeatureCatalogResponse(
        dataset_id=dataset_id,
        integration_version=payload.get("integration_version"),
        leakage_policy=payload.get("leakage_policy"),
        same_day_weather=payload.get("same_day_weather"),
        window_rule=payload.get("window_rule"),
        timezone=payload.get("timezone") or "UTC",
        dry_day_precipitation_mm=payload.get("dry_day_precipitation_mm"),
        windows_days=list(payload.get("windows_days") or []),
        quality_dimensions=list(payload.get("quality_dimensions") or []),
        modeling_note=payload.get("modeling_note"),
        features=list(payload.get("features") or []),
    )


def _summary(dataset_id: str, metadata: dict[str, Any]) -> IntegrationDatasetSummary:
    return IntegrationDatasetSummary(
        dataset_id=dataset_id,
        satellite_dataset_id=metadata.get("satellite_dataset_id") or dataset_id,
        weather_dataset_id=metadata.get("weather_dataset_id"),
        observation_count=int(metadata.get("observation_count") or 0),
        integrated_observation_complete_count=int(
            metadata.get("integrated_observation_complete_count") or 0
        ),
        weather_feature_window_complete_count=int(
            metadata.get("weather_feature_window_complete_count") or 0
        ),
        suitable_for_modeling_count=int(metadata.get("suitable_for_modeling_count") or 0),
        integration_version=metadata.get("integration_version"),
        updated_at=metadata.get("updated_at"),
    )


def _observation(row: dict[str, Any]) -> IntegrationObservation:
    payload = dict(row)
    warnings = payload.get("quality_warnings")
    if isinstance(warnings, str):
        payload["quality_warnings"] = [part for part in warnings.split(";") if part]
    elif warnings is None:
        payload["quality_warnings"] = []
    return IntegrationObservation.model_validate(payload)


def _matches(
    row: dict[str, Any],
    scene_id: str | None,
    start_date: str | None,
    end_date: str | None,
    window_complete: bool | None,
    availability: str | None,
) -> bool:
    if scene_id and row.get("scene_id") != scene_id:
        return False
    day = str(row.get("observation_date_utc") or "")[:10]
    if start_date and (not day or day < start_date[:10]):
        return False
    if end_date and (not day or day > end_date[:10]):
        return False
    if window_complete is not None and bool(row.get("weather_feature_window_complete")) != window_complete:
        return False
    if availability:
        observed = sum(
            int(row.get(field) or 0)
            for field in (
                "window_7d_observed_days",
                "window_14d_observed_days",
                "window_30d_observed_days",
            )
        )
        complete = bool(row.get("weather_feature_window_complete"))
        if availability == "complete" and not complete:
            return False
        if availability == "incomplete" and (complete or observed == 0):
            return False
        if availability == "missing" and observed != 0:
            return False
    return True


def _require_metadata(dataset_id: str) -> dict[str, Any]:
    dataset_id = _validate_id(dataset_id)
    path = Path(INTEGRATION_ROOT) / dataset_id / "integration_metadata.json"
    if not path.is_file():
        raise DatasetNotFoundError(f"Unknown integration dataset: {dataset_id}")
    return read_json(path)


def _require_rows(dataset_id: str) -> list[dict[str, Any]]:
    dataset_id = _validate_id(dataset_id)
    _require_metadata(dataset_id)
    path = Path(INTEGRATION_ROOT) / dataset_id / "satellite_weather.csv"
    if not path.is_file():
        raise MissingProcessedOutputError(
            "Integrated observation table is not available yet."
        )
    return read_daily_weather(path)


def _validate_id(dataset_id: str) -> str:
    if not IMAGE_ID_PATTERN.fullmatch(dataset_id or ""):
        raise InvalidImageIdError(
            "Dataset ID must be a local name and cannot contain path separators."
        )
    return dataset_id
