"""Study-area registry and draft-geometry endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.schemas.aoi import (
    AoiDraftRequest,
    AoiDraftResponse,
    AoiRegistryResponse,
)
from backend.app.services import aoi_service
from ml.aoi.geometry import AoiGeometryError


router = APIRouter()


@router.get("/areas", response_model=AoiRegistryResponse)
def list_areas() -> AoiRegistryResponse:
    return AoiRegistryResponse.model_validate(aoi_service.list_areas())


@router.post("/drafts", response_model=AoiDraftResponse)
def create_draft(request: AoiDraftRequest) -> AoiDraftResponse:
    try:
        payload = aoi_service.create_draft(
            name=request.name,
            geometry_type=request.geometry_type,
            bbox=request.bbox,
            coordinates=request.coordinates,
        )
    except AoiGeometryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return AoiDraftResponse.model_validate(payload)


@router.delete("/drafts/{draft_id}")
def delete_draft(draft_id: str) -> dict:
    try:
        return aoi_service.delete_draft(draft_id)
    except AoiGeometryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
