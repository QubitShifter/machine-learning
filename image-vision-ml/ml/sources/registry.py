"""Load the agricultural data-source registry without downloading products."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ml.preprocessing.raster import project_root


REGISTRY_PATH = Path("docs") / "data_sources" / "registry.yaml"

IMPLEMENTED_STATUSES = {"operational", "implemented"}
PLANNED_STATUSES = {"planned", "unavailable", "paused"}


def registry_path(root: Path | None = None) -> Path:
    return (root or project_root()) / REGISTRY_PATH


def load_source_registry(root: Path | None = None) -> dict[str, Any]:
    path = registry_path(root)
    if not path.is_file():
        return {"sources": [], "path": str(path), "missing": True}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("Source registry must be a mapping.")
    sources = list(payload.get("sources") or [])
    return {
        "title": payload.get("title", "Agricultural data sources"),
        "verified_at_utc": payload.get("verified_at_utc"),
        "sources": sources,
        "counts": {
            "total": len(sources),
            "implemented": sum(
                1 for item in sources if item.get("integration_status") in IMPLEMENTED_STATUSES
            ),
            "planned": sum(
                1 for item in sources if item.get("integration_status") in PLANNED_STATUSES
            ),
        },
        "path": str(path),
        "missing": False,
    }


def get_source(source_id: str, root: Path | None = None) -> dict[str, Any] | None:
    for item in load_source_registry(root).get("sources") or []:
        if item.get("source_id") == source_id:
            return item
    return None
