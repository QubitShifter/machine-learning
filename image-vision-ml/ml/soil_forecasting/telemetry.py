"""Training-run event schema, JSONL writer, lifecycle and log validation.

Research instrumentation only. Does not train models or stream live events.
"""

from __future__ import annotations

import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ml.ingestion.manifest import write_json_atomic
from ml.preprocessing.errors import SoilForecastingError


SCHEMA_VERSION = "1.0"

EVENT_TYPES = frozenset({
    "run_created",
    "dataset_validation_started",
    "dataset_validation_completed",
    "features_prepared",
    "split_verified",
    "preprocessing_started",
    "preprocessing_completed",
    "training_started",
    "training_iteration",
    "training_metric",
    "training_completed",
    "validation_started",
    "validation_completed",
    "artifact_saved",
    "run_completed",
    "run_failed",
    "warning",
    "training_early_stopped",
    "convergence_diagnostic",
    "training_cancelled",
})

PHASES = frozenset({
    "created",
    "dataset",
    "features",
    "split",
    "preprocessing",
    "fit",
    "validation",
    "saving",
    "completed",
    "failed",
})

STATUSES = frozenset({
    "created",
    "preparing",
    "training",
    "validating",
    "saving",
    "completed",
    "failed",
    "interrupted",
})

TRANSITIONS: dict[str, frozenset[str]] = {
    "created": frozenset({"preparing", "failed", "interrupted"}),
    "preparing": frozenset({"training", "failed", "interrupted"}),
    "training": frozenset({"validating", "saving", "failed", "interrupted"}),
    "validating": frozenset({"saving", "failed", "interrupted"}),
    "saving": frozenset({"completed", "failed", "interrupted"}),
    "completed": frozenset(),
    "failed": frozenset(),
    "interrupted": frozenset(),
}

TERMINAL_STATUSES = frozenset({"completed", "failed", "interrupted"})

SECRET_KEY_MARKERS = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "private_key",
    "access_key",
)

METRIC_PARTITIONS = frozenset({"train", "training", "validation", "internal", None})


def utc_z(stamp: datetime | None = None) -> str:
    current = stamp or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise SoilForecastingError("Telemetry timestamps must be timezone-aware UTC.")
    return current.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc(value: str) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise SoilForecastingError("timestamp_utc is required.")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise SoilForecastingError("timestamp_utc must include a UTC offset.")
    return parsed.astimezone(timezone.utc)


def assert_transition(current: str, nxt: str) -> None:
    if current not in STATUSES:
        raise SoilForecastingError(f"Unknown run status {current}.")
    if nxt not in STATUSES:
        raise SoilForecastingError(f"Unknown run status {nxt}.")
    if nxt not in TRANSITIONS[current]:
        raise SoilForecastingError(f"Invalid run status transition {current} -> {nxt}.")


def _reject_secrets(payload: dict[str, Any], *, prefix: str = "") -> None:
    for key, value in payload.items():
        lowered = str(key).lower()
        path = f"{prefix}.{key}" if prefix else str(key)
        if any(marker in lowered for marker in SECRET_KEY_MARKERS):
            raise SoilForecastingError(f"Refusing to record secret-bearing field {path}.")
        if isinstance(value, dict):
            _reject_secrets(value, prefix=path)


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise SoilForecastingError("Metric and numeric event fields must be finite.")
        return value
    if isinstance(value, Path):
        return value.name
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "item") and callable(value.item):
        return _jsonable(value.item())
    return value


