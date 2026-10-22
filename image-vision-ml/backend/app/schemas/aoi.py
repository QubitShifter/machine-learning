from pydantic import BaseModel, Field


class AoiDraftRequest(BaseModel):
    name: str | None = None
    geometry_type: str = "bbox"
    bbox: list[float] | None = None
    coordinates: list[list[float]] | None = None


class AoiGeometryResponse(BaseModel):
    model_config = {"extra": "allow"}
    type: str
    bbox: list[float]
    coordinates: list[list[float]]
    crs: str = "EPSG:4326"
    valid: bool = True
    area_km2: float | None = None


class AoiAreaResponse(BaseModel):
    model_config = {"extra": "allow"}
    aoi_id: str
    name: str
    status: str
    bbox: list[float]
    crs: str = "EPSG:4326"
    satellite_dataset_id: str | None = None
    weather_dataset_id: str | None = None
    soil_dataset_id: str | None = None
    mutable: bool = False
    downloads_allowed: bool = False
    geometry: dict | None = None
    notes: str | None = None


class AoiRegistryResponse(BaseModel):
    version: str | None = None
    operational_count: int = 0
    areas: list[AoiAreaResponse] = Field(default_factory=list)
    drafts: list[dict] = Field(default_factory=list)
    note: str | None = None


class AoiDraftResponse(BaseModel):
    model_config = {"extra": "allow"}
    draft_id: str
    name: str | None = None
    status: str = "draft"
    created_at: str
    geometry: dict
    downloads_started: bool = False
    operational: bool = False
    note: str | None = None
