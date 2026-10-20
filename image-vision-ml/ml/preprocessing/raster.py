"""Local GeoTIFF helpers for Sentinel-2 preprocessing.

This module reads existing files only. Importing it does not
search STAC catalogs or download imagery.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.errors import RasterioIOError
from rasterio.transform import Affine
from rasterio.vrt import WarpedVRT

from ml.preprocessing.errors import (
    CorruptedRasterError,
    InvalidMetadataError,
    MissingBandError,
    NoValidPixelsError,
    RasterAlignmentError,
    UnsupportedCalibrationError,
)
from ml.preprocessing.calibration import refine_calibration_with_sample
from ml.preprocessing.features import (
    VALID_SCL_CLASSES,
    calculate_ndvi,
    calculate_ndvi_statistics,
    create_rgb,
    make_valid_mask,
    to_reflectance,
)


logger = logging.getLogger(__name__)

PROCESSING_VERSION = "1.1.0"

BAND_FILES = {
    "B02": "blue_B02.tif",
    "B03": "green_B03.tif",
    "B04": "red_B04.tif",
    "B08": "nir_B08.tif",
    "SCL": "scl.tif",
}

BAND_ALIASES = {
    "blue": "B02",
    "green": "B03",
    "red": "B04",
    "nir": "B08",
    "scl": "SCL",
}

OUTPUT_NDVI_TIF = "ndvi_corrected.tif"
OUTPUT_NDVI_PNG = "ndvi_corrected.png"
OUTPUT_RGB_PNG = "rgb_preview.png"
OUTPUT_VALID_MASK = "valid_mask.tif"
OUTPUT_METADATA = "processing_metadata.json"

_CALIBRATION_KEYS = {
    "B02": ("B02", "blue", "blue_B02"),
    "B03": ("B03", "green", "green_B03"),
    "B04": ("B04", "red", "red_B04"),
    "B08": ("B08", "nir", "nir_B08"),
}


def project_root() -> Path:
    """Return the repository root that contains ``data/``."""
    return Path(__file__).resolve().parents[2]


def default_raw_root() -> Path:
    return project_root() / "data" / "raw" / "satellite"


def default_processed_root() -> Path:
    return project_root() / "data" / "processed" / "satellite"


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InvalidMetadataError(
            f"Metadata file {path.name} is not valid JSON."
        ) from exc


def list_available_bands(raw_dir: Path) -> list[str]:
    return [
        band
        for band, filename in BAND_FILES.items()
        if (raw_dir / filename).is_file()
    ]


def read_raster_metadata(path: Path) -> dict[str, Any]:
    """Read geospatial metadata without assuming a scientific scale."""
    dataset = _open_raster(path)
    try:
        return _grid_from_dataset(dataset, path.name)
    finally:
        dataset.close()


def check_alignment(
    reference: dict[str, Any],
    candidate: dict[str, Any],
    *,
    name: str,
) -> None:
    """Raise if two rasters do not share CRS, transform, and shape."""
    reasons: list[str] = []

    if reference["crs"] != candidate["crs"]:
        reasons.append("CRS")
    if reference["width"] != candidate["width"] or reference[
        "height"
    ] != candidate["height"]:
        reasons.append("dimensions")
    if not reference["transform"].almost_equals(candidate["transform"]):
        reasons.append("affine transform")

    if reasons:
        raise RasterAlignmentError(
            f"Raster {name} is not aligned with the reference grid "
            f"({', '.join(reasons)} differ)."
        )


def reproject_continuous(
    path: Path,
    reference: dict[str, Any],
    resampling: Resampling = Resampling.bilinear,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Align a continuous raster onto the reference grid."""
    dataset = _open_raster(path)
    try:
        source_grid = _grid_from_dataset(dataset, path.name)
        if _grids_match(source_grid, reference):
            return dataset.read(1), source_grid
        if resampling not in {Resampling.nearest, Resampling.bilinear, Resampling.cubic}:
            raise RasterAlignmentError(
                f"Unsupported continuous resampling: {resampling}"
            )
        logger.info(
            "Resampling continuous raster %s onto the reference grid "
            "with %s interpolation.",
            path.name,
            resampling.name,
        )
        with WarpedVRT(
            dataset,
            crs=reference["crs"],
            transform=reference["transform"],
            width=reference["width"],
            height=reference["height"],
            resampling=resampling,
            nodata=dataset.nodata,
        ) as vrt:
            return vrt.read(1), _grid_from_dataset(vrt, path.name)
    finally:
        dataset.close()


