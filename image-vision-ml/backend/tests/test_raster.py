
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine

from backend.tests.conftest import (
    REFERENCE_CRS,
    REFERENCE_TRANSFORM,
    build_fixture_dataset,
    write_geotiff,
    write_scene_metadata,
)
from ml.preprocessing.errors import (
    MissingBandError,
    RasterAlignmentError,
    UnsupportedCalibrationError,
)
from ml.preprocessing.raster import (
    check_alignment,
    process_local_dataset,
    read_raster_metadata,
    reproject_categorical,
    write_geotiff as write_processed_geotiff,
)


def test_raster_metadata_preserves_crs_and_transform(tmp_path: Path):
    path = write_geotiff(
        tmp_path / "red_B04.tif",
        np.ones((3, 4), dtype=np.uint16),
        scale=0.0001,
        offset=-0.1,
    )

    metadata = read_raster_metadata(path)

    assert metadata["crs"] == rasterio.crs.CRS.from_epsg(32635)
    assert metadata["transform"].almost_equals(REFERENCE_TRANSFORM)
    assert metadata["width"] == 4
    assert metadata["height"] == 3
    assert metadata["resolution"] == (10.0, 10.0)


def test_check_alignment_rejects_misaligned_rasters(tmp_path: Path):
    reference_path = write_geotiff(
        tmp_path / "red_B04.tif",
        np.ones((4, 6), dtype=np.uint16),
    )
    shifted = Affine(10.0, 0.0, 500100.0, 0.0, -10.0, 4700000.0)
    other_path = write_geotiff(
        tmp_path / "nir_B08.tif",
        np.ones((4, 6), dtype=np.uint16),
        transform=shifted,
    )

    reference = read_raster_metadata(reference_path)
    other = read_raster_metadata(other_path)

    try:
        check_alignment(reference, other, name="B08")
    except RasterAlignmentError as exc:
        assert "affine transform" in str(exc)
    else:
        raise AssertionError("Expected RasterAlignmentError")


def test_process_rejects_misaligned_continuous_bands(tmp_path: Path):
    raw_dir = build_fixture_dataset(tmp_path / "raw" / "misaligned")
    write_geotiff(
        raw_dir / "nir_B08.tif",
        np.full((4, 6), 6000, dtype=np.uint16),
        transform=Affine(10.0, 0.0, 501000.0, 0.0, -10.0, 4700000.0),
        scale=0.0001,
        offset=-0.1,
    )

    try:
        process_local_dataset(raw_dir, tmp_path / "out")
    except RasterAlignmentError:
        pass
    else:
        raise AssertionError("Expected RasterAlignmentError")


def test_categorical_nearest_neighbor_reprojection(tmp_path: Path):
    scl = np.array([[4, 5], [8, 4]], dtype=np.uint8)
    scl_path = write_geotiff(
        tmp_path / "scl.tif",
        scl,
        transform=Affine(20.0, 0.0, 500000.0, 0.0, -20.0, 4700000.0),
    )
    reference = {
        "crs": rasterio.crs.CRS.from_string(REFERENCE_CRS),
        "transform": REFERENCE_TRANSFORM,
        "width": 4,
        "height": 4,
        "nodata": 0,
    }

    aligned, _grid = reproject_categorical(scl_path, reference)

    expected = np.array(
        [
            [4, 4, 5, 5],
            [4, 4, 5, 5],
            [8, 8, 4, 4],
            [8, 8, 4, 4],
        ],
        dtype=np.uint8,
    )
    np.testing.assert_array_equal(aligned, expected)


def test_geotiff_round_trip_preserves_grid(tmp_path: Path):
    array = np.array([[0.1, 0.2], [0.3, np.nan]], dtype=np.float32)
    grid = {
        "crs": rasterio.crs.CRS.from_epsg(32635),
        "transform": REFERENCE_TRANSFORM,
        "width": 2,
        "height": 2,
    }
    path = tmp_path / "ndvi_corrected.tif"

    write_processed_geotiff(path, array, grid, np.nan)

    with rasterio.open(path) as dataset:
        assert dataset.crs == grid["crs"]
        assert dataset.transform.almost_equals(REFERENCE_TRANSFORM)
        np.testing.assert_allclose(
            dataset.read(1),
            array,
            equal_nan=True,
        )


