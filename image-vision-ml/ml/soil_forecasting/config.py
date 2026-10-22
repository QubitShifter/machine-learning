"""Load the versioned soil-forecasting experiment configuration."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

from ml.ingestion.manifest import validate_safe_id
from ml.preprocessing.errors import SoilForecastingError
from ml.preprocessing.raster import project_root


PIPELINE_VERSION = "4.1.0"
PRIMARY_TARGET = "swvl1"
DEFAULT_HORIZONS = (1, 3, 7)


def load_experiment_config(path: Path | str) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.is_file():
        raise SoilForecastingError(f"Experiment configuration {config_path} is missing.")
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise SoilForecastingError("Experiment configuration is not valid YAML.") from exc
    if not isinstance(payload, dict):
        raise SoilForecastingError("Experiment configuration must be a mapping.")
    config = validate_experiment_config(payload)
    config["_config_path"] = str(config_path.resolve())
    config["_config_fingerprint"] = hashlib.sha256(config_path.read_bytes()).hexdigest()
    return config


def validate_experiment_config(payload: dict[str, Any]) -> dict[str, Any]:
    experiment_id = validate_safe_id(str(payload.get("experiment_id") or ""), "experiment_id")
    source = payload.get("source") or {}
    if not source.get("ml_dataset_id") or not source.get("directory"):
        raise SoilForecastingError("source.ml_dataset_id and source.directory are required.")
    validate_safe_id(str(source["ml_dataset_id"]), "ml_dataset_id")

    target = payload.get("target") or {}
    if str(target.get("variable") or "") != PRIMARY_TARGET:
        raise SoilForecastingError("Phase 4.1 primary target must be swvl1.")
    horizons = tuple(int(item) for item in (target.get("horizons_days") or DEFAULT_HORIZONS))
    if horizons != DEFAULT_HORIZONS:
        raise SoilForecastingError("Phase 4.1 horizons must be 1, 3 and 7 days.")

    sets = payload.get("feature_sets") or {}
    for name in ("A", "B", "C"):
        block = sets.get(name) or {}
        columns = list(block.get("columns") or [])
        if not columns:
            raise SoilForecastingError(f"feature_sets.{name}.columns must be non-empty.")
        if any(str(col).startswith("target_") for col in columns):
            raise SoilForecastingError("Feature sets must not include target_ columns.")
    satellite = sets.get("D") or {}
    if satellite.get("enabled"):
        raise SoilForecastingError(
            "Feature set D (satellite) is disabled until acquisition timestamps are verified."
        )
    if payload.get("satellite_features_enabled"):
        raise SoilForecastingError("satellite_features_enabled must be false in Phase 4.1.")
    if (payload.get("missing_data") or {}).get("impute"):
        raise SoilForecastingError("Phase 4.1 uses complete-case rows; imputation is disabled.")
    if str((payload.get("splits") or {}).get("final_training_policy") or "") != "training_partition_only":
        raise SoilForecastingError("final_training_policy must be training_partition_only.")

    output = payload.get("output") or {}
    directory = str(output.get("directory") or f"data/processed/ml/experiments/{experiment_id}")
    config = dict(payload)
    config["experiment_id"] = experiment_id
    config["pipeline_version"] = str(payload.get("pipeline_version") or PIPELINE_VERSION)
    config["target"] = {**target, "horizons_days": list(horizons), "variable": PRIMARY_TARGET}
    config["output"] = {**output, "directory": directory}
    config["issue_time"] = {
        **(payload.get("issue_time") or {}),
        "research_mode": "research_reanalysis",
        "operational_availability_verified": False,
    }
    return config


def output_directory(config: dict[str, Any], *, root: Path | None = None) -> Path:
    base = root or project_root()
    return (base / str(config["output"]["directory"])).resolve()


def source_directory(config: dict[str, Any], *, root: Path | None = None) -> Path:
    base = root or project_root()
    return (base / str(config["source"]["directory"])).resolve()