def reproject_categorical(
    path: Path,
    reference: dict[str, Any],
) -> tuple[np.ndarray, dict[str, Any]]:
    """Align a classification raster using nearest-neighbor resampling."""
    dataset = _open_raster(path)
    try:
        source_grid = _grid_from_dataset(dataset, path.name)
        if _grids_match(source_grid, reference):
            return dataset.read(1), source_grid

        logger.info(
            "Resampling categorical raster %s onto the reference grid "
            "with nearest-neighbor interpolation.",
            path.name,
        )
        with WarpedVRT(
            dataset,
            crs=reference["crs"],
            transform=reference["transform"],
            width=reference["width"],
            height=reference["height"],
            resampling=Resampling.nearest,
            nodata=dataset.nodata,
        ) as vrt:
            return vrt.read(1), _grid_from_dataset(vrt, path.name)
    finally:
        dataset.close()


def write_geotiff(
    path: Path,
    array: np.ndarray,
    grid: dict[str, Any],
    nodata: float | None,
) -> None:
    """Write a single-band GeoTIFF, preserving the reference grid."""
    path.parent.mkdir(parents=True, exist_ok=True)
    profile = {
        "driver": "GTiff",
        "height": int(grid["height"]),
        "width": int(grid["width"]),
        "count": 1,
        "crs": grid["crs"],
        "transform": grid["transform"],
        "dtype": str(array.dtype),
        "nodata": nodata,
        "compress": "deflate",
    }
    temporary = path.with_name(f".{path.stem}.tmp{path.suffix}")
    try:
        with rasterio.open(temporary, "w", **profile) as destination:
            destination.write(array, 1)
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def save_preview(
    path: Path,
    image: np.ndarray,
    title: str,
    *,
    ndvi: bool = False,
) -> None:
    """Save an inspection PNG. Visualization stretch is not scientific."""
    path.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(10, 8))

    if ndvi:
        plot = axis.imshow(
            image,
            cmap="RdYlGn",
            vmin=-1,
            vmax=1,
            interpolation="nearest",
        )
        figure.colorbar(plot, ax=axis, label="NDVI", shrink=0.8)
    else:
        axis.imshow(image, interpolation="nearest")

    axis.set_title(title)
    axis.axis("off")
    temporary = path.with_name(f".{path.stem}.tmp{path.suffix}")
    try:
        figure.savefig(temporary, dpi=150, bbox_inches="tight")
        temporary.replace(path)
    finally:
        plt.close(figure)
        if temporary.exists():
            temporary.unlink()


def load_scene_metadata(raw_dir: Path) -> dict[str, Any]:
    metadata_path = raw_dir / "metadata.json"
    if not metadata_path.is_file():
        raise InvalidMetadataError(
            "Dataset metadata.json is missing."
        )
    metadata = read_json(metadata_path)
    if not isinstance(metadata, dict):
        raise InvalidMetadataError(
            "Dataset metadata.json must contain a JSON object."
        )
    return metadata


def load_calibration_document(
    raw_dir: Path,
    processed_dir: Path | None = None,
) -> dict[str, Any]:
    merged: dict[str, Any] = {}

    for filename in ("calibration.json", "metadata.json"):
        path = raw_dir / filename
        if path.is_file():
            document = read_json(path)
            if isinstance(document, dict):
                merged = _merge_calibration(merged, document)

    if processed_dir is not None:
        processed_metadata = processed_dir / OUTPUT_METADATA
        if processed_metadata.is_file():
            document = read_json(processed_metadata)
            if isinstance(document, dict):
                merged = _merge_calibration(merged, document)

    return merged


