from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.transform import Affine
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import satellite_map, satellite_service
from backend.tests.conftest import write_geotiff
from ml.ingestion.manifest import save_manifest, upsert_scene
from ml.preprocessing.errors import MissingProcessedOutputError
from ml.visualization.map_overlay import (
    colorize_ndvi,
    geographic_extent,
    inspect_overlay_sources,
    maplibre_coordinates,
    plan_destination_grid,
    render_overlay_png,
    sample_ndvi,
)
from ml.preprocessing.raster import read_raster_metadata


client = TestClient(app)

TRANSFORM = Affine(10.0, 0.0, 305520.0, 0.0, -10.0, 4661340.0)
ROTATED = Affine(10.0, 2.0, 305520.0, 1.0, -10.0, 4661340.0)


def _configure(monkeypatch, tmp_path: Path) -> tuple[Path, Path, Path]:
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    cache = tmp_path / "cache"
    monkeypatch.setattr(satellite_service, "RAW_ROOT", raw)
    monkeypatch.setattr(satellite_service, "PROCESSED_ROOT", processed)
    monkeypatch.setattr(satellite_map, "CACHE_ROOT", cache)
    return raw, processed, cache


def _seed_overlay_scene(
    raw: Path,
    processed: Path,
    *,
    scene_id: str = "S2A_35TLG_20250718_1_L2A",
    dataset_id: str = "plovdiv_2023_2025",
    ndvi_fill: float = 0.5,
    red_dn: int = 4000,
    include_rasters: bool = True,
    rotated: bool = False,
    valid_black: bool = False,
) -> Path:
    raw_dataset = raw / dataset_id
    raw_dataset.mkdir(parents=True, exist_ok=True)
    manifest = {
        "dataset_id": dataset_id,
        "bbox": [24.65, 42.05, 24.68, 42.08],
        "period": {"start": "2023-01-01", "end": "2025-12-31"},
        "source": {"collection": "sentinel-2-l2a"},
        "scenes": {},
    }
    upsert_scene(
        manifest,
        scene_id,
        status="processed",
        acquisition_date="2025-07-18",
        platform="sentinel-2a",
        cloud_cover=5.8,
    )
    upsert_scene(
        manifest,
        "S2A_35TLG_CATALOGONLY_1_L2A",
        status="discovered",
        acquisition_date="2025-12-30",
        platform="sentinel-2a",
    )
    save_manifest(raw_dataset / "manifest.json", manifest)

    scene_raw = raw_dataset / "scenes" / scene_id
    scene_proc = processed / dataset_id / "scenes" / scene_id
    scene_proc.mkdir(parents=True, exist_ok=True)
    if not include_rasters:
        return scene_proc

    transform = ROTATED if rotated else TRANSFORM
    height, width = 8, 10
    ndvi = np.full((height, width), ndvi_fill, dtype=np.float32)
    mask = np.ones((height, width), dtype=np.uint8)
    ndvi[0, 0] = np.nan
    mask[0, 0] = 0
    ndvi[1, 1] = 0.8
    write_geotiff(scene_proc / "ndvi.tif", ndvi, transform=transform, nodata=np.nan)
    write_geotiff(scene_proc / "valid_mask.tif", mask, transform=transform, nodata=0)
    (scene_proc / "processing_metadata.json").write_text(
        '{"calibration":{"B02":{"scale":0.0001,"offset":0.0,"nodata":0.0},'
        '"B03":{"scale":0.0001,"offset":0.0,"nodata":0.0},'
        '"B04":{"scale":0.0001,"offset":0.0,"nodata":0.0}}}',
        encoding="utf-8",
    )

    red = np.full((height, width), red_dn, dtype=np.uint16)
    green = np.full((height, width), 2000, dtype=np.uint16)
    blue = np.full((height, width), 1000, dtype=np.uint16)
    if valid_black:
        red[2, 2] = 0
        green[2, 2] = 0
        blue[2, 2] = 0
    scene_raw.mkdir(parents=True, exist_ok=True)
    for name, array in (
        ("red_B04.tif", red),
        ("green_B03.tif", green),
        ("blue_B02.tif", blue),
    ):
        write_geotiff(scene_raw / name, array, transform=transform, nodata=0)
    return scene_proc


def test_color_scale_is_fixed_across_scenes():
    first = colorize_ndvi(np.array([[0.5]], dtype=np.float32))
    second = colorize_ndvi(np.array([[0.5, 0.9]], dtype=np.float32))
    assert list(first[0, 0]) == list(second[0, 0])
    assert list(first[0, 0]) == [116, 196, 118]


