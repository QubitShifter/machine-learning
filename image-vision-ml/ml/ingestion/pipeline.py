"""CLI-facing satellite dataset workflow."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ml.analysis.timeseries import build_ndvi_timeseries, write_timeseries_outputs
from ml.ingestion.config import load_dataset_config
from ml.ingestion.download import download_scenes
from ml.ingestion.manifest import (
    empty_manifest,
    read_manifest,
    save_manifest,
    scene_records,
    upsert_scene,
    validate_safe_id,
    write_json_atomic,
)
from ml.ingestion.selection import select_stratified_scenes
from ml.ingestion.stac import search_sentinel2
from ml.preprocessing.errors import DatasetNotFoundError, InvalidMetadataError
from ml.preprocessing.grid import build_target_grid, serialize_grid
from ml.preprocessing.raster import (
    PROCESSING_VERSION,
    default_processed_root,
    default_raw_root,
    process_local_dataset,
    read_json,
)
from ml.validation.dataset_quality import (
    STATUS_VALID,
    evaluate_dataset_quality,
    write_quality_outputs,
)


logger = logging.getLogger(__name__)


def dataset_paths(
    dataset_id: str,
    *,
    raw_root: Path | None = None,
    processed_root: Path | None = None,
) -> dict[str, Path]:
    dataset_id = validate_safe_id(dataset_id, "dataset_id")
    raw = (raw_root or default_raw_root()) / dataset_id
    processed = (processed_root or default_processed_root()) / dataset_id
    return {
        "raw": raw,
        "processed": processed,
        "raw_manifest": raw / "manifest.json",
        "processed_manifest": processed / "manifest.json",
        "scenes_raw": raw / "scenes",
        "scenes_processed": processed / "scenes",
        "timeseries": processed / "timeseries",
        "quality": processed / "quality",
        "discovered": raw / "discovered.json",
    }


def search_dataset(config_path: Path) -> dict[str, Any]:
    config = load_dataset_config(config_path)
    records = search_sentinel2(
        config["area"]["bbox"],
        config["period"]["start"],
        config["period"]["end"],
        config["discovery"]["max_scene_cloud_cover"],
        stac_url=config["source"]["stac_url"],
        collection=config["source"]["collection"],
        min_footprint_overlap_pct=config["discovery"]["min_footprint_overlap_pct"],
        target_crs=config["processing"]["target_crs"],
    )
    paths = dataset_paths(config["dataset_id"])
    paths["raw"].mkdir(parents=True, exist_ok=True)
    if paths["raw_manifest"].is_file():
        manifest = read_manifest(paths["raw_manifest"])
    else:
        manifest = empty_manifest(config)
    for record in records:
        existing = manifest.get("scenes", {}).get(record["scene_id"], {})
        if existing.get("status") in {"downloaded", "processed"}:
            upsert_scene(
                manifest,
                record["scene_id"],
                acquisition_date=record["acquisition_date"],
                acquisition_datetime=record["acquisition_datetime"],
                cloud_cover=record.get("cloud_cover"),
                aoi_coverage=record.get("aoi_coverage"),
                footprint_overlap_pct=record.get("footprint_overlap_pct"),
                bbox_overlap_pct=record.get("bbox_overlap_pct"),
                platform=record.get("platform"),
                mgrs_tile=record.get("mgrs_tile"),
            )
            continue
        upsert_scene(
            manifest,
            record["scene_id"],
            status=existing.get("status") or "discovered",
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
        )
    save_manifest(paths["raw_manifest"], manifest)
    write_json_atomic(paths["discovered"], {
        "dataset_id": config["dataset_id"],
        "bbox": list(config["area"]["bbox"]),
        "period": dict(config["period"]),
        "discovered": len(records),
        "records": records,
    })
    return {
        "dataset_id": config["dataset_id"],
        "discovered": len(records),
        "records": records,
        "manifest": str(paths["raw_manifest"].name),
    }


def download_dataset(
    config_path: Path,
    *,
    limit: int | None = None,
    dry_run: bool = False,
    raw_root: Path | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    config = load_dataset_config(config_path)
    paths = dataset_paths(config["dataset_id"], raw_root=raw_root)
    cached = None if refresh else _load_cached_discovery(paths["discovered"], config)
    if cached is None:
        result = search_dataset(config_path)
        records = result["records"]
    else:
        records = cached["records"]
        logger.info("Reusing %s cached STAC records.", len(records))
        if not paths["raw_manifest"].is_file():
            search_dataset(config_path)
    manifest = read_manifest(paths["raw_manifest"])
    if limit is None:
        limit = int(config["downloads"]["max_scenes_per_run"])
    selected = select_stratified_scenes(
        records,
        limit=limit,
        scenes_per_year=int(config["downloads"]["scenes_per_year"]),
    )
    return download_scenes(
        selected,
        paths["raw"],
        config["area"]["bbox"],
        manifest,
        paths["raw_manifest"],
        limit=None,
        dry_run=dry_run,
    )


def process_dataset(
    config_path: Path,
    *,
    raw_root: Path | None = None,
    processed_root: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    config = load_dataset_config(config_path)
    paths = dataset_paths(
        config["dataset_id"],
        raw_root=raw_root,
        processed_root=processed_root,
    )
    if not paths["raw_manifest"].is_file():
        raise DatasetNotFoundError(
            f"Unknown satellite dataset: {config['dataset_id']}"
        )
    manifest = read_manifest(paths["raw_manifest"])
    target_grid = build_target_grid(
        config["area"]["bbox"],
        source_crs=config["area"]["crs"],
        target_crs=config["processing"]["target_crs"],
        resolution_m=config["processing"]["target_resolution_m"],
    )
    processed_manifest = (
        read_manifest(paths["processed_manifest"])
        if paths["processed_manifest"].is_file()
        else empty_manifest(config)
    )
    if processed_manifest.get("target_grid") and not force:
        existing = processed_manifest["target_grid"]
        incoming = serialize_grid(target_grid)
        if (
            existing.get("crs") != incoming["crs"]
            or existing.get("width") != incoming["width"]
            or existing.get("height") != incoming["height"]
            or existing.get("transform") != incoming["transform"]
        ):
            raise InvalidMetadataError(
                "Canonical target grid changed after scenes were processed. "
                "Re-run process with --force after invalidating incompatible outputs."
            )
    processed_manifest["target_grid"] = serialize_grid(target_grid)
    processed_manifest["processing_version"] = PROCESSING_VERSION
    processed = 0
    failed = 0
    skipped = 0

    for record in scene_records(manifest):
        if record.get("status") not in {"downloaded", "processed"}:
            continue
        scene_id = record["scene_id"]
        raw_dir = paths["scenes_raw"] / scene_id
        output_dir = paths["scenes_processed"] / scene_id
        upsert_scene(processed_manifest, scene_id, status="processing")
        save_manifest(paths["processed_manifest"], processed_manifest)
        try:
            result = process_local_dataset(
                raw_dir,
                output_dir,
                generate_rgb=True,
                generate_ndvi=config["processing"]["calculate_ndvi"],
                apply_scl_mask=config["processing"]["apply_scl_mask"],
                valid_scl_classes=tuple(
                    config["processing"]["valid_scl_classes"]
                ),
                force=force,
                target_grid=target_grid,
                ndvi_filename="ndvi.tif",
                ndvi_preview_filename="ndvi_preview.png",
                statistics_filename="statistics.json",
            )
            upsert_scene(
                processed_manifest,
                scene_id,
                status="processed",
                acquisition_date=record.get("acquisition_date"),
                cloud_cover=record.get("cloud_cover"),
                aoi_coverage=record.get("aoi_coverage"),
                footprint_overlap_pct=record.get("footprint_overlap_pct"),
                valid_pixels=result.get("valid_pixels"),
                total_pixels=result.get("total_pixels"),
                valid_percentage=result.get("valid_percentage"),
                ndvi=result.get("ndvi"),
                error=None,
            )
            upsert_scene(manifest, scene_id, status="processed")
            processed += 1
        except Exception as exc:
            upsert_scene(
                processed_manifest,
                scene_id,
                status="failed",
                error=str(exc),
            )
            failed += 1
            logger.warning("Failed to process %s: %s", scene_id, exc)

    save_manifest(paths["raw_manifest"], manifest)
    save_manifest(paths["processed_manifest"], processed_manifest)
    return {
        "dataset_id": config["dataset_id"],
        "processed": processed,
        "failed": failed,
        "skipped": skipped,
        "target_grid": processed_manifest["target_grid"],
    }


def generate_dataset_timeseries(
    config_path: Path,
    *,
    raw_root: Path | None = None,
    processed_root: Path | None = None,
) -> dict[str, Any]:
    config = load_dataset_config(config_path)
    paths = dataset_paths(
        config["dataset_id"],
        raw_root=raw_root,
        processed_root=processed_root,
    )
    if not paths["processed_manifest"].is_file():
        raise DatasetNotFoundError(
            f"Unknown satellite dataset: {config['dataset_id']}"
        )
    manifest = read_manifest(paths["processed_manifest"])
    quality_path = paths["quality"] / "dataset_quality.json"
    validated_ids = None
    if quality_path.is_file():
        quality_payload = read_json(quality_path)
        validated_ids = {
            item["scene_id"]
            for item in quality_payload.get("scenes") or []
            if item.get("quality_status") == STATUS_VALID
        }
    observations = []
    for record in scene_records(manifest):
        if record.get("status") != "processed":
            continue
        stats_path = paths["scenes_processed"] / record["scene_id"] / "statistics.json"
        stats = read_json(stats_path) if stats_path.is_file() else {}
        ndvi = record.get("ndvi") or {}
        observations.append({
            "scene_id": record["scene_id"],
            "date": record.get("acquisition_date"),
            "mean": ndvi.get("mean", stats.get("mean")),
            "median": ndvi.get("median", stats.get("median")),
            "standard_deviation": ndvi.get(
                "standard_deviation", stats.get("standard_deviation")
            ),
            "minimum": ndvi.get("minimum", stats.get("minimum")),
            "maximum": ndvi.get("maximum", stats.get("maximum")),
            "valid_pixels": record.get("valid_pixels", stats.get("valid_pixels")),
            "total_pixels": record.get("total_pixels", stats.get("total_pixels")),
            "valid_percentage": record.get(
                "valid_percentage", stats.get("valid_percentage")
            ),
            "cloud_cover": record.get("cloud_cover"),
            "aoi_coverage": record.get("aoi_coverage"),
        })
    if not observations:
        raise InvalidMetadataError(
            "No processed NDVI observations are available."
        )
    payload = build_ndvi_timeseries(
        observations,
        include_partial_coverage=config["quality"][
            "include_partial_coverage_in_full_series"
        ],
        validated_scene_ids=validated_ids,
        period_start=config["period"]["start"],
        period_end=config["period"]["end"],
    )
    payload["dataset_id"] = config["dataset_id"]
    write_timeseries_outputs(
        payload,
        paths["timeseries"],
        title=f"NDVI time series - {config['dataset_id']}",
    )
    return payload


def validate_dataset(
    config_path: Path,
    *,
    raw_root: Path | None = None,
    processed_root: Path | None = None,
) -> dict[str, Any]:
    config = load_dataset_config(config_path)
    paths = dataset_paths(
        config["dataset_id"],
        raw_root=raw_root,
        processed_root=processed_root,
    )
    payload = evaluate_dataset_quality(
        config["dataset_id"],
        raw_root=paths["raw"].parent,
        processed_root=paths["processed"].parent,
        quality=config["quality"],
        config=config,
    )
    for scene in payload["scenes"]:
        scene_dir = paths["scenes_processed"] / str(scene.get("scene_id") or "unknown")
        if scene.get("scene_id"):
            write_json_atomic(scene_dir / "quality_report.json", scene)
    write_quality_outputs(payload, paths["quality"])
    return payload


def generate_dataset_report(
    config_path: Path,
    *,
    raw_root: Path | None = None,
    processed_root: Path | None = None,
) -> dict[str, Any]:
    quality = validate_dataset(
        config_path,
        raw_root=raw_root,
        processed_root=processed_root,
    )
    try:
        series = generate_dataset_timeseries(
            config_path,
            raw_root=raw_root,
            processed_root=processed_root,
        )
    except (DatasetNotFoundError, InvalidMetadataError) as exc:
        logger.warning("Time-series report skipped: %s", exc)
        series = None
    paths = dataset_paths(
        quality["dataset_id"],
        raw_root=raw_root,
        processed_root=processed_root,
    )
    return {
        "dataset_id": quality["dataset_id"],
        "quality": quality["dataset"],
        "training_readiness": quality["training_readiness"],
        "timeseries_observations": None if series is None else series.get("observation_count"),
        "artifacts": {
            "quality_json": "dataset_quality.json",
            "quality_csv": "dataset_quality.csv",
            "training_readiness": "training_readiness.json",
            "timeseries_dir": str(paths["timeseries"].name),
        },
    }


def _load_cached_discovery(
    path: Path,
    config: dict[str, Any],
) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = read_json(path)
    except Exception:
        return None
    if not isinstance(payload, dict) or not payload.get("records"):
        return None
    expected_bbox = [float(value) for value in config["area"]["bbox"]]
    cached_bbox = [float(value) for value in payload.get("bbox") or []]
    if cached_bbox != expected_bbox:
        return None
    if payload.get("period") != config["period"]:
        return None
    return payload
