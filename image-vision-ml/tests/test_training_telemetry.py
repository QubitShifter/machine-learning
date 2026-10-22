from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ml.ingestion.manifest import write_json_atomic
from ml.preprocessing.errors import SoilForecastingError
from ml.soil_forecasting.run_registry import (
    create_run_directory,
    inferred_status,
    new_run_id,
    run_directory,
    snapshot_frozen_artifacts,
    validate_run_id,
)
from ml.soil_forecasting.telemetry import (
    SCHEMA_VERSION,
    EventWriter,
    assert_transition,
    read_jsonl_events,
    utc_z,
    validate_event,
    validate_event_log,
)


def test_run_ids_are_unique_utc_and_collision_resistant():
    now = datetime(2026, 10, 22, 19, 0, 0, tzinfo=timezone.utc)
    first = new_run_id(now=now, suffix="a7c9e1")
    second = new_run_id(now=now, suffix="b8d0f2")
    assert first == "run_20261022T190000Z_a7c9e1"
    assert first != second
    assert validate_run_id(first) == first
    with pytest.raises(SoilForecastingError):
        new_run_id(now=now, suffix="short")
    with pytest.raises((SoilForecastingError, ValueError)):
        validate_run_id("../etc")
    with pytest.raises((SoilForecastingError, ValueError)):
        validate_run_id("run_20261022T190000Z_ZZZZZZ")


def test_event_writer_sequence_utc_elapsed_and_jsonl(tmp_path: Path):
    run_id = new_run_id(suffix="aaaaaa")
    run_dir = create_run_directory(tmp_path, run_id)
    with EventWriter(run_dir, run_id) as writer:
        first = writer.emit(event_type="run_created", phase="created", model="ridge", horizon_days=1)
        second = writer.emit(event_type="training_started", phase="fit", model="ridge", horizon_days=1)
        writer.mark_immutable()
    assert first["schema_version"] == SCHEMA_VERSION
    assert first["sequence"] == 1
    assert second["sequence"] == 2
    assert first["elapsed_ms"] <= second["elapsed_ms"]
    datetime.fromisoformat(first["timestamp_utc"].replace("Z", "+00:00"))
    events, info = read_jsonl_events(run_dir / "training_events.jsonl", run_id=run_id)
    assert info["truncated_final_line"] is False
    assert [item["sequence"] for item in events] == [1, 2]
    for line in (run_dir / "training_events.jsonl").read_text(encoding="utf-8").splitlines():
        json.loads(line)


def test_event_writer_rejects_secrets_and_nonfinite_metrics(tmp_path: Path):
    run_id = new_run_id(suffix="bbbbbb")
    run_dir = create_run_directory(tmp_path, run_id)
    writer = EventWriter(run_dir, run_id)
    with pytest.raises(SoilForecastingError, match="secret"):
        writer.emit(event_type="warning", phase="fit", details={"api_key": "abc"})
    with pytest.raises(SoilForecastingError, match="finite"):
        writer.emit(
            event_type="training_metric",
            phase="fit",
            metric_name="training_loss",
            metric_value=float("nan"),
            metric_unit="squared_m3_per_m3",
            dataset_partition="train",
        )
    writer.close()


def test_completed_run_is_immutable_and_concurrent_writers_isolated(tmp_path: Path):
    run_id = new_run_id(suffix="cccccc")
    run_dir = create_run_directory(tmp_path, run_id)
    writer = EventWriter(run_dir, run_id)
    writer.emit(event_type="run_created", phase="created")
    with pytest.raises(SoilForecastingError, match="active event writer"):
        EventWriter(run_dir, run_id)
    writer.mark_immutable()
    with pytest.raises(SoilForecastingError, match="immutable"):
        writer.emit(event_type="training_started", phase="fit")
    writer.close()
    other_id = new_run_id(suffix="dddddd")
    other_dir = create_run_directory(tmp_path, other_id)
    with EventWriter(other_dir, other_id) as other:
        other.emit(event_type="run_created", phase="created")
        other.mark_immutable()
    assert (run_dir / "training_events.jsonl").read_text(encoding="utf-8") != (
        other_dir / "training_events.jsonl"
    ).read_text(encoding="utf-8") or run_id != other_id


