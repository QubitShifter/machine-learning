"""Restartable windowed Sentinel-2 COG downloads."""

from __future__ import annotations

import hashlib
import logging
import shutil
from pathlib import Path
from typing import Any

import rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds, transform as window_transform

from ml.ingestion.manifest import (
    save_manifest,
    upsert_scene,
    validate_safe_id,
    write_json_atomic,
)
from ml.preprocessing.calibration import calibration_document_from_item
from ml.preprocessing.errors import DownloadError
from ml.preprocessing.raster import BAND_FILES, write_geotiff


logger = logging.getLogger(__name__)

BAND_ASSET_NAMES = {
    "B02": "blue",
    "B03": "green",
    "B04": "red",
    "B08": "nir",
    "SCL": "scl",
}

BYTES_PER_PIXEL = {
    "B02": 2,
    "B03": 2,
    "B04": 2,
    "B08": 2,
    "SCL": 1,
}


def estimate_download(
    records: list[dict[str, Any]],
    target_pixels: int,
) -> dict[str, Any]:
    per_scene = sum(BYTES_PER_PIXEL.values()) * target_pixels
    return {
        "scenes": len(records),
        "estimated_bytes": per_scene * len(records),
        "estimated_mb": round(per_scene * len(records) / (1024 * 1024), 2),
        "bands": list(BAND_FILES),
    }


def download_scenes(
    records: list[dict[str, Any]],
    dataset_dir: Path,
    bbox: tuple[float, float, float, float],
    manifest: dict[str, Any],
    manifest_path: Path,
    *,
    limit: int | None = None,
    dry_run: bool = False,
    opener=None,
) -> dict[str, Any]:
    """Download AOI windows for selected scenes.

    Already downloaded and checksum-verified scenes are skipped.
    """
    selected = records[:limit] if limit else list(records)
    estimate = estimate_download(selected, target_pixels=90_000)
    if dry_run:
        return {
            "status": "dry_run",
            "selected": [record["scene_id"] for record in selected],
            "selected_records": [
                {
                    "scene_id": record["scene_id"],
                    "acquisition_date": record.get("acquisition_date"),
                    "mgrs_tile": record.get("mgrs_tile"),
                    "cloud_cover": record.get("cloud_cover"),
                    "footprint_overlap_pct": record.get("footprint_overlap_pct"),
                    "aoi_coverage": record.get("aoi_coverage"),
                }
                for record in selected
            ],
            "estimate": estimate,
        }

    _check_disk_space(dataset_dir, estimate["estimated_bytes"])
    downloaded = 0
    skipped = 0
    failed = 0

    for record in selected:
        scene_id = validate_safe_id(record["scene_id"], "scene_id")
        scene_dir = dataset_dir / "scenes" / scene_id
        if _scene_complete(scene_dir, manifest.get("scenes", {}).get(scene_id)):
            skipped += 1
            continue
        upsert_scene(manifest, scene_id, status="downloading", error=None)
        save_manifest(manifest_path, manifest)
        try:
            metadata, checksums = _download_scene_window(
                record,
                scene_dir,
                bbox,
                opener=opener,
            )
            upsert_scene(
                manifest,
                scene_id,
                status="downloaded",
                acquisition_date=record["acquisition_date"],
                acquisition_datetime=record["acquisition_datetime"],
                cloud_cover=record.get("cloud_cover"),
                aoi_coverage=record.get("aoi_coverage"),
                footprint_overlap_pct=record.get("footprint_overlap_pct"),
                bbox_overlap_pct=record.get("bbox_overlap_pct"),
                platform=record.get("platform"),
                mgrs_tile=record.get("mgrs_tile"),
                processing_baseline=record.get("processing_baseline"),
                source_urls={
                    name: asset["href"]
                    for name, asset in record.get("assets", {}).items()
                },
                checksums=checksums,
                expected_bands=list(BAND_FILES),
                error=None,
            )
            save_manifest(manifest_path, manifest)
            downloaded += 1
            logger.info("Downloaded scene %s", scene_id)
        except KeyboardInterrupt:
            _cleanup_partial(scene_dir)
            upsert_scene(
                manifest,
                scene_id,
                status="failed",
                error="Interrupted before the scene was complete.",
            )
            save_manifest(manifest_path, manifest)
            raise
        except Exception as exc:
            _cleanup_partial(scene_dir)
            retries = int(manifest.get("scenes", {}).get(scene_id, {}).get("retries", 0)) + 1
            upsert_scene(
                manifest,
                scene_id,
                status="failed",
                error=str(exc),
                retries=retries,
            )
            save_manifest(manifest_path, manifest)
            failed += 1
            logger.warning("Failed to download %s: %s", scene_id, exc)

    return {
        "status": "completed",
        "downloaded": downloaded,
        "skipped": skipped,
        "failed": failed,
        "estimate": estimate,
    }


