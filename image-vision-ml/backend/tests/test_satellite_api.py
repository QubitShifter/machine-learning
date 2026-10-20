
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import satellite_service
from backend.tests.conftest import build_fixture_dataset
from ml.preprocessing.errors import InvalidImageIdError
from ml.preprocessing.raster import process_local_dataset


client = TestClient(app)


def _configure_roots(monkeypatch, tmp_path: Path) -> tuple[Path, Path]:
    raw_root = tmp_path / "raw"
    processed_root = tmp_path / "processed"
    monkeypatch.setattr(satellite_service, "RAW_ROOT", raw_root)
    monkeypatch.setattr(satellite_service, "PROCESSED_ROOT", processed_root)
    return raw_root, processed_root


def test_list_images(monkeypatch, tmp_path: Path):
    raw_root, _processed = _configure_roots(monkeypatch, tmp_path)
    build_fixture_dataset(raw_root / "fixture_scene")

    response = client.get("/api/v1/satellite/images")

    assert response.status_code == 200
    payload = response.json()
    assert payload["images"][0]["id"] == "fixture_scene"
    assert payload["images"][0]["scene_id"] == "TEST_SCENE_001"
    assert payload["images"][0]["acquisition_date"] == "2025-09-16"
    assert "B04" in payload["images"][0]["available_bands"]
    assert payload["images"][0]["processed"] is False


def test_retrieve_metadata(monkeypatch, tmp_path: Path):
    raw_root, _processed = _configure_roots(monkeypatch, tmp_path)
    build_fixture_dataset(raw_root / "fixture_scene")

    response = client.get("/api/v1/satellite/images/fixture_scene/metadata")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scene_id"] == "TEST_SCENE_001"
    assert payload["cloud_cover"] == 1.25
    assert payload["crs"] == "EPSG:32635"
    assert payload["width"] == 6
    assert payload["height"] == 4
    assert payload["pixel_resolution"] == [10.0, 10.0]
    assert payload["processed"] is False


def test_process_and_retrieve_outputs(monkeypatch, tmp_path: Path):
    raw_root, processed_root = _configure_roots(monkeypatch, tmp_path)
    build_fixture_dataset(raw_root / "fixture_scene")

    process = client.post("/api/v1/satellite/images/fixture_scene/process")
    assert process.status_code == 200
    body = process.json()
    assert body["status"] == "processed"
    assert "ndvi_corrected.tif" in body["outputs"]
    assert "rgb_preview.png" in body["outputs"]
    assert body["valid_pixels"] > 0
    assert body["ndvi"]["mean"] is not None
    assert (processed_root / "fixture_scene" / "processing_metadata.json").is_file()

    repeated = client.post("/api/v1/satellite/images/fixture_scene/process")
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "already_processed"

    stats = client.get("/api/v1/satellite/images/fixture_scene/ndvi/stats")
    assert stats.status_code == 200
    assert stats.json()["image_id"] == "fixture_scene"
    assert stats.json()["valid_pixels"] == body["valid_pixels"]
    assert stats.json()["ndvi"]["minimum"] is not None

    rgb = client.get("/api/v1/satellite/images/fixture_scene/rgb")
    assert rgb.status_code == 200
    assert rgb.headers["content-type"].startswith("image/png")
    assert rgb.content[:8] == b"\x89PNG\r\n\x1a\n"

    preview = client.get("/api/v1/satellite/images/fixture_scene/ndvi/preview")
    assert preview.status_code == 200
    assert preview.headers["content-type"].startswith("image/png")
    assert preview.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_process_respects_rgb_option(monkeypatch, tmp_path: Path):
    raw_root, processed_root = _configure_roots(monkeypatch, tmp_path)
    build_fixture_dataset(raw_root / "fixture_scene")

    response = client.post(
        "/api/v1/satellite/images/fixture_scene/process",
        json={
            "generate_rgb": False,
            "generate_ndvi": True,
            "apply_scl_mask": True,
            "valid_scl_classes": [4, 5],
        },
    )

    assert response.status_code == 200
    assert "rgb_preview.png" not in response.json()["outputs"]
    assert not (processed_root / "fixture_scene" / "rgb_preview.png").exists()
    assert client.get("/api/v1/satellite/images/fixture_scene/rgb").status_code == 404


def test_unknown_image_id(monkeypatch, tmp_path: Path):
    _configure_roots(monkeypatch, tmp_path)

    assert client.get("/api/v1/satellite/images/missing").status_code == 404
    assert client.post("/api/v1/satellite/images/missing/process").status_code == 404


def test_path_traversal_is_rejected(monkeypatch, tmp_path: Path):
    _configure_roots(monkeypatch, tmp_path)

    for image_id in ("../secret", "..", "foo/bar", "foo\\bar", "first_image/../x"):
        response = client.get(f"/api/v1/satellite/images/{image_id}/metadata")
        assert response.status_code in {400, 404, 422}


def test_validate_image_id_rejects_traversal():
    try:
        satellite_service.validate_image_id("../first_image")
    except InvalidImageIdError:
        pass
    else:
        raise AssertionError("Expected InvalidImageIdError")


def test_missing_processed_output(monkeypatch, tmp_path: Path):
    raw_root, _processed = _configure_roots(monkeypatch, tmp_path)
    build_fixture_dataset(raw_root / "fixture_scene")

    assert client.get("/api/v1/satellite/images/fixture_scene/rgb").status_code == 404
    assert client.get("/api/v1/satellite/images/fixture_scene/ndvi/preview").status_code == 404
    assert client.get("/api/v1/satellite/images/fixture_scene/ndvi/stats").status_code == 404


def test_health_and_swagger_remain_available():
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    docs = client.get("/api")
    assert docs.status_code == 200

    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    paths = openapi.json()["paths"]
    assert "/api/v1/satellite/images" in paths
    assert "/api/v1/satellite/images/{image_id}/process" in paths
    assert "/docs" not in paths


def test_direct_process_does_not_touch_unrelated_raw_files(tmp_path: Path):
    raw_dir = build_fixture_dataset(tmp_path / "raw" / "fixture_scene")
    original = (raw_dir / "red_B04.tif").read_bytes()

    process_local_dataset(raw_dir, tmp_path / "processed" / "fixture_scene")

    assert (raw_dir / "red_B04.tif").read_bytes() == original