def test_all_invalid_scene_is_an_error(tmp_path: Path):
    raw_dir = build_fixture_dataset(tmp_path / "raw" / "all_invalid")
    write_geotiff(
        raw_dir / "scl.tif",
        np.full((4, 6), 8, dtype=np.uint8),
    )
    try:
        process_local_dataset(raw_dir, tmp_path / "out")
    except Exception as exc:
        from ml.preprocessing.errors import NoValidPixelsError
        assert isinstance(exc, NoValidPixelsError)
    else:
        raise AssertionError("Expected NoValidPixelsError")


def test_missing_required_band(tmp_path: Path):
    raw_dir = tmp_path / "raw" / "missing_band"
    write_scene_metadata(raw_dir)
    write_geotiff(
        raw_dir / "nir_B08.tif",
        np.full((4, 6), 6000, dtype=np.uint16),
        scale=0.0001,
        offset=-0.1,
    )

    try:
        process_local_dataset(raw_dir, tmp_path / "out")
    except MissingBandError as exc:
        assert "B04" in str(exc)
    else:
        raise AssertionError("Expected MissingBandError")


def test_missing_calibration_is_an_error(tmp_path: Path):
    raw_dir = tmp_path / "raw" / "no_cal"
    write_scene_metadata(raw_dir)
    write_geotiff(
        raw_dir / "red_B04.tif",
        np.full((2, 2), 3000, dtype=np.uint16),
    )
    write_geotiff(
        raw_dir / "nir_B08.tif",
        np.full((2, 2), 6000, dtype=np.uint16),
    )
    write_geotiff(
        raw_dir / "scl.tif",
        np.full((2, 2), 4, dtype=np.uint8),
    )

    try:
        process_local_dataset(
            raw_dir,
            tmp_path / "out",
            generate_rgb=False,
        )
    except UnsupportedCalibrationError:
        pass
    else:
        raise AssertionError("Expected UnsupportedCalibrationError")


def test_process_local_dataset_writes_outputs(tmp_path: Path):
    raw_dir = build_fixture_dataset(tmp_path / "raw" / "fixture_scene")
    output_dir = tmp_path / "processed" / "fixture_scene"

    result = process_local_dataset(raw_dir, output_dir)

    assert result["status"] == "processed"
    assert (output_dir / "ndvi_corrected.tif").is_file()
    assert (output_dir / "ndvi_corrected.png").is_file()
    assert (output_dir / "rgb_preview.png").is_file()
    assert (output_dir / "valid_mask.tif").is_file()
    assert (output_dir / "processing_metadata.json").is_file()
    assert result["ndvi"]["minimum"] is not None
    assert result["valid_pixels"] > 0

    reused = process_local_dataset(raw_dir, output_dir)
    assert reused["status"] == "already_processed"


def test_shared_target_grid_alignment(tmp_path: Path):
    raw_a = build_fixture_dataset(tmp_path / "raw" / "scene_a")
    raw_b = build_fixture_dataset(tmp_path / "raw" / "scene_b")
    grid = {
        "crs": rasterio.crs.CRS.from_epsg(32635),
        "transform": Affine(20.0, 0.0, 500000.0, 0.0, -20.0, 4700000.0),
        "width": 3,
        "height": 2,
        "bounds": (500000.0, 4699960.0, 500060.0, 4700000.0),
        "resolution": (20.0, 20.0),
    }
    result_a = process_local_dataset(
        raw_a,
        tmp_path / "out_a",
        target_grid=grid,
        ndvi_filename="ndvi.tif",
        statistics_filename="statistics.json",
    )
    result_b = process_local_dataset(
        raw_b,
        tmp_path / "out_b",
        target_grid=grid,
        ndvi_filename="ndvi.tif",
        statistics_filename="statistics.json",
    )
    assert result_a["raster"]["crs"] == result_b["raster"]["crs"]
    assert result_a["raster"]["width"] == result_b["raster"]["width"]
    assert result_a["raster"]["height"] == result_b["raster"]["height"]
    assert result_a["raster"]["transform"] == result_b["raster"]["transform"]
    assert (tmp_path / "out_a" / "ndvi.tif").is_file()
    assert (tmp_path / "out_a" / "statistics.json").is_file()
