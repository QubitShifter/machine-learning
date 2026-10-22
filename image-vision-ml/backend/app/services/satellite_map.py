"""Read-only georeferenced overlay service for Satellite Explorer."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from pathlib import Path
from typing import Any

from backend.app.schemas.satellite import (
    MapNdviSampleResponse,
    MapOverlayMetadataResponse,
    MapPixelInspectResponse,
)
from backend.app.services import satellite_service
from ml.preprocessing.errors import (
    InvalidImageIdError,
    MissingProcessedOutputError,
)
from ml.preprocessing.raster import (
    project_root,
    read_raster_metadata,
)
from ml.visualization.map_overlay import (
    GEOGRAPHIC_CRS,
    RENDER_VERSION,
    RENDERED_CRS,
    VALID_MASK_POLICY,
    geographic_extent,
    inspect_overlay_sources,
    maplibre_coordinates,
    native_bounds_payload,
    ndvi_color_scale_definition,
    plan_destination_grid,
    render_overlay_png,
    sample_ndvi,
    sample_pixel,
    scl_legend_definition,
    scl_provenance_payload,
)


CACHE_ROOT = project_root() / "data" / "cache" / "satellite_map"
_LOCKS: dict[str, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()


def default_cache_root() -> Path:
    return Path(CACHE_ROOT)


def get_map_metadata(dataset_id: str, scene_id: str) -> MapOverlayMetadataResponse:
    dataset_id, scene_id, processed_dir, raw_dir = _resolve_scene(dataset_id, scene_id)
    sources = inspect_overlay_sources(processed_dir, raw_dir)
    if not sources["overlay_available"]:
        return MapOverlayMetadataResponse(
            scene_id=scene_id,
            overlay_available=False,
            supported_modes=[],
            unavailable_reason=sources["unavailable_reason"],
            render_version=RENDER_VERSION,
            valid_mask_policy=VALID_MASK_POLICY,
            ndvi_color_scale=ndvi_color_scale_definition(),
            scl_legend=scl_legend_definition(),
            scl_provenance=scl_provenance_payload(),
            quality_limitations=_quality_limitations(sources),
        )

    artifact = _ensure_metadata_artifact(dataset_id, scene_id, processed_dir, raw_dir, sources)
    return MapOverlayMetadataResponse.model_validate(artifact)


def get_map_overlay_path(dataset_id: str, scene_id: str, mode: str) -> Path:
    if mode not in {"rgb", "ndvi", "scl"}:
        raise MissingProcessedOutputError("Overlay mode must be rgb, ndvi, or scl.")
    dataset_id, scene_id, processed_dir, raw_dir = _resolve_scene(dataset_id, scene_id)
    sources = inspect_overlay_sources(processed_dir, raw_dir)
    if mode not in sources["supported_modes"]:
        raise MissingProcessedOutputError(
            sources["unavailable_reason"]
            or f"{mode.upper()} overlay is not available for this scene."
        )
    cache_dir = _cache_dir(dataset_id, scene_id, _fingerprint(processed_dir, raw_dir, sources))
    image_path = cache_dir / f"{mode}.png"
    with _lock(str(cache_dir)):
        _ensure_metadata_artifact(dataset_id, scene_id, processed_dir, raw_dir, sources)
        if _usable_png(image_path):
            return image_path
        source_grid = read_raster_metadata(sources["ndvi_path"])
        destination = plan_destination_grid(source_grid)
        payload = render_overlay_png(processed_dir, mode, destination, raw_dir)
        _atomic_write_bytes(image_path, payload)
    if not _usable_png(image_path):
        raise MissingProcessedOutputError(
            "Overlay rendering produced an unreadable image."
        )
    return image_path


def get_ndvi_sample(
    dataset_id: str,
    scene_id: str,
    longitude: float,
    latitude: float,
) -> MapNdviSampleResponse:
    dataset_id, scene_id, processed_dir, raw_dir = _resolve_scene(dataset_id, scene_id)
    sources = inspect_overlay_sources(processed_dir, raw_dir)
    if "ndvi" not in sources["supported_modes"]:
        raise MissingProcessedOutputError(
            "Processed NDVI raster is not available for sampling."
        )
    result = sample_ndvi(processed_dir, longitude, latitude, raw_dir)
    return MapNdviSampleResponse(
        scene_id=scene_id,
        longitude=float(longitude),
        latitude=float(latitude),
        crs=GEOGRAPHIC_CRS,
        **result,
    )


def get_pixel_sample(
    dataset_id: str,
    scene_id: str,
    longitude: float,
    latitude: float,
) -> MapPixelInspectResponse:
    dataset_id, scene_id, processed_dir, raw_dir = _resolve_scene(dataset_id, scene_id)
    sources = inspect_overlay_sources(processed_dir, raw_dir)
    if "ndvi" not in sources["supported_modes"]:
        raise MissingProcessedOutputError(
            "Processed NDVI raster is not available for sampling."
        )
    result = sample_pixel(processed_dir, longitude, latitude, raw_dir)
    return MapPixelInspectResponse(scene_id=scene_id, **result)


def overlay_ready(dataset_id: str, scene_id: str) -> bool:
    try:
        processed_dir = _scene_processed_dir(dataset_id, scene_id)
        raw_dir = _scene_raw_dir(dataset_id, scene_id)
    except (InvalidImageIdError, MissingProcessedOutputError):
        return False
    sources = inspect_overlay_sources(processed_dir, raw_dir)
    return bool(sources["supported_modes"])


def _resolve_scene(
    dataset_id: str,
    scene_id: str,
) -> tuple[str, str, Path, Path]:
    dataset_id = satellite_service.validate_image_id(dataset_id)
    scene_id = satellite_service.validate_image_id(scene_id)
    satellite_service._require_dataset_manifest(dataset_id)
    processed_dir = _scene_processed_dir(dataset_id, scene_id)
    raw_dir = _scene_raw_dir(dataset_id, scene_id)
    return dataset_id, scene_id, processed_dir, raw_dir


def _scene_processed_dir(dataset_id: str, scene_id: str) -> Path:
    root = (Path(satellite_service.PROCESSED_ROOT) / dataset_id / "scenes").resolve()
    directory = (root / scene_id).resolve()
    if not directory.is_relative_to(root):
        raise InvalidImageIdError(
            "Scene ID must be a local name and cannot contain path separators."
        )
    return directory


def _scene_raw_dir(dataset_id: str, scene_id: str) -> Path:
    root = (Path(satellite_service.RAW_ROOT) / dataset_id / "scenes").resolve()
    directory = (root / scene_id).resolve()
    if not directory.is_relative_to(root):
        raise InvalidImageIdError(
            "Scene ID must be a local name and cannot contain path separators."
        )
    return directory


def _ensure_metadata_artifact(
    dataset_id: str,
    scene_id: str,
    processed_dir: Path,
    raw_dir: Path,
    sources: dict[str, Any],
) -> dict[str, Any]:
    cache_id = _fingerprint(processed_dir, raw_dir, sources)
    cache_dir = _cache_dir(dataset_id, scene_id, cache_id)
    metadata_path = cache_dir / "metadata.json"
    with _lock(str(cache_dir)):
        if metadata_path.is_file():
            try:
                payload = json.loads(metadata_path.read_text(encoding="utf-8"))
                if payload.get("cache_id") == cache_id:
                    return payload
            except json.JSONDecodeError:
                pass
        source_grid = read_raster_metadata(sources["ndvi_path"])
        destination = plan_destination_grid(source_grid)
        extent = geographic_extent(destination)
        payload = {
            "scene_id": scene_id,
            "overlay_available": True,
            "supported_modes": list(sources["supported_modes"]),
            "unavailable_reason": None,
            "native_crs": str(source_grid["crs"]),
            "native_width": int(source_grid["width"]),
            "native_height": int(source_grid["height"]),
            "native_pixel_size_m": [float(value) for value in source_grid["resolution"]],
            "native_bounds": native_bounds_payload(source_grid),
            "rendered_crs": RENDERED_CRS,
            "rendered_width": destination.width,
            "rendered_height": destination.height,
            "rendered_resolution_m": [
                float(destination.resolution_m[0]),
                float(destination.resolution_m[1]),
            ],
            "rendered_downsampled": destination.downsampled,
            "geographic_extent": extent,
            "maplibre_coordinates": maplibre_coordinates(extent),
            "valid_mask_policy": VALID_MASK_POLICY,
            "render_version": RENDER_VERSION,
            "cache_id": cache_id,
            "ndvi_color_scale": ndvi_color_scale_definition(),
            "scl_legend": scl_legend_definition(),
            "scl_provenance": scl_provenance_payload(),
            "quality_limitations": _quality_limitations(sources),
        }
        _atomic_write_text(metadata_path, json.dumps(payload, indent=2))
        return payload


def _fingerprint(
    processed_dir: Path,
    raw_dir: Path,
    sources: dict[str, Any],
) -> str:
    parts = [RENDER_VERSION, VALID_MASK_POLICY]
    for path in (
        sources.get("ndvi_path"),
        sources.get("mask_path"),
        sources.get("scl_path"),
        *list((sources.get("rgb_bands") or {}).values()),
        processed_dir / "processing_metadata.json",
    ):
        if path is None:
            continue
        candidate = Path(path)
        if candidate.is_file():
            stat = candidate.stat()
            parts.append(f"{candidate.name}:{stat.st_size}:{stat.st_mtime_ns}")
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:16]


def _cache_dir(dataset_id: str, scene_id: str, cache_id: str) -> Path:
    root = default_cache_root().resolve()
    directory = (root / dataset_id / scene_id / RENDER_VERSION / cache_id).resolve()
    if not directory.is_relative_to(root):
        raise InvalidImageIdError(
            "Cache path escaped the configured overlay cache directory."
        )
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _quality_limitations(sources: dict[str, Any]) -> list[str]:
    notes = [
        "Overlay imagery is a display product resampled for MapLibre.",
        "It does not replace the processed scientific GeoTIFF.",
        "Inspection PNGs with titles or color bars are not used as overlays.",
    ]
    if "rgb" not in sources["supported_modes"]:
        notes.append("RGB overlay requires processed mask plus raw B02/B03/B04 rasters.")
    if "ndvi" not in sources["supported_modes"]:
        notes.append("NDVI overlay requires processed ndvi.tif and valid_mask.tif.")
    if "scl" not in sources["supported_modes"]:
        notes.append("SCL overlay requires processed NDVI/mask plus the native SCL raster.")
    return notes


def _usable_png(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 32:
        return False
    return path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_bytes(payload)
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _atomic_write_text(path: Path, payload: str) -> None:
    _atomic_write_bytes(path, payload.encode("utf-8"))


def _lock(key: str) -> threading.RLock:
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(key, threading.RLock())