def validate_event(event: dict[str, Any], *, run_id: str | None = None) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise SoilForecastingError("Each training event must be a JSON object.")
    _reject_secrets(event)
    schema = str(event.get("schema_version") or "")
    if schema != SCHEMA_VERSION:
        raise SoilForecastingError(f"Unsupported event schema_version {schema}.")
    event_run = str(event.get("run_id") or "")
    if not event_run:
        raise SoilForecastingError("Event run_id is required.")
    if run_id is not None and event_run != run_id:
        raise SoilForecastingError("Event run_id does not match the writer run.")
    sequence = event.get("sequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise SoilForecastingError("Event sequence must be a positive integer.")
    parse_utc(str(event.get("timestamp_utc") or ""))
    elapsed = event.get("elapsed_ms")
    if not isinstance(elapsed, int) or isinstance(elapsed, bool) or elapsed < 0:
        raise SoilForecastingError("elapsed_ms must be a non-negative integer from a monotonic clock.")
    event_type = str(event.get("event_type") or "")
    if event_type not in EVENT_TYPES:
        raise SoilForecastingError(f"Unsupported event_type {event_type}.")
    phase = str(event.get("phase") or "")
    if phase not in PHASES:
        raise SoilForecastingError(f"Unsupported event phase {phase}.")
    if "iteration" in event and event["iteration"] is not None:
        iteration = event["iteration"]
        if not isinstance(iteration, int) or isinstance(iteration, bool) or iteration < 1:
            raise SoilForecastingError("iteration must be a positive integer when present.")
    if event.get("metric_value") is not None:
        try:
            metric_value = float(event["metric_value"])
        except (TypeError, ValueError) as exc:
            raise SoilForecastingError("metric_value must be numeric when present.") from exc
        if not math.isfinite(metric_value):
            raise SoilForecastingError("metric_value must be finite.")
        event = {**event, "metric_value": metric_value}
        if not event.get("metric_name"):
            raise SoilForecastingError("metric_name is required when metric_value is set.")
        if not event.get("metric_unit"):
            raise SoilForecastingError("metric_unit is required when metric_value is set.")
    partition = event.get("dataset_partition")
    if partition not in METRIC_PARTITIONS:
        raise SoilForecastingError(f"Unsupported dataset_partition {partition}.")
    horizon = event.get("horizon_days")
    if horizon is not None:
        if not isinstance(horizon, int) or isinstance(horizon, bool) or horizon < 1:
            raise SoilForecastingError("horizon_days must be a positive integer when present.")
    return event


def read_jsonl_events(path: Path, *, run_id: str | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Parse a JSONL event log. An incomplete final line is skipped, not fabricated."""
    info = {
        "path": path.name,
        "truncated_final_line": False,
        "skipped_incomplete_lines": 0,
        "parse_errors": 0,
    }
    if not path.is_file():
        return [], info
    events: list[dict[str, Any]] = []
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(raw_lines):
        text = line.strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            is_last = index == len(raw_lines) - 1
            if is_last:
                info["truncated_final_line"] = True
                info["skipped_incomplete_lines"] += 1
                continue
            info["parse_errors"] += 1
            continue
        if not isinstance(payload, dict):
            info["parse_errors"] += 1
            continue
        try:
            events.append(validate_event(payload, run_id=run_id))
        except SoilForecastingError:
            info["parse_errors"] += 1
    return events, info


def validate_event_log(
    events: list[dict[str, Any]],
    *,
    run_id: str,
    expected_model: str | None = None,
    expected_horizon: int | None = None,
    read_info: dict[str, Any] | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    last_sequence = 0
    last_elapsed = -1
    last_timestamp: datetime | None = None
    types: list[str] = []
    for event in events:
        try:
            validate_event(event, run_id=run_id)
        except SoilForecastingError as exc:
            errors.append(str(exc))
            continue
        sequence = int(event["sequence"])
        if sequence <= last_sequence:
            errors.append(f"Sequence {sequence} is not strictly increasing.")
        last_sequence = sequence
        elapsed = int(event["elapsed_ms"])
        if elapsed < last_elapsed:
            errors.append(f"elapsed_ms decreased at sequence {sequence}.")
        last_elapsed = elapsed
        stamp = parse_utc(str(event["timestamp_utc"]))
        if last_timestamp is not None and stamp < last_timestamp:
            warnings.append(f"Wall-clock timestamp moved backwards at sequence {sequence}.")
        last_timestamp = stamp
        types.append(str(event["event_type"]))
        if expected_model and event.get("model") not in {None, expected_model}:
            errors.append(f"Event sequence {sequence} has model {event.get('model')} instead of {expected_model}.")
        if expected_horizon is not None and event.get("horizon_days") not in {None, expected_horizon}:
            errors.append(
                f"Event sequence {sequence} has horizon {event.get('horizon_days')} instead of {expected_horizon}."
            )
        if event.get("event_type") == "training_iteration" and event.get("iteration") is None:
            errors.append(f"training_iteration at sequence {sequence} is missing iteration.")
    if status == "completed":
        if "run_completed" not in types:
            errors.append("Completed runs must include a run_completed event.")
        if "run_created" not in types:
            errors.append("Completed runs must include a run_created event.")
        if "run_failed" in types:
            errors.append("A completed run must not include run_failed.")
    if status == "failed" and "run_failed" not in types:
        errors.append("Failed runs must include a run_failed event.")
    if read_info and read_info.get("truncated_final_line") and status == "completed":
        errors.append("Completed event logs must not end with a truncated JSON line.")
    if read_info and read_info.get("parse_errors"):
        errors.append(f"Event log has {read_info['parse_errors']} unreadable lines.")
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "ok": not errors,
        "event_count": len(events),
        "errors": errors,
        "warnings": warnings,
        "event_types": types,
        "truncated_final_line": bool((read_info or {}).get("truncated_final_line")),
        "parse_errors": int((read_info or {}).get("parse_errors") or 0),
        "max_sequence": last_sequence,
        "max_elapsed_ms": last_elapsed if last_elapsed >= 0 else None,
    }


class EventWriter:
    """Single-owner append-only JSONL writer for one training run."""

    def __init__(self, run_dir: Path, run_id: str):
        self.run_dir = Path(run_dir)
        self.run_id = run_id
        self.path = self.run_dir / "training_events.jsonl"
        self._lock_path = self.run_dir / ".event_writer.lock"
        self._sequence = 0
        self._last_elapsed = 0
        self._closed = False
        self._immutable = False
        self._origin = time.monotonic()
        self._handle = None
        self._lock_fd: int | None = None
        self._acquire()
        existing, _info = read_jsonl_events(self.path, run_id=run_id)
        if existing:
            self._sequence = int(existing[-1]["sequence"])
            self._last_elapsed = int(existing[-1]["elapsed_ms"])
        self._handle = self.path.open("a", encoding="utf-8")

    def _acquire(self) -> None:
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        try:
            self._lock_fd = os.open(str(self._lock_path), flags)
        except FileExistsError as exc:
            raise SoilForecastingError(
                f"Run {self.run_id} already has an active event writer."
            ) from exc
        os.write(self._lock_fd, str(os.getpid()).encode("ascii"))
        os.fsync(self._lock_fd)

    def elapsed_ms(self) -> int:
        elapsed = int((time.monotonic() - self._origin) * 1000)
        if elapsed < self._last_elapsed:
            elapsed = self._last_elapsed
        return elapsed

    def emit(
        self,
        *,
        event_type: str,
        phase: str,
        model: str | None = None,
        horizon_days: int | None = None,
        iteration: int | None = None,
        metric_name: str | None = None,
        metric_value: float | None = None,
        metric_unit: str | None = None,
        dataset_partition: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self._closed:
            raise SoilForecastingError("Event writer is closed.")
        if self._immutable:
            raise SoilForecastingError("Completed runs are immutable.")
        self._sequence += 1
        elapsed = self.elapsed_ms()
        event = {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "sequence": self._sequence,
            "timestamp_utc": utc_z(),
            "elapsed_ms": elapsed,
            "event_type": event_type,
            "phase": phase,
            "model": model,
            "horizon_days": horizon_days,
            "iteration": iteration,
            "metric_name": metric_name,
            "metric_value": metric_value,
            "metric_unit": metric_unit,
            "dataset_partition": dataset_partition,
            "details": _jsonable(details or {}),
        }
        event = validate_event(_jsonable(event), run_id=self.run_id)
        line = json.dumps(event, separators=(",", ":"), ensure_ascii=True)
        if "\n" in line:
            raise SoilForecastingError("Event JSON must occupy a single line.")
        assert self._handle is not None
        self._handle.write(line + "\n")
        self._handle.flush()
        os.fsync(self._handle.fileno())
        self._last_elapsed = elapsed
        return event

    def mark_immutable(self) -> None:
        self._immutable = True

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._handle is not None:
            try:
                self._handle.flush()
                os.fsync(self._handle.fileno())
            finally:
                self._handle.close()
                self._handle = None
        if self._lock_fd is not None:
            os.close(self._lock_fd)
            self._lock_fd = None
        if self._lock_path.is_file() and self._immutable:
            self._lock_path.unlink()

    def __enter__(self) -> "EventWriter":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def write_validation_report(path: Path, report: dict[str, Any]) -> None:
    write_json_atomic(path, report)