def resolve_calibration(
    dataset: rasterio.io.DatasetReader,
    band: str,
    calibration_doc: dict[str, Any],
) -> dict[str, Any]:
    """
    Resolve reflectance = DN * scale + offset from local metadata.

    Identity GeoTIFF scale/offset is treated as 'not stored' unless
    the array already looks like calibrated reflectance.
    """
    scale, offset, from_raster = _raster_scale_offset(dataset)
    if from_raster:
        return {
            "scale": scale,
            "offset": offset,
            "nodata": dataset.nodata,
            "source": "geotiff",
        }

    documented = _documented_scale_offset(band, calibration_doc)
    if documented is not None:
        doc_scale, doc_offset, source = documented
        return {
            "scale": doc_scale,
            "offset": doc_offset,
            "nodata": dataset.nodata,
            "source": source,
        }

    if _looks_like_reflectance(dataset):
        return {
            "scale": 1.0,
            "offset": 0.0,
            "nodata": dataset.nodata,
            "source": "already_calibrated",
        }

    raise UnsupportedCalibrationError(
        f"No reliable reflectance calibration for band {band}. "
        "Add per-band scale and offset to calibration.json or "
        "embed them in the GeoTIFF."
    )


def process_local_dataset(
    raw_dir: Path,
    output_dir: Path,
    *,
    generate_rgb: bool = True,
    generate_ndvi: bool = True,
    apply_scl_mask: bool = True,
    valid_scl_classes: tuple[int, ...] | None = VALID_SCL_CLASSES,
    force: bool = False,
    target_grid: dict[str, Any] | None = None,
    ndvi_filename: str = OUTPUT_NDVI_TIF,
    ndvi_preview_filename: str = OUTPUT_NDVI_PNG,
    statistics_filename: str | None = None,
) -> dict[str, Any]:
    """Process an existing local Sentinel-2 window.

    Raw input files are never overwritten.
    """
    raw_dir = Path(raw_dir)
    output_dir = Path(output_dir)
    settings = {
        "generate_rgb": bool(generate_rgb),
        "generate_ndvi": bool(generate_ndvi),
        "apply_scl_mask": bool(apply_scl_mask),
        "valid_scl_classes": (
            None if valid_scl_classes is None
            else [int(value) for value in valid_scl_classes]
        ),
    }
    if target_grid is not None:
        from ml.preprocessing.grid import serialize_grid

        settings["target_grid"] = serialize_grid(target_grid)

    scene_metadata = load_scene_metadata(raw_dir)
    required_bands = _required_bands(settings)
    for band in required_bands:
        _require_band(raw_dir, band)

    reference_path = raw_dir / BAND_FILES["B04"]
    if not reference_path.is_file():
        raise MissingBandError(
            "Required reference band B04 is missing."
        )

    if not force:
        cached = _reusable_result(raw_dir, output_dir, settings)
        if cached is not None:
            logger.info(
                "Reusing processed outputs for %s; settings and "
                "source files are unchanged.",
                raw_dir.name,
            )
            cached["status"] = "already_processed"
            return cached

    reference = (
        dict(target_grid)
        if target_grid is not None
        else read_raster_metadata(reference_path)
    )
    calibration_doc = load_calibration_document(raw_dir, output_dir)
    reflectance, calibrations, source_assets = _load_reflectance_bands(
        raw_dir,
        required_bands,
        reference,
        calibration_doc,
        align_to_reference=target_grid is not None,
    )

    valid = _build_valid_mask(
        raw_dir,
        reference,
        reflectance,
        settings,
    )

    if int(valid.sum()) == 0:
        raise NoValidPixelsError(
            "No valid pixels remain after quality masking."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_filenames = [OUTPUT_VALID_MASK, OUTPUT_METADATA]
    ndvi: np.ndarray | None = None
    statistics: dict[str, Any] | None = None

    write_geotiff(
        output_dir / OUTPUT_VALID_MASK,
        valid.astype(np.uint8),
        reference,
        0,
    )

    if settings["generate_ndvi"]:
        ndvi = calculate_ndvi(
            reflectance["B04"],
            reflectance["B08"],
            valid,
        )
        if not np.isfinite(ndvi).any():
            raise NoValidPixelsError(
                "NDVI produced no finite pixels after masking."
            )
        statistics = calculate_ndvi_statistics(ndvi)
        write_geotiff(
            output_dir / ndvi_filename,
            ndvi,
            reference,
            np.nan,
        )
        save_preview(
            output_dir / ndvi_preview_filename,
            ndvi,
            f"Sentinel-2 corrected NDVI - {raw_dir.name}",
            ndvi=True,
        )
        output_filenames.extend([ndvi_filename, ndvi_preview_filename])
        if statistics_filename:
            _write_json(output_dir / statistics_filename, statistics)
            output_filenames.append(statistics_filename)

    if settings["generate_rgb"]:
        rgb = create_rgb(
            reflectance["B04"],
            reflectance["B03"],
            reflectance["B02"],
            valid,
        )
        save_preview(
            output_dir / OUTPUT_RGB_PNG,
            rgb,
            f"Sentinel-2 RGB preview - {raw_dir.name}",
        )
        output_filenames.append(OUTPUT_RGB_PNG)

    if statistics is not None:
        valid_pixels = statistics["valid_pixels"]
        total_pixels = statistics["total_pixels"]
    else:
        valid_pixels = int(valid.sum())
        total_pixels = int(valid.size)

    result = _build_processing_metadata(
        raw_dir=raw_dir,
        scene_metadata=scene_metadata,
        source_assets=source_assets,
        calibrations=calibrations,
        settings=settings,
        statistics=statistics,
        reference=reference,
        output_filenames=sorted(set(output_filenames)),
        valid_pixels=valid_pixels,
        total_pixels=total_pixels,
    )
    _write_json(output_dir / OUTPUT_METADATA, result)

    logger.info(
        "Processed local satellite dataset %s (%s valid pixels).",
        raw_dir.name,
        result["valid_pixels"],
    )
    result["status"] = "processed"
    return result


def main() -> None:
    """Process the locally stored first_image dataset."""
    logging.basicConfig(level=logging.INFO)
    raw_dir = default_raw_root() / "first_image"
    output_dir = default_processed_root() / "first_image"
    result = process_local_dataset(raw_dir, output_dir, force=True)
    logger.info("Processing complete: %s", result["ndvi"])


def _open_raster(path: Path) -> rasterio.io.DatasetReader:
    if not path.is_file():
        raise MissingBandError(f"Raster file {path.name} is missing.")
    try:
        return rasterio.open(path)
    except RasterioIOError as exc:
        raise CorruptedRasterError(
            f"GeoTIFF {path.name} could not be opened."
        ) from exc


def _grid_from_dataset(
    dataset: rasterio.io.DatasetReader,
    name: str,
) -> dict[str, Any]:
    if dataset.crs is None:
        raise InvalidMetadataError(
            f"Raster {name} does not declare a CRS."
        )
    return {
        "crs": dataset.crs,
        "transform": dataset.transform,
        "width": dataset.width,
        "height": dataset.height,
        "nodata": dataset.nodata,
        "bounds": tuple(dataset.bounds),
        "resolution": tuple(dataset.res),
        "name": name,
    }


def _grids_match(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return (
        left["crs"] == right["crs"]
        and left["width"] == right["width"]
        and left["height"] == right["height"]
        and left["transform"].almost_equals(right["transform"])
    )


def _required_bands(settings: dict[str, Any]) -> list[str]:
    bands = ["B04"]
    if settings["generate_ndvi"]:
        bands.append("B08")
    if settings["generate_rgb"]:
        bands.extend(["B02", "B03"])
    if settings["apply_scl_mask"]:
        bands.append("SCL")
    # Preserve a stable unique order.
    seen: list[str] = []
    for band in bands:
        if band not in seen:
            seen.append(band)
    return seen


def _require_band(raw_dir: Path, band: str) -> Path:
    path = raw_dir / BAND_FILES[band]
    if not path.is_file():
        raise MissingBandError(
            f"Required band {band} is missing."
        )
    return path


def _load_reflectance_bands(
    raw_dir: Path,
    required_bands: list[str],
    reference: dict[str, Any],
    calibration_doc: dict[str, Any],
    align_to_reference: bool = False,
) -> tuple[dict[str, np.ndarray], dict[str, Any], dict[str, str]]:
    reflectance: dict[str, np.ndarray] = {}
    calibrations: dict[str, Any] = {}
    source_assets: dict[str, str] = {}

    for band in required_bands:
        if band == "SCL":
            continue
        path = _require_band(raw_dir, band)
        dataset = _open_raster(path)
        try:
            calibration = resolve_calibration(
                dataset, band, calibration_doc
            )
            calibration = refine_calibration_with_sample(
                dataset.read(1),
                calibration,
            )
            if calibration.get("requires_review"):
                logger.warning(
                    "Calibration for %s requires review (%s); "
                    "documented coefficients were not changed.",
                    band,
                    calibration.get("discrepancy") or calibration.get("validation_status"),
                )
            if align_to_reference:
                array, _grid = reproject_continuous(path, reference)
            else:
                grid = _grid_from_dataset(dataset, path.name)
                check_alignment(reference, grid, name=band)
                array = dataset.read(1)
        finally:
            dataset.close()

        reflectance[band] = to_reflectance(
            array,
            calibration["scale"],
            calibration["offset"],
            calibration["nodata"],
        )
        calibrations[band] = calibration
        source_assets[band] = path.name

    return reflectance, calibrations, source_assets


def _build_valid_mask(
    raw_dir: Path,
    reference: dict[str, Any],
    reflectance: dict[str, np.ndarray],
    settings: dict[str, Any],
) -> np.ndarray:
    bands = [reflectance[name] for name in ("B04", "B03", "B02", "B08") if name in reflectance]

    if not settings["apply_scl_mask"]:
        shape = next(iter(reflectance.values())).shape
        dummy = np.zeros(shape, dtype=np.uint8)
        return make_valid_mask(
            dummy,
            *bands,
            valid_scl_classes=None,
        )

    scl_path = _require_band(raw_dir, "SCL")
    scl, scl_grid = reproject_categorical(scl_path, reference)
    if not _grids_match(scl_grid, reference) and (
        scl.shape != (reference["height"], reference["width"])
    ):
        raise RasterAlignmentError(
            "SCL raster could not be aligned to the reference grid."
        )
    return make_valid_mask(
        scl,
        *bands,
        valid_scl_classes=settings["valid_scl_classes"],
    )


def _raster_scale_offset(
    dataset: rasterio.io.DatasetReader,
) -> tuple[float, float, bool]:
    scale = float(dataset.scales[0]) if dataset.scales else 1.0
    offset = float(dataset.offsets[0]) if dataset.offsets else 0.0
    tags = dataset.tags(1)
    if "scale" in tags:
        scale = float(tags["scale"])
    if "offset" in tags:
        offset = float(tags["offset"])

    identity = scale == 1.0 and offset == 0.0
    return scale, offset, not identity


def _documented_scale_offset(
    band: str,
    calibration_doc: dict[str, Any],
) -> tuple[float, float, str] | None:
    bands = calibration_doc.get("bands", {})
    if not isinstance(bands, dict):
        return None

    for key in _CALIBRATION_KEYS.get(band, (band,)):
        entry = bands.get(key)
        if isinstance(entry, dict) and "scale" in entry:
            return (
                float(entry["scale"]),
                float(entry.get("offset", 0.0)),
                str(entry.get("source") or calibration_doc.get("source", "metadata")),
            )
    return None


def _merge_calibration(
    current: dict[str, Any],
    document: dict[str, Any],
) -> dict[str, Any]:
    bands = current.setdefault("bands", {})
    source = document.get("source") or document.get("scene_id")
    if source and "source" not in current:
        current["source"] = source

    incoming = document.get("bands")
    if incoming is None:
        incoming = document.get("calibration")
    if isinstance(incoming, dict):
        for key, value in incoming.items():
            if isinstance(value, dict) and "scale" in value:
                bands.setdefault(key, value)
    return current


def _looks_like_reflectance(dataset: rasterio.io.DatasetReader) -> bool:
    if dataset.dtypes[0] not in {"float32", "float64"}:
        return False
    sample = dataset.read(1)
    finite = sample[np.isfinite(sample)]
    if finite.size == 0:
        return False
    return bool(finite.max() <= 2.0 and finite.min() >= -1.0)


def _source_fingerprints(raw_dir: Path) -> dict[str, Any]:
    fingerprints: dict[str, Any] = {}
    for filename in (*BAND_FILES.values(), "metadata.json", "calibration.json"):
        path = raw_dir / filename
        if path.is_file():
            stats = path.stat()
            fingerprints[filename] = {
                "size": stats.st_size,
                "mtime_ns": stats.st_mtime_ns,
            }
    return fingerprints


def _reusable_result(
    raw_dir: Path,
    output_dir: Path,
    settings: dict[str, Any],
) -> dict[str, Any] | None:
    metadata_path = output_dir / OUTPUT_METADATA
    if not metadata_path.is_file():
        return None

    try:
        existing = read_json(metadata_path)
    except InvalidMetadataError:
        return None

    if existing.get("processing_version") != PROCESSING_VERSION:
        return None
    if existing.get("processing_settings") != settings:
        return None
    if existing.get("source_fingerprints") != _source_fingerprints(raw_dir):
        return None

    for filename in existing.get("output_filenames", []):
        if not (output_dir / filename).is_file():
            return None

    existing.setdefault("image_id", raw_dir.name)
    return existing


def _sanitize_calibration(calibrations: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for band, values in calibrations.items():
        entry = dict(values)
        nodata = entry.get("nodata")
        if isinstance(nodata, float) and np.isnan(nodata):
            entry["nodata"] = None
        cleaned[band] = entry
    return cleaned


def _build_processing_metadata(
    *,
    raw_dir: Path,
    scene_metadata: dict[str, Any],
    source_assets: dict[str, str],
    calibrations: dict[str, Any],
    settings: dict[str, Any],
    statistics: dict[str, Any] | None,
    reference: dict[str, Any],
    output_filenames: list[str],
    valid_pixels: int,
    total_pixels: int,
) -> dict[str, Any]:
    transform: Affine = reference["transform"]
    crs: CRS = reference["crs"]
    ndvi_block = None
    if statistics is not None:
        ndvi_block = {
            "minimum": statistics["minimum"],
            "maximum": statistics["maximum"],
            "mean": statistics["mean"],
            "median": statistics["median"],
            "standard_deviation": statistics["standard_deviation"],
        }

    valid_percentage = (
        round(100.0 * valid_pixels / total_pixels, 2)
        if total_pixels
        else 0.0
    )

    return {
        "image_id": raw_dir.name,
        "processing_version": PROCESSING_VERSION,
        "source_scene_id": scene_metadata.get("scene_id"),
        "acquisition_date": scene_metadata.get("acquisition_date"),
        "source_assets": source_assets,
        "calibration": _sanitize_calibration(calibrations),
        "scl_classes_used": settings["valid_scl_classes"],
        "processing_settings": settings,
        "ndvi": ndvi_block,
        "valid_pixels": valid_pixels,
        "total_pixels": total_pixels,
        "valid_percentage": valid_percentage,
        "raster": {
            "width": reference["width"],
            "height": reference["height"],
            "crs": crs.to_string(),
            "transform": list(transform)[:6],
            "bounds": list(reference["bounds"]),
            "resolution": list(reference["resolution"]),
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "output_filenames": output_filenames,
        "source_fingerprints": _source_fingerprints(raw_dir),
        "ndvi_statistics": statistics,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


if __name__ == "__main__":
    main()
