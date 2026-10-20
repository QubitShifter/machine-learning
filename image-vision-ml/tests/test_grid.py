from pathlib import Path

from ml.ingestion.manifest import save_manifest
from ml.preprocessing.grid import (
    build_target_grid,
    grids_equivalent,
    serialize_grid,
    validate_dataset_grid,
)


def test_canonical_grid_is_stable():
    first = build_target_grid((24.65, 42.05, 24.68, 42.08))
    second = build_target_grid((24.65, 42.05, 24.68, 42.08))
    assert first["width"] == second["width"]
    assert first["height"] == second["height"]
    assert first["crs"] == second["crs"]
    assert grids_equivalent(first, second)
    serialized = serialize_grid(first)
    assert serialized["grid_version"] == "1"
    assert serialized["width"] == first["width"]
    assert serialized["height"] == first["height"]


def test_validate_dataset_grid_reports_mismatch(tmp_path: Path):
    dataset = tmp_path / "demo"
    save_manifest(dataset / "manifest.json", {
        "dataset_id": "demo",
        "target_grid": {
            "crs": "EPSG:32635",
            "transform": [10, 0, 0, 0, -10, 0],
            "width": 10,
            "height": 10,
        },
        "scenes": {
            "scene_a": {"scene_id": "scene_a", "status": "processed"},
        },
    })
    scene_dir = dataset / "scenes" / "scene_a"
    scene_dir.mkdir(parents=True)
    (scene_dir / "processing_metadata.json").write_text(
        '{"raster": {"crs": "EPSG:32635", "transform": [20, 0, 0, 0, -20, 0], "width": 5, "height": 5}}',
        encoding="utf-8",
    )
    report = validate_dataset_grid("demo", processed_root=tmp_path)
    assert report["consistent"] is False
    assert report["mismatches"][0]["scene_id"] == "scene_a"
