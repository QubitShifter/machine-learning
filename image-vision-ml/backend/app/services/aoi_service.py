"""Read-only operational AOI registry plus isolated draft proposals."""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ml.aoi.geometry import AoiGeometryError, geometry_payload
from ml.aoi.registry import load_registry
from ml.preprocessing.raster import project_root


DRAFTS_NAME = "aoi_drafts.json"
_LOCK = threading.RLock()


def default_drafts_path() -> Path:
    return project_root() / "data" / "cache" / DRAFTS_NAME


def list_areas() -> dict[str, Any]:
    registry = load_registry()
    registry["drafts"] = _read_drafts()
    return registry


def create_draft(
    *,
    name: str | None,
    geometry_type: str,
    bbox: list[float] | None,
    coordinates: list[list[float]] | None,
) -> dict[str, Any]:
    geometry = geometry_payload(
        kind=geometry_type,
        bbox=bbox,
        coordinates=coordinates,
    )
    record = {
        "draft_id": str(uuid.uuid4()),
        "name": name or "Untitled draft AOI",
        "status": "draft",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "geometry": geometry,
        "downloads_started": False,
        "operational": False,
        "note": (
            "Draft study area only. No Sentinel-2, ERA5 weather, or ERA5-Land "
            "soil download is started. The Plovdiv operational dataset is unchanged."
        ),
    }
    drafts = _read_drafts()
    drafts.append(record)
    _write_drafts(drafts)
    return record


def delete_draft(draft_id: str) -> dict[str, Any]:
    drafts = _read_drafts()
    remaining = [item for item in drafts if item.get("draft_id") != draft_id]
    if len(remaining) == len(drafts):
        raise AoiGeometryError(f"Draft {draft_id} was not found.")
    _write_drafts(remaining)
    return {"deleted": True, "draft_id": draft_id}


def _read_drafts() -> list[dict[str, Any]]:
    path = default_drafts_path()
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(payload, dict):
        payload = payload.get("drafts") or []
    return [item for item in payload if isinstance(item, dict)]


def _write_drafts(drafts: list[dict[str, Any]]) -> None:
    path = default_drafts_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": "3.5.0",
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "drafts": drafts,
    }
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with _LOCK:
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(path)
