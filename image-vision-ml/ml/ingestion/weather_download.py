"""Resumable monthly ERA5-Land downloads."""

from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path
from typing import Any, Callable

from ml.ingestion.era5_land import (
    build_boundary_request,
    build_era5_land_request,
    cds_retrieval_area,
    detect_file_format,
    next_month_start,
    partition_months,
    require_cds_auth,
    study_aoi_bbox,
    target_filename,
)
from ml.ingestion.manifest import (
    now_iso,
    read_manifest,
    save_manifest,
    validate_safe_id,
)
from ml.preprocessing.errors import PermanentCdsRequestError, WeatherDownloadError
from ml.preprocessing.raster import project_root


logger = logging.getLogger(__name__)

MONTH_STATUSES = {
    "pending",
    "submitted",
    "downloading",
    "downloaded",
    "processing",
    "processed",
    "failed",
    "requires_review",
}


def default_weather_raw_root() -> Path:
    return project_root() / "data" / "raw" / "weather"


def default_weather_processed_root() -> Path:
    return project_root() / "data" / "processed" / "weather"


def weather_paths(
    dataset_id: str,
    *,
    raw_root: Path | None = None,
    processed_root: Path | None = None,
) -> dict[str, Path]:
    dataset_id = validate_safe_id(dataset_id, "dataset_id")
    raw = (raw_root or default_weather_raw_root()) / dataset_id
    processed = (processed_root or default_weather_processed_root()) / dataset_id
    return {
        "raw": raw,
        "processed": processed,
        "raw_manifest": raw / "manifest.json",
        "processed_manifest": processed / "manifest.json",
        "hourly": raw / "hourly",
        "quality": processed / "quality_report.json",
        "daily_csv": processed / "daily_weather.csv",
        "daily_parquet": processed / "daily_weather.parquet",
        "monthly_csv": processed / "monthly_summary.csv",
        "chart": processed / "weather_timeseries.png",
    }


def empty_weather_manifest(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "dataset_id": config["dataset_id"],
        "bbox": list(config["area"]["bbox"]),
        "retrieval_area": list(cds_retrieval_area(config)),
        "area_crs": config["area"]["crs"],
        "area_name": config["area"]["name"],
        "period": dict(config["period"]),
        "source": dict(config["source"]),
        "variables": list(config["variables"]),
        "spatial": dict(config["spatial"]),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "months": {},
    }


def parse_month(month: str) -> tuple[int, int]:
    try:
        year_text, month_text = month.split("-")
        year = int(year_text)
        month_number = int(month_text)
    except (ValueError, AttributeError) as exc:
        raise WeatherDownloadError("month must use YYYY-MM.") from exc
    if month_number < 1 or month_number > 12:
        raise WeatherDownloadError("month must use YYYY-MM.")
    return year, month_number


def month_integrity(
    hourly_dir: Path,
    record: dict[str, Any],
    *,
    require_boundary: bool = True,
) -> dict[str, Any]:
    """Inspect one month's raw files without modifying them."""
    filename = record.get("filename")
    reasons: list[str] = []
    if not filename:
        return {"complete": False, "status": "incomplete", "reasons": ["missing_filename"]}
    path = hourly_dir / filename
    if not path.is_file():
        return {"complete": False, "status": "incomplete", "reasons": ["missing_hourly_file"]}
    if path.stat().st_size == 0:
        reasons.append("empty_hourly_file")
    try:
        fmt = detect_file_format(path)
    except WeatherDownloadError:
        return {"complete": False, "status": "requires_review", "reasons": ["invalid_format"]}
    checksum = _sha256(path)
    stored = record.get("checksum")
    if stored and stored != checksum:
        return {
            "complete": False,
            "status": "requires_review",
            "reasons": ["checksum_mismatch"],
            "checksum": checksum,
            "format": fmt,
        }
    boundary_name = record.get("boundary_filename")
    if require_boundary:
        if not boundary_name:
            reasons.append("missing_boundary_filename")
        else:
            boundary_path = hourly_dir / boundary_name
            if not boundary_path.is_file():
                reasons.append("missing_boundary_file")
            elif boundary_path.stat().st_size == 0:
                reasons.append("empty_boundary_file")
            else:
                try:
                    detect_file_format(boundary_path)
                except WeatherDownloadError:
                    reasons.append("invalid_boundary_format")
                stored_boundary = record.get("boundary_checksum")
                boundary_checksum = _sha256(boundary_path)
                if stored_boundary and stored_boundary != boundary_checksum:
                    reasons.append("boundary_checksum_mismatch")
    status = "downloaded" if not reasons else (
        "requires_review" if any("mismatch" in item or "invalid" in item for item in reasons)
        else "incomplete"
    )
    return {
        "complete": not reasons,
        "status": status,
        "reasons": reasons,
        "checksum": checksum,
        "format": fmt,
        "filename": filename,
        "boundary_filename": boundary_name,
    }