def _download_scene_window(
    record: dict[str, Any],
    scene_dir: Path,
    bbox: tuple[float, float, float, float],
    opener=None,
) -> tuple[dict[str, Any], dict[str, str]]:
    scene_dir.mkdir(parents=True, exist_ok=True)
    checksums: dict[str, str] = {}
    open_raster = opener or rasterio.open

    for band, asset_name in BAND_ASSET_NAMES.items():
        asset = record.get("assets", {}).get(asset_name)
        if asset is None:
            raise DownloadError(f"Scene is missing asset {asset_name}.")
        href = asset["href"]
        with open_raster(href) as src:
            bounds = transform_bounds("EPSG:4326", src.crs, *bbox)
            window = from_bounds(*bounds, transform=src.transform)
            window = window.round_offsets().round_lengths()
            data = src.read(1, window=window)
            if data.size == 0:
                raise DownloadError(f"Empty raster window for {band}.")
            profile = src.profile.copy()
            profile.update(
                height=data.shape[0],
                width=data.shape[1],
                transform=window_transform(window, src.transform),
                count=1,
            )
            path = scene_dir / BAND_FILES[band]
            write_geotiff(
                path,
                data,
                {
                    "crs": profile["crs"],
                    "transform": profile["transform"],
                    "width": data.shape[1],
                    "height": data.shape[0],
                },
                src.nodata,
            )
            checksums[BAND_FILES[band]] = _sha256(path)

    metadata = {
        "scene_id": record["scene_id"],
        "acquisition_date": record["acquisition_datetime"],
        "cloud_cover": record.get("cloud_cover"),
        "bbox": list(bbox),
        "scene_bbox": record.get("bbox"),
        "collection": record.get("collection"),
        "stac_url": record.get("stac_url"),
        "aoi_coverage": record.get("aoi_coverage"),
        "footprint_overlap_pct": record.get("footprint_overlap_pct"),
        "bbox_overlap_pct": record.get("bbox_overlap_pct"),
        "platform": record.get("platform"),
        "mgrs_tile": record.get("mgrs_tile"),
        "processing_baseline": record.get("processing_baseline"),
        "boa_offset_applied": record.get("boa_offset_applied"),
        "assets": {
            name: asset["href"]
            for name, asset in record.get("assets", {}).items()
        },
    }
    write_json_atomic(scene_dir / "metadata.json", metadata)

    calibration = calibration_document_from_item(
        record["scene_id"],
        {
            "earthsearch:boa_offset_applied": record.get("boa_offset_applied"),
            "s2:processing_baseline": record.get("processing_baseline"),
        },
        record.get("assets", {}),
        BAND_ASSET_NAMES,
    )
    write_json_atomic(scene_dir / "calibration.json", calibration)
    return metadata, checksums


def _scene_complete(scene_dir: Path, record: dict[str, Any] | None) -> bool:
    if not record or record.get("status") not in {"downloaded", "processed"}:
        return False
    checksums = record.get("checksums") or {}
    for filename in BAND_FILES.values():
        path = scene_dir / filename
        if not path.is_file():
            return False
        expected = checksums.get(filename)
        if expected and _sha256(path) != expected:
            return False
    return (scene_dir / "metadata.json").is_file()


def _cleanup_partial(scene_dir: Path) -> None:
    if scene_dir.exists():
        shutil.rmtree(scene_dir)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _check_disk_space(path: Path, needed: int) -> None:
    path.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(path)
    if usage.free < needed * 2:
        raise DownloadError(
            "Insufficient free disk space for the requested download."
        )
