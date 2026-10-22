"""Domain errors for satellite raster processing."""

from __future__ import annotations


class SatelliteProcessingError(Exception):
    """Base error for recoverable satellite-processing failures."""


class InvalidImageIdError(SatelliteProcessingError):
    """The requested dataset identifier is not a safe local image ID."""


class DatasetNotFoundError(SatelliteProcessingError):
    """No registered local satellite dataset matches the requested ID."""


class MissingBandError(SatelliteProcessingError):
    """A required local raster band is not present."""


class CorruptedRasterError(SatelliteProcessingError):
    """A GeoTIFF exists but cannot be read as a valid raster."""


class InvalidMetadataError(SatelliteProcessingError):
    """Dataset metadata is missing, malformed, or incomplete."""


class UnsupportedCalibrationError(SatelliteProcessingError):
    """Reflectance scale/offset cannot be established from local metadata."""


class RasterAlignmentError(SatelliteProcessingError):
    """Rasters that must share a grid are not aligned."""


class NoValidPixelsError(SatelliteProcessingError):
    """Masking left no finite pixels for analysis."""


class MissingProcessedOutputError(SatelliteProcessingError):
    """A processed visualization or statistic has not been generated yet."""


class DatasetConfigError(SatelliteProcessingError):
    """A time-series dataset configuration file is invalid."""


class CatalogSearchError(SatelliteProcessingError):
    """The STAC catalog search failed."""


class DownloadError(SatelliteProcessingError):
    """A satellite asset download failed or was incomplete."""


class WeatherConfigError(DatasetConfigError):
    """A weather dataset configuration file is invalid."""


class SoilConfigError(DatasetConfigError):
    """A soil-moisture dataset configuration file is invalid."""


class AgriculturalMlError(DatasetConfigError):
    """Agricultural research-dataset configuration or validation failure."""


class SoilForecastingError(AgriculturalMlError):
    """Soil-moisture forecasting experiment configuration or validation failure."""


class CdsAuthenticationError(SatelliteProcessingError):
    """CDS API credentials are missing or incomplete."""


class WeatherDownloadError(DownloadError):
    """A weather asset download failed or was incomplete."""


class SoilDownloadError(WeatherDownloadError):
    """A soil-moisture asset download failed or was incomplete."""


class PermanentCdsRequestError(WeatherDownloadError):
    """CDS rejected the request permanently; retrying will not help."""