def plan_weather_downloads(
    config: dict[str, Any],
    *,
    start_month: str | None = None,
    end_month: str | None = None,
    raw_root: Path | None = None,
) -> dict[str, Any]:
    """Classify each UTC month without contacting CDS."""
    period_start = start_month or f"{config['period']['start'][:7]}"
    period_end = end_month or f"{config['period']['end'][:7]}"
    parse_month(period_start)
    parse_month(period_end)
    if period_start > period_end:
        raise WeatherDownloadError("start-month must be on or before end-month.")
    months = partition_months(f"{period_start}-01", f"{period_end}-01")
    paths = weather_paths(config["dataset_id"], raw_root=raw_root)
    manifest = (
        read_manifest(paths["raw_manifest"])
        if paths["raw_manifest"].is_file()
        else empty_weather_manifest(config)
    )
    records = []
    counts = {
        "downloaded": 0,
        "pending": 0,
        "incomplete": 0,
        "failed": 0,
        "requires_review": 0,
        "validated": 0,
    }
    for month in months:
        record = (manifest.get("months") or {}).get(month) or {}
        integrity = None
        if record:
            integrity = month_integrity(
                paths["hourly"],
                record,
                require_boundary=config["downloads"]["include_next_day_boundary"],
            )
            if record.get("status") == "downloaded" and integrity["complete"]:
                status = "downloaded"
                action = "skip"
                reason = "complete files and checksum match"
            elif record.get("status") == "failed":
                status = "failed"
                action = "download"
                reason = record.get("error") or "previous download failed"
            elif integrity["status"] == "requires_review":
                status = "requires_review"
                action = "review"
                reason = ",".join(integrity["reasons"])
            else:
                status = "incomplete"
                action = "download"
                reason = ",".join(integrity["reasons"]) or "incomplete raw files"
        else:
            status = "pending"
            action = "download"
            reason = "not downloaded"
        if status in counts:
            counts[status] += 1
        year, month_number = parse_month(month)
        records.append({
            "month": month,
            "status": status,
            "action": action,
            "reason": reason,
            "boundary_date": str(next_month_start(year, month_number)),
            "integrity": integrity,
        })
    return {
        "dataset_id": config["dataset_id"],
        "study_aoi": study_aoi_bbox(config),
        "retrieval_area": cds_retrieval_area(config),
        "start_month": period_start,
        "end_month": period_end,
        "month_count": len(records),
        "counts": counts,
        "months": records,
    }


