from pathlib import Path

from ml.ingestion.config import validate_dataset_config
from ml.ingestion.manifest import (
    empty_manifest,
    read_manifest,
    save_manifest,
    upsert_scene,
)


def _config():
    return validate_dataset_config({
        "dataset_id": "plovdiv_2025",
        "source": {"collection": "sentinel-2-l2a"},
        "area": {"bbox": [24.65, 42.05, 24.68, 42.08]},
        "period": {"start": "2025-01-01", "end": "2025-12-31"},
    })


def test_manifest_create_read_and_status_update(tmp_path: Path):
    path = tmp_path / "manifest.json"
    manifest = empty_manifest(_config())
    upsert_scene(manifest, "S2B_35TLG_20250916_1_L2A", status="discovered")
    save_manifest(path, manifest)
    loaded = read_manifest(path)
    assert loaded["dataset_id"] == "plovdiv_2025"
    assert loaded["scenes"]["S2B_35TLG_20250916_1_L2A"]["status"] == "discovered"
    upsert_scene(loaded, "S2B_35TLG_20250916_1_L2A", status="downloaded")
    save_manifest(path, loaded)
    assert read_manifest(path)["scenes"]["S2B_35TLG_20250916_1_L2A"]["status"] == "downloaded"


def test_corrupted_manifest_is_an_error(tmp_path: Path):
    path = tmp_path / "manifest.json"
    path.write_text("{not-json", encoding="utf-8")
    try:
        read_manifest(path)
    except ValueError:
        return
    raise AssertionError("Expected ValueError")


def test_invalid_dataset_identifier():
    try:
        validate_dataset_config({
            "dataset_id": "../secret",
            "source": {"collection": "sentinel-2-l2a"},
            "area": {"bbox": [24.65, 42.05, 24.68, 42.08]},
            "period": {"start": "2025-01-01", "end": "2025-12-31"},
        })
    except Exception:
        return
    raise AssertionError("Expected invalid identifier to fail")


def test_rerunning_completed_status_keeps_scene(tmp_path: Path):
    path = tmp_path / "manifest.json"
    manifest = empty_manifest(_config())
    upsert_scene(manifest, "S2B_35TLG_20250916_1_L2A", status="downloaded")
    save_manifest(path, manifest)
    loaded = read_manifest(path)
    upsert_scene(loaded, "S2B_35TLG_20250916_1_L2A", retries=0)
    save_manifest(path, loaded)
    assert read_manifest(path)["scenes"]["S2B_35TLG_20250916_1_L2A"]["status"] == "downloaded"
