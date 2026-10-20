"""Spectral preprocessing utilities for Sentinel-2.

These functions are numerical only. They do not import FastAPI
and they do not read or write files.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

# Accept vegetation and bare-soil classes for this
# first land-analysis experiment.
VALID_SCL_CLASSES = (4, 5)

# Near-zero reflectance sum is treated as an undefined NDVI pixel.
NDVI_DENOMINATOR_EPS = 1e-6

# Display stretch for RGB previews only. The 0.30 saturation
# point and gamma 2.2 produce an sRGB-like inspection image.
# Stretched values are not calibrated scientific measurements.
RGB_STRETCH_SATURATION = 0.30
RGB_DISPLAY_GAMMA = 2.2


def to_reflectance(
    dn: np.ndarray,
    scale: float,
    offset: float = 0.0,
    nodata: float | None = 0,
) -> np.ndarray:
    """
    Convert digital numbers to surface reflectance.

    reflectance = DN * scale + offset

    Values matching the raw no-data code are masked
    BEFORE applying the offset.
    """
    values = np.asarray(dn)
    valid = np.isfinite(values)

    if nodata is not None and not (
        isinstance(nodata, float) and np.isnan(nodata)
    ):
        valid &= values != nodata

    output = values.astype(np.float32) * float(scale) + float(offset)
    output[~valid] = np.nan

    return output


def make_valid_mask(
    scl: np.ndarray,
    *bands: np.ndarray,
    valid_scl_classes: Sequence[int] | None = VALID_SCL_CLASSES,
) -> np.ndarray:
    """Return pixels with usable land classes and finite band values.

    ``valid_scl_classes=None`` disables scene-classification filtering
    and keeps every pixel whose band values are finite.
    """
    scl_array = np.asarray(scl)

    if valid_scl_classes is None:
        valid = np.ones(scl_array.shape, dtype=bool)
    else:
        valid = np.isin(scl_array, tuple(valid_scl_classes))

    for band in bands:
        array = np.asarray(band)
        if array.shape != scl_array.shape:
            raise ValueError(
                "SCL and reflectance bands must have the same shape."
            )
        valid &= np.isfinite(array)

    return valid


def calculate_ndvi(
    red: np.ndarray,
    nir: np.ndarray,
    valid_mask: np.ndarray | None = None,
) -> np.ndarray:
    """
    Calculate NDVI from calibrated reflectance.

    NDVI = (NIR - Red) / (NIR + Red)

    Invalid, non-finite, masked, and near-zero denominator
    pixels are written as NaN.

    Negative reflectance is retained. Atmospheric correction can
    produce small negative BOA values; those are radiometric
    observations, not fill values. They are excluded only when
    the NDVI denominator is undefined.
    """
    red = np.asarray(red, dtype=np.float32)
    nir = np.asarray(nir, dtype=np.float32)

    if red.shape != nir.shape:
        raise ValueError("Red and NIR arrays must have the same shape.")

    denominator = nir + red

    valid = (
        np.isfinite(red)
        & np.isfinite(nir)
        & (np.abs(denominator) > NDVI_DENOMINATOR_EPS)
    )

    if valid_mask is not None:
        mask = np.asarray(valid_mask)
        if mask.shape != red.shape:
            raise ValueError(
                "NDVI mask must have the same shape as the bands."
            )
        valid &= mask.astype(bool)

    result = np.full(red.shape, np.nan, dtype=np.float32)

    np.divide(
        nir - red,
        denominator,
        out=result,
        where=valid,
    )

    return result


def create_rgb(
    red: np.ndarray,
    green: np.ndarray,
    blue: np.ndarray,
    valid_mask: np.ndarray,
) -> np.ndarray:
    """
    Convert reflectance bands into a display RGB image.

    Display stretch: clip(reflectance / 0.30, 0, 1), then gamma 1/2.2.
    This stretch is for visualization only and must not be used as
    calibrated reflectance or as model-training input.
    """
    red = np.asarray(red, dtype=np.float32)
    green = np.asarray(green, dtype=np.float32)
    blue = np.asarray(blue, dtype=np.float32)
    mask = np.asarray(valid_mask, dtype=bool)

    if not (red.shape == green.shape == blue.shape == mask.shape):
        raise ValueError("RGB bands and mask must have the same shape.")

    rgb = np.stack([red, green, blue], axis=-1)
    rgb = np.clip(rgb / RGB_STRETCH_SATURATION, 0, 1)
    rgb = np.power(rgb, 1 / RGB_DISPLAY_GAMMA)
    rgb = np.nan_to_num(rgb, nan=0.0, posinf=0.0, neginf=0.0)
    rgb[~mask] = 0

    return rgb.astype(np.float32)


def calculate_ndvi_statistics(ndvi: np.ndarray) -> dict[str, Any]:
    """Summarize finite NDVI pixels, including an empty valid set."""
    array = np.asarray(ndvi, dtype=np.float32)
    total_pixels = int(array.size)
    values = array[np.isfinite(array)]
    valid_pixels = int(values.size)
    valid_percentage = (
        round(100.0 * valid_pixels / total_pixels, 2)
        if total_pixels
        else 0.0
    )

    if valid_pixels == 0:
        return {
            "valid_pixels": 0,
            "total_pixels": total_pixels,
            "valid_percentage": valid_percentage,
            "minimum": None,
            "maximum": None,
            "mean": None,
            "median": None,
            "standard_deviation": None,
        }

    return {
        "valid_pixels": valid_pixels,
        "total_pixels": total_pixels,
        "valid_percentage": valid_percentage,
        "minimum": float(values.min()),
        "maximum": float(values.max()),
        "mean": float(values.mean()),
        "median": float(np.median(values)),
        "standard_deviation": float(values.std()),
    }