def download_weather_range(
    config: dict[str, Any],
    *,
    start_month: str,
    end_month: str,
    dry_run: bool = False,
    resume: bool = False,
    raw_root: Path | None = None,
    client_factory: Callable[..., Any] | None = None,
    retrieve: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Download months sequentially. Dry-run never contacts CDS."""
    plan = plan_weather_downloads(
        config,
        start_month=start_month,
        end_month=end_month,
        raw_root=raw_root,
    )
    if dry_run:
        return {
            "status": "dry_run",
            "execute": False,
            "resume": resume,
            **plan,
        }
    if not resume:
        raise WeatherDownloadError(
            "Refusing to start a multi-month CDS retrieval without --resume. "
            "Review the dry-run plan first, then pass --resume to download "
            "only pending, failed, or incomplete months."
        )
    results = []
    for item in plan["months"]:
        if item["action"] == "skip":
            results.append({
                "month": item["month"],
                "status": "skipped",
                "reason": item["reason"],
            })
            continue
        if item["action"] == "review":
            results.append({
                "month": item["month"],
                "status": "requires_review",
                "reason": item["reason"],
            })
            continue
        result = download_weather_month(
            config,
            item["month"],
            dry_run=False,
            raw_root=raw_root,
            client_factory=client_factory,
            retrieve=retrieve,
        )
        results.append(result)
        if result.get("status") == "failed":
            break
    refreshed = plan_weather_downloads(
        config,
        start_month=start_month,
        end_month=end_month,
        raw_root=raw_root,
    )
    return {
        "status": "completed" if refreshed["counts"]["pending"] == 0
        and refreshed["counts"]["failed"] == 0
        and refreshed["counts"]["incomplete"] == 0
        else "partial",
        "execute": True,
        "resume": True,
        "results": results,
        **refreshed,
    }


def download_weather_month(
    config: dict[str, Any],
    month: str,
    *,
    dry_run: bool = False,
    raw_root: Path | None = None,
    client_factory: Callable[..., Any] | None = None,
    retrieve: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    year, month_number = parse_month(month)
    request = build_era5_land_request(config, year=year, month=month_number)
    boundary = None
    if config["downloads"]["include_next_day_boundary"]:
        boundary = build_boundary_request(config, year, month_number)
    study_aoi = study_aoi_bbox(config)
    retrieval_area = cds_retrieval_area(config)
    estimate = {
        "month": month,
        "variables": list(config["variables"]),
        "days": len(request["day"]),
        "hours": len(request["time"]),
        "study_aoi": study_aoi,
        "retrieval_area": retrieval_area,
        "area": retrieval_area,
        "data_format": request["data_format"],
        "includes_next_day_00utc": boundary is not None,
        "boundary_date": None if boundary is None else str(next_month_start(year, month_number)),
    }
    if dry_run:
        return {
            "status": "dry_run",
            "study_aoi": study_aoi,
            "retrieval_area": retrieval_area,
            "request": request,
            "boundary_request": boundary,
            "estimate": estimate,
        }

    require_cds_auth()
    paths = weather_paths(config["dataset_id"], raw_root=raw_root)
    paths["hourly"].mkdir(parents=True, exist_ok=True)
    manifest = (
        read_manifest(paths["raw_manifest"])
        if paths["raw_manifest"].is_file()
        else empty_weather_manifest(config)
    )
    existing = (manifest.get("months") or {}).get(month) or {}
    integrity = month_integrity(
        paths["hourly"],
        existing,
        require_boundary=config["downloads"]["include_next_day_boundary"],
    ) if existing else None
    if existing.get("status") == "downloaded" and integrity and integrity["complete"]:
        return {
            "status": "skipped",
            "month": month,
            "estimate": estimate,
            "reason": "complete files and checksum match",
        }
    final_hourly = paths["hourly"] / target_filename(month, existing.get("format") or "netcdf")
    if existing.get("filename"):
        existing_path = paths["hourly"] / existing["filename"]
        if existing_path.is_file() and integrity and not integrity["complete"]:
            if "checksum_mismatch" in integrity["reasons"] or "invalid_format" in integrity["reasons"]:
                raise WeatherDownloadError(
                    f"Refusing to overwrite {existing_path.name}: {', '.join(integrity['reasons'])}."
                )

    _set_month(manifest, month, status="submitted", request=request)
    save_manifest(paths["raw_manifest"], manifest)
    try:
        hourly_path = _retrieve_file(
            config,
            request,
            paths["hourly"] / f"{month}.download",
            client_factory=client_factory,
            retrieve=retrieve,
        )
        fmt = detect_file_format(hourly_path)
        final_hourly = paths["hourly"] / target_filename(month, fmt)
        if hourly_path != final_hourly:
            if final_hourly.exists():
                raise WeatherDownloadError(f"Refusing to overwrite {final_hourly.name}.")
            hourly_path.replace(final_hourly)
        boundary_name = None
        boundary_checksum = None
        if boundary is not None:
            boundary_tmp = paths["hourly"] / f"{month}.boundary.download"
            boundary_path = _retrieve_file(
                config,
                boundary,
                boundary_tmp,
                client_factory=client_factory,
                retrieve=retrieve,
            )
            boundary_fmt = detect_file_format(boundary_path)
            final_boundary = paths["hourly"] / target_filename(month, boundary_fmt, boundary=True)
            if boundary_path != final_boundary:
                if final_boundary.exists():
                    raise WeatherDownloadError(f"Refusing to overwrite {final_boundary.name}.")
                boundary_path.replace(final_boundary)
            boundary_name = final_boundary.name
            boundary_checksum = _sha256(final_boundary)
        _set_month(
            manifest,
            month,
            status="downloaded",
            request=request,
            filename=final_hourly.name,
            format=fmt,
            checksum=_sha256(final_hourly),
            boundary_filename=boundary_name,
            boundary_checksum=boundary_checksum,
            error=None,
        )
        save_manifest(paths["raw_manifest"], manifest)
        return {
            "status": "downloaded",
            "month": month,
            "filename": final_hourly.name,
            "format": fmt,
            "estimate": estimate,
        }
    except KeyboardInterrupt:
        _set_month(manifest, month, status="failed", error="Interrupted before completion.")
        save_manifest(paths["raw_manifest"], manifest)
        raise
    except Exception as exc:
        _set_month(manifest, month, status="failed", error=str(exc))
        save_manifest(paths["raw_manifest"], manifest)
        if isinstance(exc, WeatherDownloadError):
            raise
        raise WeatherDownloadError(str(exc)) from exc


def _retrieve_file(
    config: dict[str, Any],
    request: dict[str, Any],
    target: Path,
    *,
    client_factory: Callable[..., Any] | None,
    retrieve: Callable[..., Any] | None,
) -> Path:
    retries = int(config["downloads"]["retries"])
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            if retrieve is not None:
                retrieve(config["source"]["dataset"], request, str(target))
            else:
                factory = client_factory or _default_client
                client = factory()
                client.retrieve(config["source"]["dataset"], request, str(target))
            if not target.is_file() or target.stat().st_size == 0:
                raise WeatherDownloadError("CDS returned an empty file.")
            return target
        except Exception as exc:
            last_error = exc
            if _is_permanent_cds_error(exc):
                raise PermanentCdsRequestError(
                    "CDS rejected this request permanently "
                    f"({_error_status(exc) or 'non-retriable'}). "
                    "The retrieval area must contain at least one ERA5-Land "
                    "grid point. Retrying the same spatial crop will fail."
                ) from exc
            logger.warning("CDS retrieve attempt %s/%s failed: %s", attempt, retries, exc)
            time.sleep(min(2 ** (attempt - 1), 8))
    raise WeatherDownloadError("CDS retrieve failed after retries.") from last_error


def _is_permanent_cds_error(exc: Exception) -> bool:
    status = _error_status(exc)
    if status == 400:
        return True
    text = str(exc).lower()
    markers = (
        "multiadaptornodataerror",
        "non-empty area crop/mask",
        "invalid spatial",
        "http 400",
        "400 client error",
        "bad request",
    )
    return any(marker in text for marker in markers)


def _error_status(exc: Exception) -> int | None:
    for attr in ("status_code", "status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    if response is not None:
        value = getattr(response, "status_code", None)
        if isinstance(value, int):
            return value
    return None


def _default_client():
    import cdsapi

    return cdsapi.Client()


def _set_month(manifest: dict[str, Any], month: str, **fields: Any) -> None:
    months = manifest.setdefault("months", {})
    current = dict(months.get(month) or {"month": month})
    current.update(fields)
    current["month"] = month
    if current.get("status") not in MONTH_STATUSES:
        raise ValueError(f"Unknown weather month status: {current.get('status')}")
    current["updated_at"] = now_iso()
    months[month] = current
    manifest["updated_at"] = now_iso()


def _month_complete(hourly_dir: Path, record: dict[str, Any]) -> bool:
    return month_integrity(hourly_dir, record, require_boundary=False)["complete"]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
