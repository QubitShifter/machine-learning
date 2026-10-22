"""Unique training-run identifiers, exclusive directories and manifests."""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

import yaml

from ml.agricultural_ml.pipeline import _git_reference
from ml.ingestion.manifest import validate_safe_id, write_json_atomic
from ml.preprocessing.errors import SoilForecastingError
from ml.preprocessing.raster import project_root
from ml.soil_forecasting.telemetry import SCHEMA_VERSION, TERMINAL_STATUSES, utc_z


RUN_ID_PATTERN = re.compile(r"^run_[0-9]{8}T[0-9]{6}Z_[0-9a-f]{6}$")
TELEMETRY_PIPELINE_LABEL = "4.1-telemetry"
FROZEN_PROTECTED_NAMES = frozenset({
    "frozen_experiment.json",
    "final_test_metrics.csv",
    "final_test_predictions.csv",
    "training_summary.json",
    "model_comparison.csv",
    "selected_validation_predictions.csv",
    "experiment_manifest.json",
    "data_fingerprint.json",
    "experiment_summary.json",
    "validation_metrics.csv",
    "validation_predictions.csv",
    "prepared_summary.json",
    "feature_selection.json",
    "joined_modeling_frame.csv",
    "experiment_config_snapshot.yaml",
    "error_analysis.json",
    "limitations.json",
    "test_evaluation_log.json",
})


def new_run_id(*, now: datetime | None = None, suffix: str | None = None) -> str:
    stamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    token = suffix or secrets.token_hex(3)
    if not re.fullmatch(r"[0-9a-f]{6}", token):
        raise SoilForecastingError("Run ID suffix must be 6 lowercase hex characters.")
    run_id = f"run_{stamp.strftime('%Y%m%dT%H%M%SZ')}_{token}"
    return validate_run_id(run_id)


def validate_run_id(run_id: str) -> str:
    value = str(run_id or "")
    validate_safe_id(value, "run_id")
    if not RUN_ID_PATTERN.fullmatch(value):
        raise SoilForecastingError("run_id must match run_YYYYMMDDTHHMMSSZ_<hex6>.")
    return value


def runs_root(experiment_dir: Path) -> Path:
    return Path(experiment_dir) / "runs"


def run_directory(experiment_dir: Path, run_id: str) -> Path:
    safe = validate_run_id(run_id)
    root = Path(experiment_dir).resolve()
    path = (root / "runs" / safe).resolve()
    if root not in path.parents:
        raise SoilForecastingError("Run directory escaped the experiment root.")
    return path


def create_run_directory(experiment_dir: Path, run_id: str | None = None) -> Path:
    identifier = run_id or new_run_id()
    path = run_directory(experiment_dir, identifier)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.mkdir(exist_ok=False)
    except FileExistsError as exc:
        raise SoilForecastingError(f"Run directory already exists: {identifier}") from exc
    (path / "model_artifacts").mkdir(exist_ok=True)
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_frozen_artifacts(experiment_dir: Path) -> dict[str, str]:
    root = Path(experiment_dir)
    snapshot: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative.startswith("runs/"):
            continue
        snapshot[relative] = sha256_file(path)
    return snapshot


def assert_frozen_unchanged(experiment_dir: Path, before: dict[str, str]) -> None:
    after = snapshot_frozen_artifacts(experiment_dir)
    if after != before:
        changed = sorted(set(before) ^ set(after) | {
            key for key in before if after.get(key) != before.get(key)
        })
        raise SoilForecastingError(
            "Frozen Phase 4.1 artifacts changed during a telemetry run: "
            + ", ".join(changed[:12])
        )


def environment_metadata(root: Path | None = None) -> dict[str, Any]:
    base = root or project_root()
    git = _git_reference(base)
    versions = {"python": sys.version.split()[0]}
    for name in ("scikit-learn", "numpy", "pandas", "joblib"):
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = "missing"
    return {
        "git_commit": git.get("commit"),
        "git_dirty": git.get("dirty"),
        "git_reference": git.get("git_reference"),
        "python_version": versions["python"],
        "scikit-learn": versions["scikit-learn"],
        "numpy": versions["numpy"],
        "pandas": versions["pandas"],
        "joblib": versions["joblib"],
        "platform_python_implementation": sys.implementation.name,
    }


