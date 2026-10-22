"""Pydantic schemas for the satellite analysis API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ImageSummary(BaseModel):
    id: str
    scene_id: str | None = None
    acquisition_date: str | None = None
    available_bands: list[str]
    processed: bool


class ImageListResponse(BaseModel):
    images: list[ImageSummary]


class ImageMetadataResponse(BaseModel):
    id: str
    scene_id: str | None = None
    acquisition_date: str | None = None
    cloud_cover: float | None = None
    source: str | None = None
    collection: str | None = None
    crs: str | None = None
    width: int | None = None
    height: int | None = None
    pixel_resolution: list[float] | None = None
    bbox: list[float] | None = None
    available_bands: list[str]
    processed: bool


class ProcessRequest(BaseModel):
    generate_rgb: bool = True
    generate_ndvi: bool = True
    apply_scl_mask: bool = True
    valid_scl_classes: list[int] = Field(default_factory=lambda: [4, 5])


class NdviSummary(BaseModel):
    minimum: float | None = None
    maximum: float | None = None
    mean: float | None = None
    median: float | None = None
    standard_deviation: float | None = None


class ProcessResponse(BaseModel):
    image_id: str
    status: str
    outputs: list[str]
    valid_pixels: int | None = None
    total_pixels: int | None = None
    valid_percentage: float | None = None
    ndvi: NdviSummary | None = None


class NdviStatsResponse(BaseModel):
    image_id: str
    valid_pixels: int
    total_pixels: int
    valid_percentage: float
    ndvi: NdviSummary


class DatasetSummary(BaseModel):
    dataset_id: str
    period_start: str | None = None
    period_end: str | None = None
    scene_count: int = 0
    processed_count: int = 0
    has_timeseries: bool = False


class DatasetListResponse(BaseModel):
    datasets: list[DatasetSummary]


class DatasetDetailResponse(BaseModel):
    dataset_id: str
    bbox: list[float] | None = None
    period: dict | None = None
    collection: str | None = None
    processing_version: str | None = None
    target_grid: dict | None = None
    scene_count: int = 0
    processed_count: int = 0
    statuses: dict[str, int] = Field(default_factory=dict)


class DatasetSceneRecord(BaseModel):
    scene_id: str
    acquisition_date: str | None = None
    status: str | None = None
    platform: str | None = None
    cloud_cover: float | None = None
    aoi_coverage: float | None = None
    valid_percentage: float | None = None
    overlay_ready: bool = False


class DatasetScenesResponse(BaseModel):
    dataset_id: str
    scenes: list[DatasetSceneRecord]


class TimeseriesObservation(BaseModel):
    scene_id: str | None = None
    date: str | None = None
    mean: float | None = None
    median: float | None = None
    valid_percentage: float | None = None


class DatasetTimeseriesResponse(BaseModel):
    dataset_id: str
    metric: str = "ndvi"
    observations: list[TimeseriesObservation]


class DatasetProcessResponse(BaseModel):
    dataset_id: str
    status: str
    processed: int = 0
    failed: int = 0
    message: str | None = None


class SceneQualityResponse(BaseModel):
    scene_id: str | None = None
    acquisition_date: str | None = None
    satellite_platform: str | None = None
    quality_status: str | None = None
    scene_quality_status: str | None = None
    calibration_status: str | None = None
    scene_quality_reasons: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    exclusion_counts: dict | None = None
    geometric_footprint_overlap_pct: float | None = None
    actual_aoi_coverage_pct: float | None = None
    valid_ndvi_pct: float | None = None
    ndvi_minimum: float | None = None
    ndvi_mean: float | None = None
    ndvi_maximum: float | None = None
    ndvi_median: float | None = None
    cloud_shadow_fraction_pct: float | None = None
    valid_pixels: int | None = None
    total_aoi_pixels: int | None = None
    grid_aligned: bool | None = None
    calibration: dict | None = None
    missing_assets: list[str] = Field(default_factory=list)


class DatasetQualityResponse(BaseModel):
    dataset_id: str
    dataset: dict
    training_readiness: dict | None = None
    coverage: dict | None = None
    calibration_audit: dict | None = None
    task_readiness: dict | None = None
    scene_count: int = 0


class MonthlyNdviRow(BaseModel):
    month: str
    observation_count: int = 0
    mean: float | None = None
    median_of_medians: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    valid_pixel_percentage: float | None = None
    available_dates: list[str] = Field(default_factory=list)


class YearlyNdviRow(BaseModel):
    year: str
    observation_count: int = 0
    mean: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    growing_season_mean: float | None = None


class MonthlyNdviResponse(BaseModel):
    dataset_id: str
    metric: str = "ndvi"
    monthly: list[MonthlyNdviRow]
    missing_months: list[str] = Field(default_factory=list)


class YearlyNdviResponse(BaseModel):
    dataset_id: str
    metric: str = "ndvi"
    yearly: list[YearlyNdviRow]


class NdviComparisonResponse(BaseModel):
    dataset_id: str
    metric: str = "ndvi"
    comparison: dict


class MapOverlayMetadataResponse(BaseModel):
    scene_id: str
    overlay_available: bool
    supported_modes: list[str] = Field(default_factory=list)
    unavailable_reason: str | None = None
    native_crs: str | None = None
    native_width: int | None = None
    native_height: int | None = None
    native_pixel_size_m: list[float] | None = None
    native_bounds: dict | None = None
    rendered_crs: str | None = None
    rendered_width: int | None = None
    rendered_height: int | None = None
    rendered_resolution_m: list[float] | None = None
    rendered_downsampled: bool = False
    geographic_extent: dict | None = None
    maplibre_coordinates: list[list[float]] | None = None
    valid_mask_policy: str | None = None
    render_version: str | None = None
    cache_id: str | None = None
    ndvi_color_scale: list[dict] = Field(default_factory=list)
    scl_legend: list[dict] = Field(default_factory=list)
    scl_provenance: dict | None = None
    quality_limitations: list[str] = Field(default_factory=list)


class MapNdviSampleResponse(BaseModel):
    scene_id: str
    longitude: float
    latitude: float
    crs: str = "EPSG:4326"
    inside_raster: bool
    valid: bool
    ndvi: float | None = None
    sampling: str = "nearest"
    message: str | None = None


class MapPixelInspectResponse(BaseModel):
    scene_id: str
    acquisition_date: str | None = None
    longitude: float
    latitude: float
    crs: str = "EPSG:4326"
    coverage_state: str
    inside_raster: bool
    valid: bool
    row: int | None = None
    col: int | None = None
    sampling: str = "nearest_10m_target_grid"
    red_b04: float | None = None
    green_b03: float | None = None
    blue_b02: float | None = None
    nir_b08: float | None = None
    ndvi: float | None = None
    scl_class: int | None = None
    scl_class_name: str | None = None
    valid_mask: bool | None = None
    exclusion_reason: str | None = None
    calibration_status: str | None = None
    scene_quality_status: str | None = None
    missing_reasons: dict[str, str] = Field(default_factory=dict)
    message: str | None = None
    source: str = "processed_rasters"
    estimated_from_display_rgb: bool = False


class SceneHistogramResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    dataset_id: str | None = None
    scene_id: str | None = None
    histogram_version: str | None = None
    pixel_exclusion_version: str | None = None
    processing_version: str | None = None
    acquisition_date: str | None = None
    scene_quality_status: str | None = None
    calibration_status: str | None = None
    scientific_use: str | None = None
    warnings: list[str] = Field(default_factory=list)
    ndvi: dict = Field(default_factory=dict)
    reflectance: dict = Field(default_factory=dict)
    scl: dict | None = None
    source: dict | None = None
    cached: bool | None = None
