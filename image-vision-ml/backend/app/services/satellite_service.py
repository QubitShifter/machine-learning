"""Service layer for local satellite image analysis."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from backend.app.schemas.satellite import (
    DatasetDetailResponse,
    DatasetListResponse,
    DatasetProcessResponse,
    DatasetQualityResponse,
    DatasetSceneRecord,
    DatasetScenesResponse,
    DatasetSummary,
    DatasetTimeseriesResponse,
    ImageListResponse,
    ImageMetadataResponse,
    ImageSummary,
    MonthlyNdviResponse,
    MonthlyNdviRow,
    NdviComparisonResponse,
    NdviStatsResponse,
    NdviSummary,
    ProcessRequest,
    ProcessResponse,
    SceneQualityResponse,
    TimeseriesObservation,
    YearlyNdviResponse,
    YearlyNdviRow,
)
from ml.ingestion.config import load_dataset_config
from ml.ingestion.manifest import read_manifest, scene_records, validate_safe_id
from ml.ingestion.pipeline import (
    generate_dataset_timeseries,
    process_dataset,
)
from ml.preprocessing.errors import (
    DatasetNotFoundError,
    InvalidImageIdError,
    InvalidMetadataError,
    MissingProcessedOutputError,
)
from ml.preprocessing.features import VALID_SCL_CLASSES, calculate_ndvi_statistics
from ml.preprocessing.raster import (
    BAND_FILES,
    OUTPUT_METADATA,
    OUTPUT_NDVI_PNG,
    OUTPUT_NDVI_TIF,
    OUTPUT_RGB_PNG,
    default_processed_root,
    default_raw_root,
    list_available_bands,
    load_scene_metadata,
    process_local_dataset,
    read_json,
    read_raster_metadata,
)


logger = logging.getLogger(__name__)

IMAGE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")

RAW_ROOT = default_raw_root()
PROCESSED_ROOT = default_processed_root()
CONFIG_ROOT = default_raw_root().parents[3] / "configs"


def list_images() -> ImageListResponse:
    raw_root = _raw_root()
    images: list[ImageSummary] = []

    if not raw_root.is_dir():
        return ImageListResponse(images=[])

    for entry in sorted(raw_root.iterdir()):
        if not entry.is_dir():
            continue
        if not IMAGE_ID_PATTERN.fullmatch(entry.name):
            continue
        if not (entry / "metadata.json").is_file():
            continue
        images.append(_image_summary(entry.name))

    return ImageListResponse(images=images)


def get_metadata(image_id: str) -> ImageMetadataResponse:
    image_id = validate_image_id(image_id)
    raw_dir = _require_dataset(image_id)
    scene = load_scene_metadata(raw_dir)
    grid = _reference_grid(raw_dir)

    return ImageMetadataResponse(
        id=image_id,
        scene_id=scene.get("scene_id"),
        acquisition_date=_date_only(scene.get("acquisition_date")),
        cloud_cover=_as_float(scene.get("cloud_cover")),
        source=_source(scene),
        collection=scene.get("collection"),
        crs=None if grid is None else str(grid["crs"]),
        width=None if grid is None else int(grid["width"]),
        height=None if grid is None else int(grid["height"]),
        pixel_resolution=(
            None if grid is None else [float(value) for value in grid["resolution"]]
        ),
        bbox=(
            None if grid is None else [float(value) for value in grid["bounds"]]
        ),
        available_bands=list_available_bands(raw_dir),
        processed=_is_processed(image_id),
    )


def process_image(
    image_id: str,
    request: ProcessRequest | None = None,
) -> ProcessResponse:
    image_id = validate_image_id(image_id)
    raw_dir = _require_dataset(image_id)
    options = request or ProcessRequest()
    scl_classes = (
        tuple(options.valid_scl_classes)
        if options.apply_scl_mask
        else None
    )
    if options.apply_scl_mask and not scl_classes:
        scl_classes = VALID_SCL_CLASSES

    logger.info(
        "Processing satellite dataset %s with settings %s",
        image_id,
        options.model_dump(),
    )

    result = process_local_dataset(
        raw_dir,
        _processed_dir(image_id),
        generate_rgb=options.generate_rgb,
        generate_ndvi=options.generate_ndvi,
        apply_scl_mask=options.apply_scl_mask,
        valid_scl_classes=scl_classes,
    )

    ndvi = result.get("ndvi")
    return ProcessResponse(
        image_id=image_id,
        status=str(result.get("status", "processed")),
        outputs=list(result.get("output_filenames", [])),
        valid_pixels=result.get("valid_pixels"),
        total_pixels=result.get("total_pixels"),
        valid_percentage=result.get("valid_percentage"),
        ndvi=None if ndvi is None else NdviSummary.model_validate(ndvi),
    )


def get_ndvi_stats(image_id: str) -> NdviStatsResponse:
    image_id = validate_image_id(image_id)
    _require_dataset(image_id)
    processed_dir = _processed_dir(image_id)
    ndvi_path = processed_dir / OUTPUT_NDVI_TIF
    metadata_path = processed_dir / OUTPUT_METADATA

    if not ndvi_path.is_file():
        raise MissingProcessedOutputError(
            "NDVI statistics are not available because the dataset "
            "has not been processed yet."
        )

    from rasterio.errors import RasterioIOError
    import rasterio

    try:
        with rasterio.open(ndvi_path) as dataset:
            ndvi = dataset.read(1)
    except RasterioIOError as exc:
        raise InvalidMetadataError(
            "Processed NDVI raster could not be read."
        ) from exc

    statistics = calculate_ndvi_statistics(ndvi)

    if metadata_path.is_file():
        stored = read_json(metadata_path)
        if stored.get("total_pixels") is not None:
            statistics["total_pixels"] = int(stored["total_pixels"])
            statistics["valid_percentage"] = (
                round(
                    100.0 * statistics["valid_pixels"] / statistics["total_pixels"],
                    2,
                )
                if statistics["total_pixels"]
                else 0.0
            )

    return NdviStatsResponse(
        image_id=image_id,
        valid_pixels=statistics["valid_pixels"],
        total_pixels=statistics["total_pixels"],
        valid_percentage=statistics["valid_percentage"],
        ndvi=NdviSummary(
            minimum=statistics["minimum"],
            maximum=statistics["maximum"],
            mean=statistics["mean"],
            median=statistics["median"],
            standard_deviation=statistics["standard_deviation"],
        ),
    )


def get_rgb_preview_path(image_id: str) -> Path:
    return _require_output(image_id, OUTPUT_RGB_PNG, "RGB preview")


def get_ndvi_preview_path(image_id: str) -> Path:
    return _require_output(image_id, OUTPUT_NDVI_PNG, "NDVI preview")


def validate_image_id(image_id: str) -> str:
    if not IMAGE_ID_PATTERN.fullmatch(image_id or ""):
        raise InvalidImageIdError(
            "Image ID must be a local dataset name and cannot contain "
            "path separators."
        )
    return image_id


def _raw_root() -> Path:
    return Path(RAW_ROOT)


def _processed_root() -> Path:
    return Path(PROCESSED_ROOT)


def _raw_dir(image_id: str) -> Path:
    root = _raw_root().resolve()
    candidate = (root / image_id).resolve()
    if not candidate.is_relative_to(root):
        raise InvalidImageIdError(
            "Image ID must be a local dataset name and cannot contain "
            "path separators."
        )
    return candidate


def _processed_dir(image_id: str) -> Path:
    root = _processed_root().resolve()
    root.mkdir(parents=True, exist_ok=True)
    candidate = (root / image_id).resolve()
    if not candidate.is_relative_to(root):
        raise InvalidImageIdError(
            "Image ID must be a local dataset name and cannot contain "
            "path separators."
        )
    return candidate


def _require_dataset(image_id: str) -> Path:
    raw_dir = _raw_dir(image_id)
    if not raw_dir.is_dir() or not (raw_dir / "metadata.json").is_file():
        raise DatasetNotFoundError(
            f"Unknown satellite dataset: {image_id}"
        )
    return raw_dir


def _is_processed(image_id: str) -> bool:
    return (_processed_dir(image_id) / OUTPUT_METADATA).is_file()


def _image_summary(image_id: str) -> ImageSummary:
    raw_dir = _raw_dir(image_id)
    scene = load_scene_metadata(raw_dir)
    return ImageSummary(
        id=image_id,
        scene_id=scene.get("scene_id"),
        acquisition_date=_date_only(scene.get("acquisition_date")),
        available_bands=list_available_bands(raw_dir),
        processed=_is_processed(image_id),
    )


def _reference_grid(raw_dir: Path) -> dict | None:
    for band in ("B04", "B08", "B03", "B02", "SCL"):
        path = raw_dir / BAND_FILES[band]
        if path.is_file():
            return read_raster_metadata(path)
    return None


def _require_output(image_id: str, filename: str, label: str) -> Path:
    image_id = validate_image_id(image_id)
    _require_dataset(image_id)
    path = _processed_dir(image_id) / filename
    if not path.is_file():
        raise MissingProcessedOutputError(
            f"{label} is not available because the dataset "
            "has not been processed yet."
        )
    return path


def _date_only(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text[:10] if text else None


def _as_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _source(scene: dict) -> str | None:
    for key in ("source", "stac_url", "collection"):
        value = scene.get(key)
        if value:
            return str(value)
    return None


def list_datasets() -> DatasetListResponse:
    datasets = []
    raw_root = _raw_root()
    if not raw_root.is_dir():
        return DatasetListResponse(datasets=[])
    for entry in sorted(raw_root.iterdir()):
        manifest_path = entry / "manifest.json"
        if not entry.is_dir() or not manifest_path.is_file():
            continue
        try:
            validate_safe_id(entry.name, "dataset_id")
            manifest = read_manifest(manifest_path)
        except (ValueError, FileNotFoundError):
            continue
        datasets.append(_dataset_summary(entry.name, manifest))
    return DatasetListResponse(datasets=datasets)


def get_dataset(dataset_id: str) -> DatasetDetailResponse:
    manifest = _require_dataset_manifest(dataset_id)
    scenes = scene_records(manifest)
    statuses: dict[str, int] = {}
    for record in scenes:
        status = str(record.get("status") or "unknown")
        statuses[status] = statuses.get(status, 0) + 1
    processed_manifest = _processed_manifest(dataset_id)
    return DatasetDetailResponse(
        dataset_id=dataset_id,
        bbox=manifest.get("bbox"),
        period=manifest.get("period"),
        collection=(manifest.get("source") or {}).get("collection"),
        processing_version=(
            None if processed_manifest is None
            else processed_manifest.get("processing_version")
        ),
        target_grid=(
            None if processed_manifest is None
            else processed_manifest.get("target_grid")
        ),
        scene_count=len(scenes),
        processed_count=statuses.get("processed", 0),
        statuses=statuses,
    )


def list_dataset_scenes(dataset_id: str) -> DatasetScenesResponse:
    manifest = _require_dataset_manifest(dataset_id)
    processed = _processed_manifest(dataset_id) or {}
    processed_scenes = processed.get("scenes") or {}
    scenes = []
    for record in scene_records(manifest):
        extra = processed_scenes.get(record["scene_id"], {})
        scenes.append(DatasetSceneRecord(
            scene_id=record["scene_id"],
            acquisition_date=record.get("acquisition_date"),
            status=extra.get("status") or record.get("status"),
            cloud_cover=_as_float(record.get("cloud_cover")),
            aoi_coverage=_as_float(record.get("aoi_coverage")),
            valid_percentage=_as_float(extra.get("valid_percentage")),
        ))
    return DatasetScenesResponse(dataset_id=dataset_id, scenes=scenes)


def get_dataset_timeseries(dataset_id: str) -> DatasetTimeseriesResponse:
    dataset_id = validate_image_id(dataset_id)
    path = _processed_root() / dataset_id / "timeseries" / "ndvi_timeseries.json"
    if not path.is_file():
        raise MissingProcessedOutputError(
            "NDVI time series is not available because it has not "
            "been generated yet."
        )
    payload = read_json(path)
    observations = [
        TimeseriesObservation.model_validate({
            "scene_id": item.get("scene_id"),
            "date": item.get("date"),
            "mean": item.get("mean"),
            "median": item.get("median"),
            "valid_percentage": item.get("valid_percentage"),
        })
        for item in payload.get("observations", [])
    ]
    return DatasetTimeseriesResponse(
        dataset_id=dataset_id,
        metric=payload.get("metric", "ndvi"),
        observations=observations,
    )


def get_dataset_quality(dataset_id: str) -> DatasetQualityResponse:
    dataset_id = validate_image_id(dataset_id)
    _require_dataset_manifest(dataset_id)
    path = _processed_root() / dataset_id / "quality" / "dataset_quality.json"
    if not path.is_file():
        raise MissingProcessedOutputError(
            "Dataset quality report is not available yet."
        )
    payload = read_json(path)
    return DatasetQualityResponse(
        dataset_id=dataset_id,
        dataset=payload.get("dataset") or {},
        training_readiness=payload.get("training_readiness"),
        scene_count=len(payload.get("scenes") or []),
    )


def get_scene_quality(dataset_id: str, scene_id: str) -> SceneQualityResponse:
    dataset_id = validate_image_id(dataset_id)
    scene_id = validate_image_id(scene_id)
    _require_dataset_manifest(dataset_id)
    path = _processed_root() / dataset_id / "scenes" / scene_id / "quality_report.json"
    if not path.is_file():
        quality_path = _processed_root() / dataset_id / "quality" / "dataset_quality.json"
        if quality_path.is_file():
            payload = read_json(quality_path)
            for item in payload.get("scenes") or []:
                if item.get("scene_id") == scene_id:
                    return SceneQualityResponse.model_validate(item)
        raise MissingProcessedOutputError(
            "Scene quality report is not available yet."
        )
    return SceneQualityResponse.model_validate(read_json(path))


def get_dataset_monthly_ndvi(dataset_id: str) -> MonthlyNdviResponse:
    payload = _require_timeseries(dataset_id)
    monthly = [
        MonthlyNdviRow.model_validate(item)
        for item in payload.get("monthly") or []
    ]
    return MonthlyNdviResponse(
        dataset_id=dataset_id,
        metric=payload.get("metric", "ndvi"),
        monthly=monthly,
        missing_months=list(payload.get("missing_months") or []),
    )


def get_dataset_yearly_ndvi(dataset_id: str) -> YearlyNdviResponse:
    payload = _require_timeseries(dataset_id)
    yearly = [
        YearlyNdviRow.model_validate(item)
        for item in payload.get("yearly") or []
    ]
    return YearlyNdviResponse(
        dataset_id=dataset_id,
        metric=payload.get("metric", "ndvi"),
        yearly=yearly,
    )


def get_dataset_ndvi_comparison(dataset_id: str) -> NdviComparisonResponse:
    payload = _require_timeseries(dataset_id)
    comparison = payload.get("comparison")
    if not comparison:
        raise MissingProcessedOutputError(
            "Interannual NDVI comparison is not available yet."
        )
    return NdviComparisonResponse(
        dataset_id=dataset_id,
        metric=payload.get("metric", "ndvi"),
        comparison=comparison,
    )


def get_dataset_quality_report_path(dataset_id: str) -> Path:
    dataset_id = validate_image_id(dataset_id)
    path = _processed_root() / dataset_id / "quality" / "dataset_quality.json"
    if not path.is_file():
        raise MissingProcessedOutputError(
            "Dataset quality report is not available yet."
        )
    return path


def get_dataset_chart_path(dataset_id: str) -> Path:
    dataset_id = validate_image_id(dataset_id)
    path = _processed_root() / dataset_id / "timeseries" / "ndvi_timeseries.png"
    if not path.is_file():
        raise MissingProcessedOutputError(
            "NDVI time-series chart is not available yet."
        )
    return path


def process_registered_dataset(dataset_id: str) -> DatasetProcessResponse:
    dataset_id = validate_image_id(dataset_id)
    _require_dataset_manifest(dataset_id)
    config_path = _find_dataset_config(dataset_id)
    if config_path is None:
        raise InvalidMetadataError(
            "No local configuration file is registered for this dataset. "
            "Use the CLI to process it."
        )
    result = process_dataset(config_path)
    try:
        generate_dataset_timeseries(config_path)
        message = "Processed downloaded scenes and refreshed the NDVI time series."
    except Exception as exc:
        message = f"Processed scenes but time-series generation failed: {exc}"
    return DatasetProcessResponse(
        dataset_id=dataset_id,
        status="processed",
        processed=result.get("processed", 0),
        failed=result.get("failed", 0),
        message=message,
    )


def _require_dataset_manifest(dataset_id: str) -> dict:
    dataset_id = validate_image_id(dataset_id)
    path = _raw_root() / dataset_id / "manifest.json"
    if not path.is_file():
        raise DatasetNotFoundError(
            f"Unknown satellite dataset: {dataset_id}"
        )
    try:
        return read_manifest(path)
    except ValueError as exc:
        raise InvalidMetadataError("Dataset manifest is invalid.") from exc


def _processed_manifest(dataset_id: str) -> dict | None:
    path = _processed_root() / dataset_id / "manifest.json"
    if not path.is_file():
        return None
    try:
        return read_manifest(path)
    except ValueError:
        return None


def _dataset_summary(dataset_id: str, manifest: dict) -> DatasetSummary:
    scenes = scene_records(manifest)
    processed = _processed_manifest(dataset_id) or {}
    processed_count = sum(
        1 for item in scene_records(processed)
        if item.get("status") == "processed"
    )
    period = manifest.get("period") or {}
    chart = _processed_root() / dataset_id / "timeseries" / "ndvi_timeseries.json"
    return DatasetSummary(
        dataset_id=dataset_id,
        period_start=period.get("start"),
        period_end=period.get("end"),
        scene_count=len(scenes),
        processed_count=processed_count,
        has_timeseries=chart.is_file(),
    )


def _require_timeseries(dataset_id: str) -> dict:
    dataset_id = validate_image_id(dataset_id)
    path = _processed_root() / dataset_id / "timeseries" / "ndvi_timeseries.json"
    if not path.is_file():
        raise MissingProcessedOutputError(
            "NDVI time series is not available because it has not "
            "been generated yet."
        )
    return read_json(path)


def _find_dataset_config(dataset_id: str) -> Path | None:
    root = Path(CONFIG_ROOT)
    if not root.is_dir():
        return None
    for path in sorted(root.glob("*.y*ml")):
        try:
            payload = load_dataset_config(path)
        except Exception:
            continue
        if payload.get("dataset_id") == dataset_id:
            return path
    return None