def initial_manifest(
    *,
    run_id: str,
    experiment_id: str,
    algorithm: str,
    horizon_days: int,
    feature_set: str,
    target_variable: str,
    provenance_label: str,
    research_mode: str,
    execution_mode: str,
    hyperparameters: dict[str, Any],
    random_seed: int,
    environment: dict[str, Any],
    fingerprints: dict[str, Any],
    pipeline_version: str,
) -> dict[str, Any]:
    created = utc_z()
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "experiment_id": experiment_id,
        "pipeline_version": pipeline_version,
        "telemetry_pipeline": TELEMETRY_PIPELINE_LABEL,
        "created_at_utc": created,
        "start_at_utc": created,
        "finish_at_utc": None,
        "status": "created",
        "algorithm": algorithm,
        "model_id": algorithm,
        "target_variable": target_variable,
        "forecast_horizon_days": int(horizon_days),
        "feature_set": feature_set,
        "training_sample_count": None,
        "validation_sample_count": None,
        "selected_feature_count": None,
        "hyperparameters": hyperparameters,
        "random_seed": int(random_seed),
        "source_dataset_fingerprint": fingerprints.get("source_dataset_fingerprint"),
        "feature_schema_fingerprint": fingerprints.get("feature_schema_fingerprint"),
        "configuration_fingerprint": fingerprints.get("configuration_fingerprint"),
        "git_commit": environment.get("git_commit"),
        "git_dirty": environment.get("git_dirty"),
        "python_version": environment.get("python_version"),
        "scikit-learn": environment.get("scikit-learn"),
        "numpy": environment.get("numpy"),
        "research_mode": research_mode,
        "execution_mode": execution_mode,
        "provenance_label": provenance_label,
        "research_development": execution_mode == "research_development",
        "is_frozen_phase_4_1_model": False,
        "test_targets_accessed": False,
        "operational_forecast": False,
        "operational_availability_verified": False,
        "is_ground_truth": False,
        "is_measured_soil_moisture": False,
        "suitable_for_modeling": False,
        "artifacts": {},
        "error": None,
    }


def write_manifest(run_dir: Path, manifest: dict[str, Any]) -> None:
    write_json_atomic(Path(run_dir) / "run_manifest.json", manifest)


def read_manifest(run_dir: Path) -> dict[str, Any]:
    path = Path(run_dir) / "run_manifest.json"
    if not path.is_file():
        raise SoilForecastingError("run_manifest.json is missing.")
    import json
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SoilForecastingError("run_manifest.json must be an object.")
    return payload


def write_run_config(run_dir: Path, config: dict[str, Any]) -> None:
    path = Path(run_dir) / "run_config.yaml"
    temporary = path.with_name(".run_config.tmp.yaml")
    try:
        temporary.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def list_run_dirs(experiment_dir: Path) -> list[Path]:
    root = runs_root(experiment_dir)
    if not root.is_dir():
        return []
    dirs = []
    for path in sorted(root.iterdir()):
        try:
            validate_run_id(path.name)
        except (SoilForecastingError, ValueError):
            continue
        if path.is_symlink():
            continue
        if path.is_dir():
            dirs.append(path)
    return dirs


def lock_pid(run_dir: Path) -> int | None:
    lock = Path(run_dir) / ".event_writer.lock"
    if not lock.is_file():
        return None
    try:
        return int(lock.read_text(encoding="utf-8").strip() or "0")
    except ValueError:
        return None


def process_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def inferred_status(manifest: dict[str, Any], run_dir: Path) -> str:
    status = str(manifest.get("status") or "created")
    if status in TERMINAL_STATUSES:
        return status
    pid = lock_pid(run_dir)
    if pid is None or not process_is_running(pid):
        return "interrupted"
    return status


def fingerprint_columns(columns: list[str]) -> str:
    payload = "\n".join(columns)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
