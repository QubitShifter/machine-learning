"""Versioned weather dataset endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from backend.app.schemas.weather import (
    DailyWeatherResponse,
    MonthlyWeatherResponse,
    SatelliteWeatherResponse,
    WeatherDatasetDetailResponse,
    WeatherDatasetListResponse,
    WeatherQualityResponse,
    WeatherSummaryResponse,
)
from backend.app.services import weather_service
from ml.preprocessing.errors import (
    DatasetConfigError,
    DatasetNotFoundError,
    InvalidImageIdError,
    InvalidMetadataError,
    MissingProcessedOutputError,
    WeatherConfigError,
)


logger = logging.getLogger(__name__)

router = APIRouter()

_STATUS_CODES = {
    InvalidImageIdError: 400,
    DatasetNotFoundError: 404,
    MissingProcessedOutputError: 404,
    InvalidMetadataError: 422,
    DatasetConfigError: 422,
    WeatherConfigError: 422,
}


@router.get("/datasets", response_model=WeatherDatasetListResponse)
def list_datasets() -> WeatherDatasetListResponse:
    return _call(weather_service.list_datasets)


@router.get("/datasets/{dataset_id}", response_model=WeatherDatasetDetailResponse)
def get_dataset(dataset_id: str) -> WeatherDatasetDetailResponse:
    return _call(weather_service.get_dataset, dataset_id)


@router.get("/datasets/{dataset_id}/daily", response_model=DailyWeatherResponse)
def get_daily(
    dataset_id: str,
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=2000),
) -> DailyWeatherResponse:
    return _call(
        weather_service.get_daily,
        dataset_id,
        start_date=start_date,
        end_date=end_date,
        offset=offset,
        limit=limit,
    )


@router.get("/datasets/{dataset_id}/summary", response_model=WeatherSummaryResponse)
def get_summary(
    dataset_id: str,
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> WeatherSummaryResponse:
    return _call(
        weather_service.get_summary,
        dataset_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/datasets/{dataset_id}/monthly", response_model=MonthlyWeatherResponse)
def get_monthly(dataset_id: str) -> MonthlyWeatherResponse:
    return _call(weather_service.get_monthly, dataset_id)


@router.get("/datasets/{dataset_id}/quality", response_model=WeatherQualityResponse)
def get_quality(dataset_id: str) -> WeatherQualityResponse:
    return _call(weather_service.get_quality, dataset_id)


@router.get("/datasets/{dataset_id}/chart")
def get_chart(dataset_id: str) -> FileResponse:
    path = _call(weather_service.get_chart_path, dataset_id)
    return FileResponse(
        path,
        media_type="image/png",
        filename="weather_timeseries.png",
    )


@router.get(
    "/datasets/{dataset_id}/satellite-integration",
    response_model=SatelliteWeatherResponse,
)
def get_satellite_integration(dataset_id: str) -> SatelliteWeatherResponse:
    return _call(weather_service.get_satellite_integration, dataset_id)


def _call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception as exc:
        status = _STATUS_CODES.get(type(exc))
        if status is None:
            for error_type, code in _STATUS_CODES.items():
                if isinstance(exc, error_type):
                    status = code
                    break
        if status is None:
            raise
        logger.warning("Weather API error: %s", exc)
        raise HTTPException(status_code=status, detail=str(exc)) from exc
