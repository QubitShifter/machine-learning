"""Georeferenced RGB/NDVI overlay rendering for MapLibre.

This module creates display-only RGBA PNGs. It does not modify scientific
source rasters or recalculate NDVI. RGB uses the same reflectance stretch
documented in ``ml.preprocessing.features.create_rgb``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.transform import array_bounds
from rasterio.warp import (
    calculate_default_transform,
    reproject,
    transform as warp_xy,
    transform_bounds,
)

from ml.preprocessing.errors import (
    MissingProcessedOutputError,
    RasterAlignmentError,
)
from ml.preprocessing.features import (
    RGB_DISPLAY_GAMMA,
    RGB_STRETCH_SATURATION,
    create_rgb,
    to_reflectance,
)
from ml.preprocessing.raster import (
    BAND_FILES,
    OUTPUT_METADATA,
    OUTPUT_NDVI_TIF,
    OUTPUT_VALID_MASK,
    read_json,
    read_raster_metadata,
    reproject_continuous,
)


RENDER_VERSION = "map-overlay-v1"
RENDERED_CRS = "EPSG:3857"
GEOGRAPHIC_CRS = "EPSG:4326"
MAX_RENDER_PIXELS = 4_000_000
NDVI_SOURCE_CANDIDATES = ("ndvi.tif", OUTPUT_NDVI_TIF)
MASK_SOURCE_CANDIDATES = (OUTPUT_VALID_MASK,)

# Fixed NDVI display scale. Values are not normalized per scene.
NDVI_COLOR_STOPS: tuple[tuple[float, tuple[int, int, int]], ...] = (
    (-1.0, (139, 0, 0)),
    (-0.2, (186, 110, 49)),
    (0.0, (245, 245, 245)),
    (0.2, (186, 228, 179)),
    (0.5, (116, 196, 118)),
    (0.8, (35, 139, 69)),
    (1.0, (0, 68, 27)),
)

VALID_MASK_POLICY = (
    "alpha=0 where processed valid_mask is 0 or NDVI is non-finite. "
    "The valid mask is SCL classes 4 and 5 plus finite reflectance "
    "(vegetation and bare soil). Cloud, shadow, water, cirrus, nodata, "
    "and other SCL classes are transparent. Valid dark land pixels stay opaque."
)


@dataclass(frozen=True)
class DestinationGrid:
    crs: CRS
    transform: Any
    width: int
    height: int
    resolution_m: tuple[float, float]
    downsampled: bool


def ndvi_color_scale_definition() -> list[dict[str, Any]]:
    return [
        {"value": value, "color_rgb": list(color)}
        for value, color in NDVI_COLOR_STOPS
    ]


def colorize_ndvi(values: np.ndarray) -> np.ndarray:
    """Map NDVI in [-1, 1] to uint8 RGB using the fixed display scale."""
    stops_x = np.array([item[0] for item in NDVI_COLOR_STOPS], dtype=np.float32)
    stops_c = np.array([item[1] for item in NDVI_COLOR_STOPS], dtype=np.float32)
    clipped = np.clip(np.asarray(values, dtype=np.float32), -1.0, 1.0)
    rgb = np.empty(clipped.shape + (3,), dtype=np.uint8)
    for channel in range(3):
        rgb[..., channel] = np.interp(clipped, stops_x, stops_c[:, channel])
    return rgb


def find_source_raster(directory: Path, candidates: tuple[str, ...]) -> Path | None:
    for name in candidates:
        path = directory / name
        if path.is_file():
            return path
    return None


def inspect_overlay_sources(
    processed_dir: Path,
    raw_dir: Path | None = None,
) -> dict[str, Any]:
    """Describe whether a processed scene can produce map overlays."""
    ndvi_path = find_source_raster(processed_dir, NDVI_SOURCE_CANDIDATES)
    mask_path = find_source_raster(processed_dir, MASK_SOURCE_CANDIDATES)
    rgb_bands = _rgb_band_paths(raw_dir) if raw_dir is not None else {}
    modes: list[str] = []
    if ndvi_path is not None and mask_path is not None:
        modes.append("ndvi")
        if len(rgb_bands) == 3:
            modes.append("rgb")
    reason = None
    if not modes:
        if ndvi_path is None or mask_path is None:
            reason = "Processed NDVI raster or valid mask is missing."
        else:
            reason = "RGB source reflectance bands are missing."
    return {
        "overlay_available": bool(modes),
        "supported_modes": modes,
        "unavailable_reason": reason,
        "ndvi_path": ndvi_path,
        "mask_path": mask_path,
        "rgb_bands": rgb_bands,
    }


def plan_destination_grid(source_grid: dict[str, Any]) -> DestinationGrid:
    """Build a north-up EPSG:3857 grid from the source raster geometry."""
    src_crs = CRS.from_user_input(source_grid["crs"])
    dst_crs = CRS.from_epsg(3857)
    west, south, east, north = _source_bounds(source_grid)
    transform, width, height = calculate_default_transform(
        src_crs,
        dst_crs,
        int(source_grid["width"]),
        int(source_grid["height"]),
        west,
        south,
        east,
        north,
    )
    downsampled = False
    pixels = int(width) * int(height)
    if pixels > MAX_RENDER_PIXELS:
        scale = (MAX_RENDER_PIXELS / pixels) ** 0.5
        width = max(1, int(width * scale))
        height = max(1, int(height * scale))
        transform, width, height = calculate_default_transform(
            src_crs,
            dst_crs,
            int(source_grid["width"]),
            int(source_grid["height"]),
            west,
            south,
            east,
            north,
            dst_width=width,
            dst_height=height,
        )
        downsampled = True
    return DestinationGrid(
        crs=dst_crs,
        transform=transform,
        width=int(width),
        height=int(height),
        resolution_m=(abs(transform.a), abs(transform.e)),
        downsampled=downsampled,
    )


def geographic_extent(grid: DestinationGrid) -> dict[str, Any]:
    """WGS84 envelope of the rendered north-up Mercator raster."""
    west, south, east, north = transform_bounds(
        grid.crs,
        GEOGRAPHIC_CRS,
        *array_bounds(grid.height, grid.width, grid.transform),
        densify_pts=21,
    )
    return {
        "crs": GEOGRAPHIC_CRS,
        "west": float(west),
        "south": float(south),
        "east": float(east),
        "north": float(north),
        "coordinate_order": "west,south,east,north",
    }


def maplibre_coordinates(extent: dict[str, Any]) -> list[list[float]]:
    """MapLibre image-source corners: TL, TR, BR, BL in lon/lat."""
    west = extent["west"]
    south = extent["south"]
    east = extent["east"]
    north = extent["north"]
    return [
        [west, north],
        [east, north],
        [east, south],
        [west, south],
    ]


def native_bounds_payload(source_grid: dict[str, Any]) -> dict[str, Any]:
    west, south, east, north = _source_bounds(source_grid)
    return {
        "crs": str(CRS.from_user_input(source_grid["crs"])),
        "west": float(west),
        "south": float(south),
        "east": float(east),
        "north": float(north),
        "coordinate_order": "west,south,east,north",
    }


def render_overlay_png(
    processed_dir: Path,
    mode: str,
    destination: DestinationGrid,
    raw_dir: Path | None = None,
) -> bytes:
    """Render a clean RGBA PNG with no titles, axes, or legends."""
    arrays = _source_display_arrays(processed_dir, mode, raw_dir)
    rgb, alpha = _reproject_display_arrays(arrays, destination)
    rgba = np.dstack([rgb, alpha])
    image = Image.fromarray(rgba, mode="RGBA")
    buffer = _png_bytes(image)
    return buffer


def sample_ndvi(
    processed_dir: Path,
    longitude: float,
    latitude: float,
) -> dict[str, Any]:
    """Nearest-neighbor sample of the processed NDVI raster."""
    import rasterio

    sources = inspect_overlay_sources(processed_dir)
    ndvi_path = sources["ndvi_path"]
    mask_path = sources["mask_path"]
    if ndvi_path is None or mask_path is None:
        raise MissingProcessedOutputError(
            "Processed NDVI raster is not available for sampling."
        )
    with rasterio.open(ndvi_path) as dataset:
        xs, ys = warp_xy(
            GEOGRAPHIC_CRS,
            dataset.crs,
            [float(longitude)],
            [float(latitude)],
        )
        row, col = dataset.index(xs[0], ys[0])
        inside = 0 <= row < dataset.height and 0 <= col < dataset.width
        if not inside:
            return {
                "inside_raster": False,
                "valid": False,
                "ndvi": None,
                "sampling": "nearest",
                "message": "Clicked location is outside the processed raster grid.",
            }
        value = float(dataset.read(1)[row, col])
    with rasterio.open(mask_path) as mask_ds:
        valid = bool(mask_ds.read(1)[row, col])
    if not valid or not np.isfinite(value):
        return {
            "inside_raster": True,
            "valid": False,
            "ndvi": None,
            "sampling": "nearest",
            "message": "Pixel is nodata or excluded by the valid-land mask.",
        }
    return {
        "inside_raster": True,
        "valid": True,
        "ndvi": value,
        "sampling": "nearest",
        "message": None,
    }


def _source_display_arrays(
    processed_dir: Path,
    mode: str,
    raw_dir: Path | None,
) -> dict[str, Any]:
    sources = inspect_overlay_sources(processed_dir, raw_dir)
    if mode not in sources["supported_modes"]:
        raise MissingProcessedOutputError(
            sources["unavailable_reason"]
            or f"{mode.upper()} overlay is not available for this scene."
        )
    ndvi_path: Path = sources["ndvi_path"]
    mask_path: Path = sources["mask_path"]
    source_grid = read_raster_metadata(ndvi_path)
    mask_grid = read_raster_metadata(mask_path)
    if (
        str(source_grid["crs"]) != str(mask_grid["crs"])
        or source_grid["width"] != mask_grid["width"]
        or source_grid["height"] != mask_grid["height"]
        or not source_grid["transform"].almost_equals(mask_grid["transform"])
    ):
        raise RasterAlignmentError(
            "NDVI and valid_mask rasters do not share the same grid."
        )

    import rasterio

    with rasterio.open(mask_path) as dataset:
        mask = dataset.read(1) != 0
    if mode == "ndvi":
        with rasterio.open(ndvi_path) as dataset:
            ndvi = dataset.read(1).astype(np.float32)
        rgb = colorize_ndvi(np.nan_to_num(ndvi, nan=0.0))
        alpha = (mask & np.isfinite(ndvi)).astype(np.uint8) * 255
    elif mode == "rgb":
        rgb_float = _aligned_display_rgb(sources["rgb_bands"], source_grid, processed_dir)
        rgb = np.clip(np.round(rgb_float * 255.0), 0, 255).astype(np.uint8)
        rgb[~mask] = 0
        alpha = mask.astype(np.uint8) * 255
    else:
        raise MissingProcessedOutputError(
            f"Unsupported overlay mode: {mode}"
        )
    return {
        "source_grid": source_grid,
        "rgb": rgb,
        "alpha": alpha,
    }


def _aligned_display_rgb(
    band_paths: dict[str, Path],
    reference: dict[str, Any],
    processed_dir: Path,
) -> np.ndarray:
    calibration_doc = _calibration_document(processed_dir, band_paths)
    reflectance: dict[str, np.ndarray] = {}
    for band in ("B04", "B03", "B02"):
        path = band_paths[band]
        array, _ = reproject_continuous(path, reference, Resampling.bilinear)
        import rasterio

        with rasterio.open(path) as dataset:
            nodata = dataset.nodata
        documented = (calibration_doc.get(band) or {})
        scale = float(documented.get("scale", 0.0001))
        offset = float(documented.get("offset", 0.0))
        if documented.get("nodata") is not None:
            nodata = documented.get("nodata")
        reflectance[band] = to_reflectance(array, scale, offset, nodata)
    return create_rgb(
        reflectance["B04"],
        reflectance["B03"],
        reflectance["B02"],
        np.isfinite(reflectance["B04"])
        & np.isfinite(reflectance["B03"])
        & np.isfinite(reflectance["B02"]),
    )


def _reproject_display_arrays(
    arrays: dict[str, Any],
    destination: DestinationGrid,
) -> tuple[np.ndarray, np.ndarray]:
    source_grid = arrays["source_grid"]
    src_crs = CRS.from_user_input(source_grid["crs"])
    rgb = np.asarray(arrays["rgb"])
    alpha = np.asarray(arrays["alpha"])
    dest_rgb = np.zeros((destination.height, destination.width, 3), dtype=np.uint8)
    dest_alpha = np.zeros((destination.height, destination.width), dtype=np.uint8)
    for channel in range(3):
        reproject(
            source=rgb[..., channel],
            destination=dest_rgb[..., channel],
            src_transform=source_grid["transform"],
            src_crs=src_crs,
            dst_transform=destination.transform,
            dst_crs=destination.crs,
            resampling=Resampling.bilinear,
        )
    reproject(
        source=alpha,
        destination=dest_alpha,
        src_transform=source_grid["transform"],
        src_crs=src_crs,
        dst_transform=destination.transform,
        dst_crs=destination.crs,
        resampling=Resampling.nearest,
    )
    dest_rgb[dest_alpha == 0] = 0
    return dest_rgb, dest_alpha


def _rgb_band_paths(raw_dir: Path | None) -> dict[str, Path]:
    if raw_dir is None or not raw_dir.is_dir():
        return {}
    paths = {}
    for band in ("B02", "B03", "B04"):
        path = raw_dir / BAND_FILES[band]
        if path.is_file():
            paths[band] = path
    return paths


def _calibration_document(
    processed_dir: Path,
    band_paths: dict[str, Path],
) -> dict[str, Any]:
    metadata_path = processed_dir / OUTPUT_METADATA
    if metadata_path.is_file():
        payload = read_json(metadata_path)
        calibration = payload.get("calibration")
        if isinstance(calibration, dict):
            return calibration
    raw_dir = next(iter(band_paths.values())).parent
    calibration_path = raw_dir / "calibration.json"
    if calibration_path.is_file():
        payload = read_json(calibration_path)
        if isinstance(payload, dict):
            return payload.get("calibration") or payload
    return {}


def _source_bounds(source_grid: dict[str, Any]) -> tuple[float, float, float, float]:
    bounds = source_grid.get("bounds")
    if bounds is not None and len(bounds) == 4:
        west, south, east, north = [float(value) for value in bounds]
        return west, south, east, north
    return array_bounds(
        int(source_grid["height"]),
        int(source_grid["width"]),
        source_grid["transform"],
    )


def _png_bytes(image: Image.Image) -> bytes:
    from io import BytesIO

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