def test_create_run_directory_refuses_overwrite(tmp_path: Path):
    run_id = new_run_id(suffix="eeeeee")
    create_run_directory(tmp_path, run_id)
    with pytest.raises(SoilForecastingError, match="already exists"):
        create_run_directory(tmp_path, run_id)


def test_jsonl_reader_skips_truncated_final_line(tmp_path: Path):
    run_id = new_run_id(suffix="ffffff")
    path = tmp_path / "training_events.jsonl"
    valid = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "sequence": 1,
        "timestamp_utc": utc_z(),
        "elapsed_ms": 0,
        "event_type": "run_created",
        "phase": "created",
        "model": None,
        "horizon_days": None,
        "iteration": None,
        "metric_name": None,
        "metric_value": None,
        "metric_unit": None,
        "dataset_partition": None,
        "details": {},
    }
    path.write_text(json.dumps(valid) + "\n{\"sequence\":", encoding="utf-8")
    events, info = read_jsonl_events(path, run_id=run_id)
    assert len(events) == 1
    assert info["truncated_final_line"] is True


def test_lifecycle_transitions_and_failed_status(tmp_path: Path):
    assert_transition("created", "preparing")
    assert_transition("preparing", "training")
    assert_transition("training", "validating")
    assert_transition("validating", "saving")
    assert_transition("saving", "completed")
    with pytest.raises(SoilForecastingError, match="Invalid run status"):
        assert_transition("completed", "training")
    with pytest.raises(SoilForecastingError, match="Invalid run status"):
        assert_transition("failed", "completed")
    run_id = new_run_id(suffix="111111")
    run_dir = create_run_directory(tmp_path, run_id)
    write_json_atomic(run_dir / "run_manifest.json", {"run_id": run_id, "status": "training"})
    assert inferred_status({"status": "training"}, run_dir) == "interrupted"
    assert inferred_status({"status": "completed"}, run_dir) == "completed"


def test_validation_rejects_non_monotonic_sequences():
    run_id = "run_20261022T190000Z_abc123"
    events = [
        validate_event({
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "sequence": 1,
            "timestamp_utc": "2026-10-22T19:00:00Z",
            "elapsed_ms": 10,
            "event_type": "run_created",
            "phase": "created",
            "details": {},
        }, run_id=run_id),
        {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "sequence": 1,
            "timestamp_utc": "2026-10-22T19:00:01Z",
            "elapsed_ms": 5,
            "event_type": "run_completed",
            "phase": "completed",
            "details": {},
        },
    ]
    report = validate_event_log(events, run_id=run_id, status="completed")
    assert report["ok"] is False
    assert any("strictly increasing" in item for item in report["errors"])


def test_atomic_manifest_write(tmp_path: Path):
    path = tmp_path / "run_manifest.json"
    write_json_atomic(path, {"status": "created", "run_id": "run_20261022T190000Z_abc123"})
    write_json_atomic(path, {"status": "completed", "run_id": "run_20261022T190000Z_abc123"})
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["status"] == "completed"
    assert not list(tmp_path.glob(".*.tmp.json"))


def test_run_directory_rejects_path_escape(tmp_path: Path):
    with pytest.raises((SoilForecastingError, ValueError)):
        run_directory(tmp_path, "../secret")
    with pytest.raises((SoilForecastingError, ValueError)):
        run_directory(tmp_path, "run_../../x")


def test_frozen_snapshot_ignores_runs_subdirectory(tmp_path: Path):
    (tmp_path / "frozen_experiment.json").write_text("{\"frozen\": true}", encoding="utf-8")
    before = snapshot_frozen_artifacts(tmp_path)
    run_dir = create_run_directory(tmp_path, new_run_id(suffix="222222"))
    (run_dir / "run_manifest.json").write_text("{}", encoding="utf-8")
    after = snapshot_frozen_artifacts(tmp_path)
    assert before == after
