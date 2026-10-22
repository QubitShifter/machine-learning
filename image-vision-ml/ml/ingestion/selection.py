"""Deterministic scene selection for limited historical downloads."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any


SEASON_ORDER = ("DJF", "MAM", "JJA", "SON")


def season_name(date_text: str) -> str:
    month = _month(date_text)
    if month in {12, 1, 2}:
        return "DJF"
    if month in {3, 4, 5}:
        return "MAM"
    if month in {6, 7, 8}:
        return "JJA"
    return "SON"


def select_requested_scenes(
    records: list[dict[str, Any]],
    scene_ids: list[str],
) -> list[dict[str, Any]]:
    """Return catalog records for explicit scene IDs, preserving request order.

    Duplicate IDs are ignored after the first occurrence. Unknown IDs raise
    ``ValueError`` so a download batch cannot silently substitute another scene.
    """
    if not scene_ids:
        return []
    by_id = {item["scene_id"]: item for item in records}
    missing = [scene_id for scene_id in scene_ids if scene_id not in by_id]
    if missing:
        raise ValueError(
            "Requested scene_id(s) were not in the catalog: " + ", ".join(missing)
        )
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for scene_id in scene_ids:
        if scene_id in seen:
            continue
        seen.add(scene_id)
        selected.append(by_id[scene_id])
    return selected


def select_stratified_scenes(
    records: list[dict[str, Any]],
    *,
    limit: int | None,
    scenes_per_year: int = 3,
) -> list[dict[str, Any]]:
    """Pick a seasonally distributed subset without cloud-cover-only ranking.

    Within each year the first eligible scene from each meteorological
    season is taken in season order (DJF, MAM, JJA, SON). Remaining
    slots are filled from unused seasons, then from later dates in the
    same year. Cloud cover is a quality constraint already applied
    during discovery; it is not the ranking key.
    """
    if limit is None:
        return list(records)
    if limit <= 0:
        return []

    by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        year = _year(record.get("acquisition_date") or record.get("acquisition_datetime"))
        if year is None:
            continue
        by_year[year].append(record)

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    per_year = max(1, scenes_per_year)

    for year in sorted(by_year):
        year_records = sorted(
            by_year[year],
            key=lambda item: item.get("acquisition_datetime") or item.get("acquisition_date") or "",
        )
        by_season: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in year_records:
            by_season[season_name(record.get("acquisition_date") or "")].append(record)

        year_picks: list[dict[str, Any]] = []
        for season in SEASON_ORDER:
            candidates = [
                item for item in by_season.get(season, [])
                if item["scene_id"] not in selected_ids
            ]
            if not candidates:
                continue
            pick = _mid_season_candidate(candidates)
            year_picks.append(pick)
            selected_ids.add(pick["scene_id"])
            if len(year_picks) >= per_year:
                break

        if len(year_picks) < per_year:
            leftovers = [
                item for item in year_records
                if item["scene_id"] not in selected_ids
            ]
            for item in leftovers:
                year_picks.append(item)
                selected_ids.add(item["scene_id"])
                if len(year_picks) >= per_year:
                    break
        selected.extend(year_picks)
        if len(selected) >= limit:
            break

    if len(selected) < limit:
        leftovers = [
            item for item in records
            if item["scene_id"] not in selected_ids
        ]
        leftovers.sort(
            key=lambda item: item.get("acquisition_datetime") or item.get("acquisition_date") or ""
        )
        for item in leftovers:
            selected.append(item)
            if len(selected) >= limit:
                break

    selected.sort(
        key=lambda item: item.get("acquisition_datetime") or item.get("acquisition_date") or ""
    )
    return selected[:limit]


def _mid_season_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Prefer a mid-season date so selection is not lowest-cloud-only."""
    if len(candidates) == 1:
        return candidates[0]
    return candidates[len(candidates) // 2]


def _year(value: Any) -> int | None:
    text = str(value or "")[:10]
    if len(text) < 4:
        return None
    try:
        return int(text[:4])
    except ValueError:
        return None


def _month(value: str) -> int:
    try:
        return datetime.fromisoformat(value[:10]).month
    except ValueError:
        return 0