def test_reproject_extent_and_transparency(tmp_path: Path):
    processed = _seed_overlay_scene(tmp_path / "raw", tmp_path / "processed")
    raw_dir = tmp_path / "raw" / "plovdiv_2023_2025" / "scenes" / "S2A_35TLG_20250718_1_L2A"
    source = read_raster_metadata(processed / "ndvi.tif")
    destination = plan_destination_grid(source)
    assert str(destination.crs) == "EPSG:3857"
    assert destination.transform.b == 0
    assert destination.transform.d == 0

    png = render_overlay_png(processed, "ndvi", destination, raw_dir)
    image = Image.open(BytesIO(png))
    assert image.mode == "RGBA"
    assert image.size == (destination.width, destination.height)
    arr = np.array(image)
    assert arr[0, 0, 3] == 0
    assert int(arr[..., 3].max()) == 255
    extent = geographic_extent(destination)
    coords = maplibre_coordinates(extent)
    assert coords[0][0] == extent["west"]
    assert coords[0][1] == extent["north"]
    assert 24.6 < extent["west"] < 24.7
    assert 42.04 < extent["south"] < 42.09


def test_rgb_channel_order_and_valid_black(tmp_path: Path):
    processed = _seed_overlay_scene(
        tmp_path / "raw",
        tmp_path / "processed",
        red_dn=8000,
        valid_black=True,
    )
    raw_dir = tmp_path / "raw" / "plovdiv_2023_2025" / "scenes" / "S2A_35TLG_20250718_1_L2A"
    destination = plan_destination_grid(read_raster_metadata(processed / "ndvi.tif"))
    image = Image.open(BytesIO(render_overlay_png(processed, "rgb", destination, raw_dir)))
    arr = np.array(image)
    valid = arr[..., 3] == 255
    reds = arr[..., 0][valid]
    greens = arr[..., 1][valid]
    blues = arr[..., 2][valid]
    assert reds.mean() > greens.mean() > blues.mean()
    assert (arr[0, 0] == [0, 0, 0, 0]).all()


def test_rotated_source_becomes_north_up(tmp_path: Path):
    processed = _seed_overlay_scene(
        tmp_path / "raw",
        tmp_path / "processed",
        rotated=True,
    )
    source = read_raster_metadata(processed / "ndvi.tif")
    assert source["transform"].b != 0
    destination = plan_destination_grid(source)
    assert destination.transform.b == 0
    assert destination.transform.d == 0


def test_missing_source_is_not_overlay_ready(tmp_path: Path):
    processed = _seed_overlay_scene(
        tmp_path / "raw",
        tmp_path / "processed",
        include_rasters=False,
    )
    sources = inspect_overlay_sources(processed, tmp_path / "raw" / "missing")
    assert sources["overlay_available"] is False


def test_sample_ndvi_nearest(tmp_path: Path):
    processed = _seed_overlay_scene(tmp_path / "raw", tmp_path / "processed")
    with rasterio.open(processed / "ndvi.tif") as dataset:
        lon, lat = rasterio.warp.transform(
            dataset.crs,
            "EPSG:4326",
            [dataset.xy(4, 4)[0]],
            [dataset.xy(4, 4)[1]],
        )
        outside = rasterio.warp.transform(
            dataset.crs,
            "EPSG:4326",
            [dataset.bounds.left - 500],
            [dataset.bounds.bottom - 500],
        )
    inside = sample_ndvi(processed, lon[0], lat[0])
    assert inside["valid"] is True
    assert abs(inside["ndvi"] - 0.5) < 1e-5
    missed = sample_ndvi(processed, outside[0][0], outside[1][0])
    assert missed["inside_raster"] is False


def test_source_rasters_are_not_mutated(tmp_path: Path):
    processed = _seed_overlay_scene(tmp_path / "raw", tmp_path / "processed")
    ndvi = processed / "ndvi.tif"
    before = ndvi.read_bytes()
    destination = plan_destination_grid(read_raster_metadata(ndvi))
    render_overlay_png(
        processed,
        "ndvi",
        destination,
        tmp_path / "raw" / "plovdiv_2023_2025" / "scenes" / "S2A_35TLG_20250718_1_L2A",
    )
    assert ndvi.read_bytes() == before


