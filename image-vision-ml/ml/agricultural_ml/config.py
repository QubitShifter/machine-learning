"""Load the versioned agricultural ML research-dataset configuration."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

from ml.ingestion.manifest import validate_safe_id
from ml.preprocessing.errors import AgriculturalMlError
from ml.preprocessing.raster import project_root


PIPELINE_VERSION = "4.0.0"
SAFE_MODES = {"research_reanalysis", "operational_replay", "perfect_weather_hindcast"}
SOIL_TARGET_VARS = ("swvl1", "swvl2", "swvl3", "swvl4", "theta_root_zone_0_100")
DEFAULT_HORIZONS = (1, 3, 7)
DEFAULT_WINDOWS = (1, 3, 7, 14, 30)


def load_ml_config(path: Path | str) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.is_file():
        raise AgriculturalMlError(f"Configuration file {config_path} is missing.")
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise AgriculturalMlError("Agricultural ML configuration is not valid YAML.") from exc
    if not isinstance(payload, dict):
        raise AgriculturalMlError("Agricultural ML configuration must be a mapping.")
    config = validate_ml_config(payload)
    config["_config_path"] = str(config_path.resolve())
    config["_config_fingerprint"] = hashlib.sha256(
        config_path.read_bytes()
    ).hexdigest()
    return config


def validate_ml_config(payload: dict[str, Any]) -> dict[str, Any]:
    dataset_id = validate_safe_id(str(payload.get("dataset_id") or ""), "dataset_id")
    sources = payload.get("sources") or {}
    for key in ("weather_dataset_id", "soil_dataset_id", "satellite_dataset_id"):
        if not sources.get(key):
            raise AgriculturalMlError(f"sources.{key} is required.")
        validate_safe_id(str(sources[key]), key)

    period = payload.get("period") or {}
    if not period.get("start") or not period.get("end"):
        raise AgriculturalMlError("period.start and period.end are required.")
    if str(period["start"]) > str(period["end"]):
        raise AgriculturalMlError("period.start must not follow period.end.")

    issue = payload.get("issue_time") or {}
    mode = str(issue.get("research_mode") or "research_reanalysis")
    if mode not in SAFE_MODES:
        raise AgriculturalMlError(f"issue_time.research_mode must be one of {sorted(SAFE_MODES)}.")
    if mode == "operational_replay" and issue.get("operational_availability_verified") is True:
        if not issue.get("publication_timestamps_known"):
            raise AgriculturalMlError(
                "operational_replay cannot be verified without publication timestamps."
            )
    if mode == "perfect_weather_hindcast":
        raise AgriculturalMlError(
            "perfect_weather_hindcast is not the default research dataset and must not be enabled here."
        )

    windows = tuple(int(item) for item in (payload.get("feature_windows_days") or DEFAULT_WINDOWS))
    if any(item < 1 for item in windows):
        raise AgriculturalMlError("feature_windows_days must be positive.")

    targets = payload.get("targets") or {}
    variables = tuple(targets.get("variables") or SOIL_TARGET_VARS)
    unknown = [item for item in variables if item not in SOIL_TARGET_VARS]
    if unknown:
        raise AgriculturalMlError(f"Unknown target variables: {unknown}.")
    horizons = tuple(int(item) for item in (targets.get("horizons_days") or DEFAULT_HORIZONS))
    if horizons != DEFAULT_HORIZONS:
        raise AgriculturalMlError("Phase 4.0 horizons must be 1, 3 and 7 days.")

    splits = payload.get("splits") or {}
    for name in ("training", "validation", "test"):
        block = splits.get(name) or {}
        if not block.get("start") or not block.get("end"):
            raise AgriculturalMlError(f"splits.{name}.start and end are required.")

    output = payload.get("output") or {}
    directory = str(output.get("directory") or f"data/processed/ml/{dataset_id}")
    config = dict(payload)
    config["dataset_id"] = dataset_id
    config["pipeline_version"] = str(payload.get("pipeline_version") or PIPELINE_VERSION)
    config["dataset_version"] = str(payload.get("dataset_version") or PIPELINE_VERSION)
    config["feature_windows_days"] = list(windows)
    config["targets"] = {
        **targets,
        "variables": list(variables),
        "horizons_days": list(horizons),
        "aggregation": targets.get("aggregation") or "daily_mean_of_complete_utc_day",
        "change_baseline": targets.get("change_baseline") or "last_complete_historical_day",
        "source_kind": targets.get("source_kind") or "modeled_reanalysis",
        "ground_truth": False,
    }
    config["issue_time"] = {
        **issue,
        "research_mode": mode,
        "operational_availability_verified": False,
        "publication_timestamps_known": bool(issue.get("publication_timestamps_known")),
    }
    config["output"] = {**output, "directory": directory}
    return config


def output_directory(config: dict[str, Any], *, root: Path | None = None) -> Path:
    base = root or project_root()
    return (base / str(config["output"]["directory"])).resolve()
