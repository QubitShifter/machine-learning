"""Versioned satellite image analysis endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from backend.app.schemas.satellite import (
    DatasetDetailResponse,
    DatasetListResponse,
    DatasetProcessResponse,
    DatasetQualityResponse,
    DatasetScenesResponse,
    DatasetTimeseriesResponse,
    ImageListResponse,
    ImageMetadataResponse,
    MapNdviSampleResponse,
    MapOverlayMetadataResponse,
    MapPixelInspectResponse,
    MonthlyNdviResponse,
    NdviComparisonResponse,
    NdviStatsResponse,
    ProcessRequest,
    ProcessResponse,
    SceneHistogramResponse,
    SceneQualityResponse,
    YearlyNdviResponse,
)
from backend.app.services import satellite_map, satellite_service
from ml.preprocessing.errors import (
    CatalogSearchError,
    CorruptedRasterError,
    DatasetConfigError,
    DatasetNotFoundError,
    DownloadError,
    InvalidImageIdError,
    InvalidMetadataError,
    MissingBandError,
    MissingProcessedOutputError,
    NoValidPixelsError,
    RasterAlignmentError,
    SatelliteProcessingError,
    UnsupportedCalibrationError,
)


logger = logging.getLogger(__name__)

router = APIRouter()

_STATUS_CODES = {
    InvalidImageIdError: 400,
    DatasetNotFoundError: 404,
    MissingProcessedOutputError: 404,
    MissingBandError: 422,
    CorruptedRasterError: 422,
    InvalidMetadataError: 422,
    UnsupportedCalibrationError: 422,
    RasterAlignmentError: 422,
    NoValidPixelsError: 422,
    DatasetConfigError: 422,
    CatalogSearchError: 502,
    DownloadError: 422,
    SatelliteProcessingError: 422,
}


@router.get("/images", response_model=ImageListResponse)
def list_images() -> ImageListResponse:
    return _call(satellite_service.list_images)


@router.get("/images/{image_id}/metadata", response_model=ImageMetadataResponse)
def get_metadata(image_id: str) -> ImageMetadataResponse:
    return _call(satellite_service.get_metadata, image_id)


@router.post("/images/{image_id}/process", response_model=ProcessResponse)
def process_image(
    image_id: str,
    request: ProcessRequest | None = None,
) -> ProcessResponse:
    return _call(satellite_service.process_image, image_id, request)


@router.get("/images/{image_id}/ndvi/stats", response_model=NdviStatsResponse)
def get_ndvi_stats(image_id: str) -> NdviStatsResponse:
    return _call(satellite_service.get_ndvi_stats, image_id)


@router.get("/images/{image_id}/rgb")
def get_rgb_preview(image_id: str) -> FileResponse:
    path = _call(satellite_service.get_rgb_preview_path, image_id)
    return FileResponse(
        path,
        media_type="image/png",
        filename="rgb_preview.png",
    )


@router.get("/images/{image_id}/ndvi/preview")
def get_ndvi_preview(image_id: str) -> FileResponse:
    path = _call(satellite_service.get_ndvi_preview_path, image_id)
    return FileResponse(
        path,
        media_type="image/png",
        filename="ndvi_corrected.png",
    )


@router.get("/datasets", response_model=DatasetListResponse)
def list_datasets() -> DatasetListResponse:
    return _call(satellite_service.list_datasets)


@router.get("/datasets/{dataset_id}", response_model=DatasetDetailResponse)
def get_dataset(dataset_id: str) -> DatasetDetailResponse:
    return _call(satellite_service.get_dataset, dataset_id)


@router.get(
    "/datasets/{dataset_id}/scenes",
    response_model=DatasetScenesResponse,
)
def list_dataset_scenes(dataset_id: str) -> DatasetScenesResponse:
    return _call(satellite_service.list_dataset_scenes, dataset_id)


@router.get(
    "/datasets/{dataset_id}/timeseries/ndvi",
    response_model=DatasetTimeseriesResponse,
)
def get_dataset_timeseries(dataset_id: str) -> DatasetTimeseriesResponse:
    return _call(satellite_service.get_dataset_timeseries, dataset_id)


@router.get(
    "/datasets/{dataset_id}/quality",
    response_model=DatasetQualityResponse,
)
def get_dataset_quality(dataset_id: str) -> DatasetQualityResponse:
    return _call(satellite_service.get_dataset_quality, dataset_id)


@router.get(
    "/datasets/{dataset_id}/scenes/{scene_id}/quality",
    response_model=SceneQualityResponse,
)
def get_scene_quality(dataset_id: str, scene_id: str) -> SceneQualityResponse:
    return _call(satellite_service.get_scene_quality, dataset_id, scene_id)


@router.get(
    "/datasets/{dataset_id}/scenes/{scene_id}/histograms",
    response_model=SceneHistogramResponse,
)
def get_scene_histograms(
    dataset_id: str,
    scene_id: str,
    bins: int = Query(default=45, ge=8, le=200),
) -> SceneHistogramResponse:
    return _call(
        satellite_service.get_scene_histograms,
        dataset_id,
        scene_id,
        bins=bins,
    )


@router.get("/datasets/{dataset_id}/scenes/{scene_id}/rgb")
def get_dataset_scene_rgb(dataset_id: str, scene_id: str) -> FileResponse:
    path = _call(
        satellite_service.get_dataset_scene_preview_path,
        dataset_id,
        scene_id,
        "rgb",
    )
    return FileResponse(path, media_type="image/png", filename="rgb_preview.png")


@router.get("/datasets/{dataset_id}/scenes/{scene_id}/ndvi/preview")
def get_dataset_scene_ndvi(dataset_id: str, scene_id: str) -> FileResponse:
    path = _call(
        satellite_service.get_dataset_scene_preview_path,
        dataset_id,
        scene_id,
        "ndvi",
    )
    return FileResponse(path, media_type="image/png", filename="ndvi_preview.png")


@router.get(
    "/datasets/{dataset_id}/scenes/{scene_id}/map/metadata",
    response_model=MapOverlayMetadataResponse,
)
def get_scene_map_metadata(dataset_id: str, scene_id: str) -> MapOverlayMetadataResponse:
    return _call(satellite_map.get_map_metadata, dataset_id, scene_id)


@router.get("/datasets/{dataset_id}/scenes/{scene_id}/map/rgb")
def get_scene_map_rgb(dataset_id: str, scene_id: str) -> FileResponse:
    path = _call(satellite_map.get_map_overlay_path, dataset_id, scene_id, "rgb")
    return FileResponse(path, media_type="image/png", filename="map_rgb.png")


@router.get("/datasets/{dataset_id}/scenes/{scene_id}/map/ndvi")
def get_scene_map_ndvi(dataset_id: str, scene_id: str) -> FileResponse:
    path = _call(satellite_map.get_map_overlay_path, dataset_id, scene_id, "ndvi")
    return FileResponse(path, media_type="image/png", filename="map_ndvi.png")


@router.get("/datasets/{dataset_id}/scenes/{scene_id}/map/scl")
def get_scene_map_scl(dataset_id: str, scene_id: str) -> FileResponse:
    path = _call(satellite_map.get_map_overlay_path, dataset_id, scene_id, "scl")
    return FileResponse(path, media_type="image/png", filename="map_scl.png")


@router.get(
    "/datasets/{dataset_id}/scenes/{scene_id}/map/ndvi/sample",
    response_model=MapNdviSampleResponse,
)
def get_scene_ndvi_sample(
    dataset_id: str,
    scene_id: str,
    longitude: float = Query(..., ge=-180, le=180),
    latitude: float = Query(..., ge=-90, le=90),
) -> MapNdviSampleResponse:
    return _call(
        satellite_map.get_ndvi_sample,
        dataset_id,
        scene_id,
        longitude,
        latitude,
    )


@router.get(
    "/datasets/{dataset_id}/scenes/{scene_id}/map/pixel",
    response_model=MapPixelInspectResponse,
)
def get_scene_pixel_sample(
    dataset_id: str,
    scene_id: str,
    longitude: float = Query(..., ge=-180, le=180),
    latitude: float = Query(..., ge=-90, le=90),
) -> MapPixelInspectResponse:
    return _call(
        satellite_map.get_pixel_sample,
        dataset_id,
        scene_id,
        longitude,
        latitude,
    )


@router.get(
    "/datasets/{dataset_id}/timeseries/ndvi/monthly",
    response_model=MonthlyNdviResponse,
)
def get_dataset_monthly_ndvi(dataset_id: str) -> MonthlyNdviResponse:
    return _call(satellite_service.get_dataset_monthly_ndvi, dataset_id)


@router.get(
    "/datasets/{dataset_id}/timeseries/ndvi/yearly",
    response_model=YearlyNdviResponse,
)
def get_dataset_yearly_ndvi(dataset_id: str) -> YearlyNdviResponse:
    return _call(satellite_service.get_dataset_yearly_ndvi, dataset_id)


@router.get(
    "/datasets/{dataset_id}/timeseries/ndvi/comparison",
    response_model=NdviComparisonResponse,
)
def get_dataset_ndvi_comparison(dataset_id: str) -> NdviComparisonResponse:
    return _call(satellite_service.get_dataset_ndvi_comparison, dataset_id)


@router.get("/datasets/{dataset_id}/quality/report")
def get_dataset_quality_report(dataset_id: str) -> FileResponse:
    path = _call(satellite_service.get_dataset_quality_report_path, dataset_id)
    return FileResponse(
        path,
        media_type="application/json",
        filename="dataset_quality.json",
    )


@router.get("/datasets/{dataset_id}/timeseries/ndvi/chart")
def get_dataset_chart(dataset_id: str) -> FileResponse:
    path = _call(satellite_service.get_dataset_chart_path, dataset_id)
    return FileResponse(
        path,
        media_type="image/png",
        filename="ndvi_timeseries.png",
    )


@router.post(
    "/datasets/{dataset_id}/process",
    response_model=DatasetProcessResponse,
)
def process_dataset(dataset_id: str) -> DatasetProcessResponse:
    return _call(satellite_service.process_registered_dataset, dataset_id)


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
        logger.warning("Satellite API error: %s", exc)
        raise HTTPException(status_code=status, detail=str(exc)) from exc
