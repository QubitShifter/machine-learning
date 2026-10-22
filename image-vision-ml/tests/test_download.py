from pathlib import Path

from backend.tests.conftest import write_geotiff
import numpy as np
from rasterio.transform import Affine

from ml.ingestion.download import _cleanup_partial, _scene_complete, estimate_download
from ml.preprocessing.raster import BAND_FILES


def test_download_estimate():
    estimate = estimate_download([{"scene_id": "a"}, {"scene_id": "b"}], 1000)
    assert estimate["scenes"] == 2
    assert estimate["estimated_bytes"] > 0


def test_incomplete_scene_is_not_complete(tmp_path: Path):
    scene_dir = tmp_path / "scene"
    scene_dir.mkdir()
    record = {"status": "downloaded", "checksums": {}}
    assert _scene_complete(scene_dir, record) is False


def test_partial_download_cleanup(tmp_path: Path):
    scene_dir = tmp_path / "scene"
    scene_dir.mkdir()
    (scene_dir / "red_B04.tif").write_bytes(b"partial")
    _cleanup_partial(scene_dir)
    assert not scene_dir.exists()


def test_candidates_cli_is_local_dry_run(monkeypatch):
    captured: dict = {}

    def fake_preview(config, *, refresh_stac=False, limit=12):
        captured["refresh_stac"] = refresh_stac
        captured["limit"] = limit
        captured["config"] = str(config)
        return {"dry_run": True, "candidates": [], "refresh_stac": refresh_stac}

    monkeypatch.setattr("scripts.satellite_dataset.preview_dataset_candidates", fake_preview)
    from scripts.satellite_dataset import main

    code = main([
        "candidates",
        "--config",
        "configs/satellite_multiyear.yaml",
        "--limit",
        "8",
    ])
    assert code == 0
    assert captured["refresh_stac"] is False
    assert captured["limit"] == 8


def test_download_cli_forwards_scene_ids(monkeypatch):
    captured: dict = {}

    def fake_download(config, *, limit=None, dry_run=False, scene_ids=None):
        captured["scene_ids"] = scene_ids
        captured["dry_run"] = dry_run
        captured["limit"] = limit
        return {"status": "dry_run", "selected": scene_ids or []}

    monkeypatch.setattr("scripts.satellite_dataset.download_dataset", fake_download)
    from scripts.satellite_dataset import main

    code = main([
        "download",
        "--config",
        "configs/satellite_multiyear.yaml",
        "--scene-id",
        "S2B_35TLG_20230609_0_L2A",
        "--scene-id",
        "S2A_35TLG_20230912_1_L2A",
        "--dry-run",
    ])
    assert code == 0
    assert captured["dry_run"] is True
    assert captured["scene_ids"] == [
        "S2B_35TLG_20230609_0_L2A",
        "S2A_35TLG_20230912_1_L2A",
    ]


def test_verified_scene_is_complete(tmp_path: Path):
    scene_dir = tmp_path / "scene"
    for filename in BAND_FILES.values():
        write_geotiff(
            scene_dir / filename,
            np.ones((2, 2), dtype=np.uint16),
            transform=Affine(10, 0, 0, 0, -10, 0),
        )
    (scene_dir / "metadata.json").write_text("{}", encoding="utf-8")
    record = {"status": "downloaded", "checksums": {}}
    assert _scene_complete(scene_dir, record) is True