def test_map_api_and_cache(monkeypatch, tmp_path: Path):
    raw, processed, cache = _configure(monkeypatch, tmp_path)
    _seed_overlay_scene(raw, processed)

    listing = client.get("/api/v1/satellite/datasets/plovdiv_2023_2025/scenes")
    assert listing.status_code == 200
    by_id = {item["scene_id"]: item for item in listing.json()["scenes"]}
    assert by_id["S2A_35TLG_20250718_1_L2A"]["overlay_ready"] is True
    assert by_id["S2A_35TLG_CATALOGONLY_1_L2A"]["overlay_ready"] is False
    assert by_id["S2A_35TLG_20250718_1_L2A"]["platform"] == "sentinel-2a"

    metadata = client.get(
        "/api/v1/satellite/datasets/plovdiv_2023_2025/scenes/"
        "S2A_35TLG_20250718_1_L2A/map/metadata"
    )
    assert metadata.status_code == 200
    body = metadata.json()
    assert body["overlay_available"] is True
    assert set(body["supported_modes"]) == {"rgb", "ndvi"}
    assert body["native_crs"] == "EPSG:32635"
    assert body["rendered_crs"] == "EPSG:3857"
    assert body["geographic_extent"]["crs"] == "EPSG:4326"
    assert len(body["maplibre_coordinates"]) == 4
    assert "server" not in str(body).lower() or "path" not in str(body).lower()

    first = client.get(
        "/api/v1/satellite/datasets/plovdiv_2023_2025/scenes/"
        "S2A_35TLG_20250718_1_L2A/map/ndvi"
    )
    assert first.status_code == 200
    assert first.content[:8] == b"\x89PNG\r\n\x1a\n"
    cached = list(cache.rglob("ndvi.png"))
    assert len(cached) == 1
    mtime = cached[0].stat().st_mtime_ns
    second = client.get(
        "/api/v1/satellite/datasets/plovdiv_2023_2025/scenes/"
        "S2A_35TLG_20250718_1_L2A/map/ndvi"
    )
    assert second.content == first.content
    assert cached[0].stat().st_mtime_ns == mtime

    rgb = client.get(
        "/api/v1/satellite/datasets/plovdiv_2023_2025/scenes/"
        "S2A_35TLG_20250718_1_L2A/map/rgb"
    )
    assert rgb.status_code == 200

    catalog = client.get(
        "/api/v1/satellite/datasets/plovdiv_2023_2025/scenes/"
        "S2A_35TLG_CATALOGONLY_1_L2A/map/metadata"
    )
    assert catalog.status_code == 200
    assert catalog.json()["overlay_available"] is False
    assert client.get(
        "/api/v1/satellite/datasets/plovdiv_2023_2025/scenes/"
        "S2A_35TLG_CATALOGONLY_1_L2A/map/ndvi"
    ).status_code == 404

    assert client.get(
        "/api/v1/satellite/datasets/plovdiv_2023_2025/scenes/../secret/map/ndvi"
    ).status_code in {400, 404, 422}


def test_concurrent_overlay_requests(monkeypatch, tmp_path: Path):
    raw, processed, cache = _configure(monkeypatch, tmp_path)
    _seed_overlay_scene(raw, processed)

    def fetch() -> bytes:
        response = client.get(
            "/api/v1/satellite/datasets/plovdiv_2023_2025/scenes/"
            "S2A_35TLG_20250718_1_L2A/map/ndvi"
        )
        assert response.status_code == 200
        return response.content

    with ThreadPoolExecutor(max_workers=4) as pool:
        payloads = list(pool.map(lambda _: fetch(), range(4)))
    assert len({item for item in payloads}) == 1
    assert len(list(cache.rglob("ndvi.png"))) == 1


def test_different_source_grids_are_aligned_or_rejected(tmp_path: Path):
    processed = _seed_overlay_scene(tmp_path / "raw", tmp_path / "processed")
    write_geotiff(
        processed / "valid_mask.tif",
        np.ones((7, 9), dtype=np.uint8),
        transform=Affine(10.0, 0.0, 305530.0, 0.0, -10.0, 4661340.0),
        nodata=0,
    )
    destination = plan_destination_grid(read_raster_metadata(processed / "ndvi.tif"))
    try:
        render_overlay_png(
            processed,
            "ndvi",
            destination,
            tmp_path / "raw" / "plovdiv_2023_2025" / "scenes" / "S2A_35TLG_20250718_1_L2A",
        )
    except Exception as exc:
        assert "grid" in str(exc).lower() or isinstance(exc, MissingProcessedOutputError)
    else:
        raise AssertionError("Expected mismatched NDVI/mask grids to fail")
