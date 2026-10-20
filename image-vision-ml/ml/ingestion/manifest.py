"""Atomic dataset and scene manifest management."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")

SCENE_STATUSES = (
    "discovered",
    "downloading",
    "downloaded",
    "processing",
    "processed",
    "failed",
    "skipped",
)


def validate_safe_id(value: str, label: str = "identifier") -> str:
    if not SAFE_ID_PATTERN.fullmatch(value or ""):
        raise ValueError(
            f"{label} must be a local name without path separators."
        )
    return value


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.stem}.tmp{path.suffix}")
    try:
        temporary.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def read_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path.name)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Manifest {path.name} is not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Manifest {path.name} must contain a JSON object.")
    return payload


def empty_manifest(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "dataset_id": config["dataset_id"],
        "bbox": list(config["area"]["bbox"]),
        "area_crs": config["area"]["crs"],
        "area_name": config["area"]["name"],
        "period": dict(config["period"]),
        "source": dict(config["source"]),
        "filters": dict(config["filters"]),
        "discovery": dict(config.get("discovery") or config["filters"]),
        "processing": dict(config["processing"]),
        "quality": dict(config.get("quality") or {}),
        "downloads": dict(config.get("downloads") or {}),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "processing_version": None,
        "target_grid": None,
        "scenes": {},
    }


def upsert_scene(
    manifest: dict[str, Any],
    scene_id: str,
    **fields: Any,
) -> dict[str, Any]:
    validate_safe_id(scene_id, "scene_id")
    scenes = manifest.setdefault("scenes", {})
    current = dict(scenes.get(scene_id) or {"scene_id": scene_id})
    current.update(fields)
    current["scene_id"] = scene_id
    if "status" in current and current["status"] not in SCENE_STATUSES:
        raise ValueError(f"Unknown scene status: {current['status']}")
    scenes[scene_id] = current
    manifest["updated_at"] = now_iso()
    return current


def save_manifest(path: Path, manifest: dict[str, Any]) -> None:
    write_json_atomic(path, manifest)


def scene_records(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    scenes = list(manifest.get("scenes", {}).values())
    scenes.sort(key=lambda item: str(item.get("acquisition_date") or ""))
    return scenes
