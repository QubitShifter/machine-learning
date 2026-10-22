"""Load Phase 4.0 tables and assemble leakage-safe modeling frames."""

from __future__ import annotations

from typing import Any

import pandas as pd

from ml.agricultural_ml.catalog import feature_catalog
from ml.preprocessing.errors import SoilForecastingError
from ml.preprocessing.weather import _maybe_float


FORBIDDEN_PREFIXES = ("target_",)
FORBIDDEN_COLUMNS = {
    "absolute_target", "change_target", "persistence_prediction",
    "missing_reason", "source_checksum", "config_fingerprint",
}


def enabled_feature_sets(config: dict[str, Any]) -> dict[str, list[str]]:
    selected = {}
    for name, block in (config.get("feature_sets") or {}).items():
        if name == "D" or block.get("enabled") is False:
            continue
        columns = [str(item) for item in (block.get("columns") or [])]
        selected[str(name)] = columns
    return selected


def catalog_by_column(ml_config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items = feature_catalog(ml_config).get("features") or []
    return {str(item["column_name"]): item for item in items}


def assert_documented_features(config: dict[str, Any], ml_config: dict[str, Any], columns: list[str]) -> None:
    catalog = catalog_by_column(ml_config)
    missing = [name for name in columns if name not in catalog]
    if missing:
        raise SoilForecastingError(
            f"Predictors are missing from the feature catalog: {missing}."
        )
    for name in columns:
        if name in FORBIDDEN_COLUMNS or name.startswith(FORBIDDEN_PREFIXES):
            raise SoilForecastingError(f"Predictor {name} is not an admissible historical feature.")


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"true", "1", "yes"}


def load_joined_frame(source_dir, *, target_variable: str) -> pd.DataFrame:
    features_path = source_dir / "features_daily.csv"
    targets_path = source_dir / "targets.csv"
    splits_path = source_dir / "split_membership.csv"
    for path in (features_path, targets_path, splits_path):
        if not path.is_file():
            raise SoilForecastingError(f"Required Phase 4.0 table is missing: {path.name}")
    features = pd.read_csv(features_path)
    targets = pd.read_csv(targets_path)
    splits = pd.read_csv(splits_path)
    targets = targets[targets["target_variable"].astype(str) == target_variable].copy()
    splits = splits[splits["target_variable"].astype(str) == target_variable].copy()
    targets["horizon_days"] = targets["horizon_days"].astype(int)
    splits["horizon_days"] = splits["horizon_days"].astype(int)
    if targets.empty or splits.empty:
        raise SoilForecastingError(f"No rows for target variable {target_variable}.")
    merged = targets.merge(
        splits[
            [
                "issue_row_key", "horizon_days", "target_variable", "split",
                "excluded", "exclusion_reason", "target_crosses_next_split",
                "issue_partition",
            ]
        ],
        on=["issue_row_key", "horizon_days", "target_variable"],
        how="inner",
        validate="one_to_one",
    )
    keep_features = [
        column for column in features.columns
        if column == "issue_row_key" or column not in merged.columns
    ]
    frame = merged.merge(features[keep_features], on="issue_row_key", how="inner", validate="many_to_one").copy()
    frame["horizon_days"] = frame["horizon_days"].astype(int)
    frame["excluded_flag"] = frame["excluded"].map(_as_bool)
    frame["target_available_flag"] = frame["target_available"].map(_as_bool)
    frame["absolute_target"] = frame["absolute_target"].map(_maybe_float)
    frame["change_target"] = frame["change_target"].map(_maybe_float)
    return frame


def eligible_mask(frame: pd.DataFrame) -> pd.Series:
    return (
        frame["target_available_flag"]
        & ~frame["excluded_flag"]
        & frame["absolute_target"].notna()
        & frame["split"].isin(["training", "validation", "test"])
    )


def complete_mask(frame: pd.DataFrame, columns: list[str]) -> pd.Series:
    missing = [name for name in columns if name not in frame.columns]
    if missing:
        raise SoilForecastingError(f"Feature columns missing from the table: {missing}.")
    numeric = frame[columns].apply(pd.to_numeric, errors="coerce")
    return numeric.notna().all(axis=1)


def partition_frame(
    frame: pd.DataFrame,
    *,
    split: str,
    horizon: int,
    columns: list[str],
    require_complete: bool = True,
) -> pd.DataFrame:
    mask = eligible_mask(frame) & (frame["split"] == split) & (frame["horizon_days"] == horizon)
    if require_complete:
        mask = mask & complete_mask(frame, columns)
    selected = frame.loc[mask].copy()
    selected.sort_values("issue_date_utc", inplace=True)
    return selected.reset_index(drop=True)


def matrix(frame: pd.DataFrame, columns: list[str]) -> tuple[Any, Any]:
    values = frame[columns].apply(pd.to_numeric, errors="coerce")
    target = frame["absolute_target"].astype(float)
    return values.to_numpy(dtype=float), target.to_numpy(dtype=float)
