"""Horizon-aware chronological splits with target-period purging."""

from __future__ import annotations

from datetime import date
from typing import Any

from ml.agricultural_ml.time_semantics import parse_utc_date, target_date


SPLIT_ORDER = ("training", "validation", "test")


def split_windows(config: dict[str, Any]) -> dict[str, tuple[date, date]]:
    splits = config.get("splits") or {}
    windows = {}
    for name in SPLIT_ORDER:
        block = splits.get(name) or {}
        start = parse_utc_date(block.get("start"))
        end = parse_utc_date(block.get("end"))
        if start is None or end is None:
            raise ValueError(f"splits.{name} needs start and end dates.")
        windows[name] = (start, end)
    return windows


def issue_partition(issue_date: date, windows: dict[str, tuple[date, date]]) -> str | None:
    for name, (start, end) in windows.items():
        if start <= issue_date <= end:
            return name
    return None


def next_partition_start(name: str, windows: dict[str, tuple[date, date]]) -> date | None:
    if name == "training":
        return windows["validation"][0]
    if name == "validation":
        return windows["test"][0]
    return None


def assign_split(
    issue_date: date,
    horizon_days: int,
    windows: dict[str, tuple[date, date]],
    *,
    purge: bool = True,
) -> dict[str, Any]:
    partition = issue_partition(issue_date, windows)
    stamp = target_date(issue_date, horizon_days)
    if partition is None:
        return {
            "split": "out_of_range",
            "excluded": True,
            "exclusion_reason": "issue_date_outside_split_windows",
            "target_date_utc": stamp.isoformat(),
            "target_crosses_next_split": False,
        }
    boundary = next_partition_start(partition, windows)
    crosses = bool(purge and boundary is not None and stamp >= boundary)
    return {
        "split": "excluded_purge" if crosses else partition,
        "excluded": crosses,
        "exclusion_reason": "target_period_crosses_next_split" if crosses else None,
        "target_date_utc": stamp.isoformat(),
        "target_crosses_next_split": crosses,
        "issue_partition": partition,
    }


def build_split_membership(
    target_rows: list[dict[str, Any]],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    windows = split_windows(config)
    purge = bool((config.get("splits") or {}).get("purge_target_crossing", True))
    rows = []
    for item in target_rows:
        issue_date = parse_utc_date(item["issue_date_utc"])
        horizon = int(item["horizon_days"])
        if issue_date is None:
            continue
        assignment = assign_split(issue_date, horizon, windows, purge=purge)
        rows.append({
            "dataset_id": item.get("dataset_id"),
            "issue_row_key": item.get("issue_row_key"),
            "issue_date_utc": item.get("issue_date_utc"),
            "horizon_days": horizon,
            "target_variable": item.get("target_variable"),
            "target_available": item.get("target_available"),
            **assignment,
        })
    return rows
