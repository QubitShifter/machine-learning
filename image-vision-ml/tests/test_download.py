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
