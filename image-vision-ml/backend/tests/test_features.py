
import numpy as np

from ml.preprocessing.features import (
    calculate_ndvi,
    calculate_ndvi_statistics,
    create_rgb,
    make_valid_mask,
    to_reflectance,
)


def test_reflectance_scale_and_offset():
    dn = np.array([0, 1000, 3000])

    result = to_reflectance(
        dn,
        scale=0.0001,
        offset=-0.1,
        nodata=0,
    )

    assert np.isnan(result[0])
    assert np.isclose(result[1], 0.0)
    assert np.isclose(result[2], 0.2)


def test_reflectance_masks_non_finite_values():
    dn = np.array([np.nan, np.inf, 2000.0])

    result = to_reflectance(dn, scale=0.0001, offset=-0.1, nodata=None)

    assert np.isnan(result[0])
    assert np.isnan(result[1])
    assert np.isclose(result[2], 0.1)


def test_ndvi_formula():
    red = np.array([[0.2]], dtype=np.float32)
    nir = np.array([[0.6]], dtype=np.float32)

    result = calculate_ndvi(red, nir)

    assert np.isclose(result[0, 0], 0.5)


def test_ndvi_zero_denominator():
    red = np.array([[0.0, 1e-12]], dtype=np.float32)
    nir = np.array([[0.0, 1e-12]], dtype=np.float32)

    result = calculate_ndvi(red, nir)

    assert np.isnan(result[0, 0])
    assert np.isnan(result[0, 1])


def test_ndvi_nodata_keeps_negative_reflectance():
    red = np.array([[np.nan, -0.1, 0.2]], dtype=np.float32)
    nir = np.array([[0.4, 0.4, 0.6]], dtype=np.float32)

    result = calculate_ndvi(red, nir)

    assert np.isnan(result[0, 0])
    assert np.isclose(result[0, 1], 0.5 / 0.3)
    assert np.isclose(result[0, 2], 0.5)


def test_scl_mask():
    scl = np.array([[4, 5, 6, 8, 9, 11]])

    mask = make_valid_mask(scl)

    expected = np.array([
        [True, True, False, False, False, False]
    ])

    np.testing.assert_array_equal(mask, expected)


def test_valid_and_rejected_scl_classes_are_configurable():
    scl = np.array([[4, 5, 6]])
    red = np.array([[0.2, 0.2, 0.2]])

    default_mask = make_valid_mask(scl, red)
    custom_mask = make_valid_mask(
        scl,
        red,
        valid_scl_classes=(6,),
    )
    unfiltered = make_valid_mask(
        scl,
        red,
        valid_scl_classes=None,
    )

    np.testing.assert_array_equal(
        default_mask,
        np.array([[True, True, False]]),
    )
    np.testing.assert_array_equal(
        custom_mask,
        np.array([[False, False, True]]),
    )
    np.testing.assert_array_equal(
        unfiltered,
        np.array([[True, True, True]]),
    )


def test_ndvi_respects_mask():
    red = np.array([[0.2, 0.2]])
    nir = np.array([[0.6, 0.6]])
    mask = np.array([[True, False]])

    result = calculate_ndvi(red, nir, mask)

    assert np.isclose(result[0, 0], 0.5)
    assert np.isnan(result[0, 1])


def test_empty_valid_mask_statistics():
    ndvi = np.full((3, 3), np.nan, dtype=np.float32)

    stats = calculate_ndvi_statistics(ndvi)

    assert stats["valid_pixels"] == 0
    assert stats["total_pixels"] == 9
    assert stats["valid_percentage"] == 0.0
    assert stats["minimum"] is None
    assert stats["mean"] is None


def test_ndvi_statistics_from_valid_pixels():
    ndvi = np.array([[0.2, 0.4], [np.nan, 0.6]], dtype=np.float32)

    stats = calculate_ndvi_statistics(ndvi)

    assert stats["valid_pixels"] == 3
    assert stats["total_pixels"] == 4
    assert stats["valid_percentage"] == 75.0
    assert np.isclose(stats["minimum"], 0.2)
    assert np.isclose(stats["maximum"], 0.6)
    assert np.isclose(stats["mean"], 0.4)
    assert np.isclose(stats["median"], 0.4)


def test_rgb_output_shape_and_range():
    red = np.array([[0.15, 0.45]], dtype=np.float32)
    green = np.array([[0.10, 0.20]], dtype=np.float32)
    blue = np.array([[0.05, 0.09]], dtype=np.float32)
    mask = np.array([[True, False]])

    rgb = create_rgb(red, green, blue, mask)

    assert rgb.shape == (1, 2, 3)
    assert rgb.dtype == np.float32
    assert np.all(rgb >= 0)
    assert np.all(rgb <= 1)
    assert np.all(rgb[0, 1] == 0)
    assert rgb[0, 0, 0] > 0
