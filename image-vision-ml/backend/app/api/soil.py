"""Versioned soil-moisture and agricultural source endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from backend.app.schemas.soil import (
    CombinedSoilWeatherResponse,
    DailySoilResponse,
    MonthlySoilResponse,
    SoilDatasetDetailResponse,
    SoilDatasetListResponse,
    SoilQualityResponse,
    SourceRegistryResponse,
    WetnessResponse,
)
from backend.app.services import soil_service
from ml.preprocessing.errors import (
    DatasetConfigError,
    DatasetNotFoundError,
    InvalidImageIdError,
    InvalidMetadataError,
    MissingProcessedOutputError,
    SoilConfigError,
)


logger = logging.getLogger(__name__)

router = APIRouter()

_STATUS_CODES = {
    InvalidImageIdError: 400,
    DatasetNotFoundError: 404,
    MissingProcessedOutputError: 404,
    InvalidMetadataError: 422,
    DatasetConfigError: 422,
    SoilConfigError: 422,
}


@router.get("/datasets", response_model=SoilDatasetListResponse)
def list_datasets() -> SoilDatasetListResponse:
    return soil_service.list_datasets()


@router.get("/datasets/{dataset_id}", response_model=SoilDatasetDetailResponse)
def get_dataset(dataset_id: str) -> SoilDatasetDetailResponse:
    return _call(soil_service.get_dataset, dataset_id)


@router.get("/datasets/{dataset_id}/daily", response_model=DailySoilResponse)
def get_daily(
    dataset_id: str,
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=2000),
) -> DailySoilResponse:
    return _call(
        soil_service.get_daily,
        dataset_id,
        start_date=start_date,
        end_date=end_date,
        offset=offset,
        limit=limit,
    )


@router.get("/datasets/{dataset_id}/monthly", response_model=MonthlySoilResponse)
def get_monthly(dataset_id: str) -> MonthlySoilResponse:
    return _call(soil_service.get_monthly, dataset_id)


@router.get("/datasets/{dataset_id}/quality", response_model=SoilQualityResponse)
def get_quality(dataset_id: str) -> SoilQualityResponse:
    return _call(soil_service.get_quality, dataset_id)


@router.get(
    "/combined/{soil_dataset_id}/{weather_dataset_id}",
    response_model=CombinedSoilWeatherResponse,
)
def get_combined(
    soil_dataset_id: str,
    weather_dataset_id: str,
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=2000),
) -> CombinedSoilWeatherResponse:
    return _call(
        soil_service.get_combined,
        soil_dataset_id,
        weather_dataset_id,
        start_date=start_date,
        end_date=end_date,
        offset=offset,
        limit=limit,
    )


@router.get("/sources", response_model=SourceRegistryResponse)
def get_sources() -> SourceRegistryResponse:
    return soil_service.get_sources()


@router.get("/wetness/{weather_dataset_id}", response_model=WetnessResponse)
def get_wetness(
    weather_dataset_id: str,
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=2000),
) -> WetnessResponse:
    return _call(
        soil_service.get_wetness,
        weather_dataset_id,
        start_date=start_date,
        end_date=end_date,
        offset=offset,
        limit=limit,
    )


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
        logger.warning("Soil API error: %s", exc)
        raise HTTPException(status_code=status, detail=str(exc)) from exc
