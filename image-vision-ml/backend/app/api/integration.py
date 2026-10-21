"""Versioned satellite–weather integration endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from backend.app.schemas.integration import (
    IntegrationDatasetDetailResponse,
    IntegrationDatasetListResponse,
    IntegrationFeatureCatalogResponse,
    IntegrationObservationListResponse,
    IntegrationQualityResponse,
)
from backend.app.services import integration_service
from ml.preprocessing.errors import (
    DatasetNotFoundError,
    InvalidImageIdError,
    InvalidMetadataError,
    MissingProcessedOutputError,
)


logger = logging.getLogger(__name__)

router = APIRouter()

_STATUS_CODES = {
    InvalidImageIdError: 400,
    DatasetNotFoundError: 404,
    MissingProcessedOutputError: 404,
    InvalidMetadataError: 422,
}


@router.get("/datasets", response_model=IntegrationDatasetListResponse)
def list_datasets() -> IntegrationDatasetListResponse:
    return _call(integration_service.list_datasets)


@router.get("/datasets/{dataset_id}", response_model=IntegrationDatasetDetailResponse)
def get_dataset(dataset_id: str) -> IntegrationDatasetDetailResponse:
    return _call(integration_service.get_dataset, dataset_id)


@router.get(
    "/datasets/{dataset_id}/observations",
    response_model=IntegrationObservationListResponse,
)
def get_observations(
    dataset_id: str,
    scene_id: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    window_complete: bool | None = Query(default=None),
    availability: str | None = Query(
        default=None,
        description="complete, incomplete, or missing weather-feature coverage",
    ),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=2000),
) -> IntegrationObservationListResponse:
    return _call(
        integration_service.get_observations,
        dataset_id,
        scene_id=scene_id,
        start_date=start_date,
        end_date=end_date,
        window_complete=window_complete,
        availability=availability,
        offset=offset,
        limit=limit,
    )


@router.get("/datasets/{dataset_id}/quality", response_model=IntegrationQualityResponse)
def get_quality(dataset_id: str) -> IntegrationQualityResponse:
    return _call(integration_service.get_quality, dataset_id)


@router.get(
    "/datasets/{dataset_id}/features",
    response_model=IntegrationFeatureCatalogResponse,
)
def get_features(dataset_id: str) -> IntegrationFeatureCatalogResponse:
    return _call(integration_service.get_features, dataset_id)


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
        logger.warning("Integration API error: %s", exc)
        raise HTTPException(status_code=status, detail=str(exc)) from exc
