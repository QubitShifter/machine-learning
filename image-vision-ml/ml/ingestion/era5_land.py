"""CDS ERA5-Land request construction and credential checks.

Importing this module does not contact the network.
"""

from __future__ import annotations

import calendar
import logging
from datetime import date
from pathlib import Path
from typing import Any

from ml.preprocessing.errors import CdsAuthenticationError, WeatherDownloadError


logger = logging.getLogger(__name__)

DEFAULT_CDS_URL = "https://cds.climate.copernicus.eu/api"
DEFAULT_CONFIG_PATH = Path.home() / ".cdsapirc"
HOURS = [f"{hour:02d}:00" for hour in range(24)]


def cds_auth_status(config_path: Path | None = None) -> dict[str, Any]:
    """Report whether CDS credentials exist without exposing secrets."""
    path = Path(config_path or DEFAULT_CONFIG_PATH)
    if not path.is_file():
        return {
            "configured": False,
            "config_path": str(path),
            "url_present": False,
            "key_present": False,
            "message": (
                "CDS credentials are not configured. Create "
                f"{path} with url and key from "
                "https://cds.climate.copernicus.eu/how-to-api "
                "and accept the ERA5-Land terms on the dataset page."
            ),
        }
    values = _read_cdsapirc(path)
    url_present = bool(values.get("url"))
    key_present = bool(values.get("key"))
    configured = url_present and key_present
    return {
        "configured": configured,
        "config_path": str(path),
        "url_present": url_present,
        "key_present": key_present,
        "url_host": _url_host(values.get("url")),
        "message": (
            "CDS API configuration is present."
            if configured
            else "CDS configuration file exists but url or key is missing."
        ),
    }


def require_cds_auth(config_path: Path | None = None) -> dict[str, Any]:
    status = cds_auth_status(config_path)
    if not status["configured"]:
        raise CdsAuthenticationError(status["message"])
    return status


def month_days(year: int, month: int) -> list[str]:
    last = calendar.monthrange(year, month)[1]
    return [f"{day:02d}" for day in range(1, last + 1)]


def next_month_start(year: int, month: int) -> date:
    if month == 12:
        return date(year + 1, 1, 1)
    return date(year, month + 1, 1)


def cds_retrieval_area(config: dict[str, Any]) -> list[float]:
    """CDS ``area`` in north, west, south, east order.

    This is the meteorological retrieval crop, not the scientific study AOI.
    ERA5-Land is ~0.1°. A crop smaller than one grid cell returns
    MultiAdaptorNoDataError from MARS.
    """
    spatial = config.get("spatial") or {}
    area = spatial.get("retrieval_area")
    if area is None:
        from ml.preprocessing.weather import expand_bbox_to_retrieval_area

        area = expand_bbox_to_retrieval_area(tuple(config["area"]["bbox"]))
    return [float(value) for value in area]


def study_aoi_bbox(config: dict[str, Any]) -> list[float]:
    """Study AOI in west, south, east, north order."""
    return [float(value) for value in config["area"]["bbox"]]


def build_era5_land_request(
    config: dict[str, Any],
    *,
    year: int,
    month: int,
    days: list[str] | None = None,
    times: list[str] | None = None,
) -> dict[str, Any]:
    """Build a CDS retrieve payload. This is not an API call."""
    return {
        "variable": list(config["variables"]),
        "year": [f"{year:04d}"],
        "month": [f"{month:02d}"],
        "day": days or month_days(year, month),
        "time": times or list(HOURS),
        "data_format": config["source"].get("data_format", "netcdf"),
        "download_format": config["source"].get("download_format", "unarchived"),
        "area": cds_retrieval_area(config),
    }


def build_boundary_request(config: dict[str, Any], year: int, month: int) -> dict[str, Any]:
    """Request the following day's 00:00 UTC accumulation boundary."""
    boundary = next_month_start(year, month)
    return build_era5_land_request(
        config,
        year=boundary.year,
        month=boundary.month,
        days=["01"],
        times=["00:00"],
    )


def partition_months(start: str, end: str) -> list[str]:
    first = date.fromisoformat(start[:10])
    last = date.fromisoformat(end[:10])
    months = []
    cursor = date(first.year, first.month, 1)
    end_month = date(last.year, last.month, 1)
    while cursor <= end_month:
        months.append(f"{cursor.year:04d}-{cursor.month:02d}")
        cursor = next_month_start(cursor.year, cursor.month)
    return months


def detect_file_format(path: Path) -> str:
    header = path.read_bytes()[:64].lstrip()
    if header.startswith(b"{") or header.startswith(b"["):
        return "json"
    if header.startswith(b"GRIB"):
        return "grib"
    if header.startswith(b"CDF") or header.startswith(b"\x89HDF"):
        return "netcdf"
    raise WeatherDownloadError(
        f"Downloaded file {path.name} is not a recognised GRIB, NetCDF, or JSON payload."
    )


def target_filename(month: str, fmt: str, *, boundary: bool = False) -> str:
    suffixes = {"grib": "grib", "json": "json", "netcdf": "nc"}
    suffix = suffixes.get(fmt, "nc")
    extra = ".boundary" if boundary else ""
    return f"{month}{extra}.{suffix}"


def _read_cdsapirc(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def _url_host(url: str | None) -> str | None:
    if not url:
        return None
    text = url.replace("https://", "").replace("http://", "")
    return text.split("/")[0]


VARIABLE_ALIASES = {
    "t2m": ("t2m", "2m_temperature"),
    "d2m": ("d2m", "2m_dewpoint_temperature"),
    "tp": ("tp", "total_precipitation"),
    "u10": ("u10", "10m_u_component_of_wind", "u_component_of_wind_10m"),
    "v10": ("v10", "10m_v_component_of_wind", "v_component_of_wind_10m"),
    "e": ("e", "total_evaporation"),
    "swvl1": ("swvl1", "volumetric_soil_water_layer_1"),
    "swvl2": ("swvl2", "volumetric_soil_water_layer_2"),
    "swvl3": ("swvl3", "volumetric_soil_water_layer_3"),
    "swvl4": ("swvl4", "volumetric_soil_water_layer_4"),
    "stl1": ("stl1", "soil_temperature_level_1"),
    "stl2": ("stl2", "soil_temperature_level_2"),
    "stl3": ("stl3", "soil_temperature_level_3"),
    "stl4": ("stl4", "soil_temperature_level_4"),
}


def extract_hourly_records(
    path: Path,
    *,
    bbox: tuple[float, float, float, float],
    method: str = "nearest_grid_cell",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Read a downloaded ERA5-Land file into hourly dictionaries.

    JSON fixtures are supported so unit tests stay offline and do not
    require a NetCDF or GRIB engine.
    """
    path = Path(path)
    if path.suffix.lower() == ".json":
        return _extract_json(path, bbox)
    fmt = detect_file_format(path)
    if fmt == "json":
        return _extract_json(path, bbox)
    if fmt == "grib":
        return _extract_xarray(path, bbox, engine="cfgrib")
    return _extract_xarray(path, bbox, engine=None)


def _extract_json(
    path: Path,
    bbox: tuple[float, float, float, float],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise WeatherDownloadError(f"{path.name} is not a weather record object.")
    records = list(payload.get("hours") or payload.get("records") or [])
    spatial = payload.get("spatial") or {
        "method": "nearest_grid_cell",
        "query_longitude": (bbox[0] + bbox[2]) / 2.0,
        "query_latitude": (bbox[1] + bbox[3]) / 2.0,
        "native_resolution_deg": 0.1,
    }
    return records, spatial


def _extract_xarray(
    path: Path,
    bbox: tuple[float, float, float, float],
    engine: str | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        import xarray as xr
    except ImportError as exc:
        raise WeatherDownloadError(
            "xarray is required to read ERA5-Land NetCDF or GRIB files."
        ) from exc

    open_kwargs: dict[str, Any] = {}
    if engine:
        open_kwargs["engine"] = engine
    try:
        dataset = xr.open_dataset(path, **open_kwargs)
    except Exception as exc:
        if engine == "cfgrib":
            raise WeatherDownloadError(
                f"GRIB file {path.name} could not be read. Install cfgrib "
                "or request NetCDF from CDS (data_format=netcdf)."
            ) from exc
        raise WeatherDownloadError(f"Weather file {path.name} could not be read.") from exc

    try:
        return _records_from_dataset(dataset, bbox)
    finally:
        dataset.close()


def _records_from_dataset(dataset, bbox: tuple[float, float, float, float]):
    from datetime import datetime, timezone

    from ml.preprocessing.weather import aoi_centroid, nearest_era5_land_cell

    lon_name = _coord_name(dataset, ("longitude", "lon", "longitudes"))
    lat_name = _coord_name(dataset, ("latitude", "lat", "latitudes"))
    time_name = _coord_name(dataset, ("valid_time", "time"))
    longitudes = dataset[lon_name].values.ravel()
    latitudes = dataset[lat_name].values.ravel()
    if longitudes.size == 0 or latitudes.size == 0:
        raise WeatherDownloadError(
            "Downloaded ERA5-Land file contains no grid points. "
            "The CDS retrieval area must include at least one native cell."
        )
    query_lon, query_lat = aoi_centroid(bbox)
    spatial = nearest_era5_land_cell(query_lon, query_lat, longitudes, latitudes)
    spatial["study_aoi"] = list(bbox)
    spatial["downloaded_longitudes"] = [float(value) for value in longitudes]
    spatial["downloaded_latitudes"] = [float(value) for value in latitudes]
    subset = dataset
    if dataset[lon_name].ndim >= 1 and dataset[lon_name].size > 1:
        subset = subset.isel({lon_name: spatial["longitude_index"]})
    if dataset[lat_name].ndim >= 1 and dataset[lat_name].size > 1:
        subset = subset.isel({lat_name: spatial["latitude_index"]})

    times = subset[time_name].values
    records = []
    for index, stamp in enumerate(times):
        parsed = _numpy_time_to_utc(stamp)
        if parsed is None:
            continue
        point = subset.isel({time_name: index})
        record = {"timestamp_utc": parsed.isoformat().replace("+00:00", "Z")}
        for key, names in VARIABLE_ALIASES.items():
            if any(name in point for name in names):
                record[key] = _scalar(point, names)
        records.append(record)
    spatial["source_format"] = "xarray"
    return records, spatial


def _coord_name(dataset, names: tuple[str, ...]) -> str:
    lowered = {str(name).lower(): name for name in list(dataset.coords) + list(dataset.variables)}
    for candidate in names:
        if candidate in dataset.coords or candidate in dataset.variables:
            return candidate
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]
    raise WeatherDownloadError(
        f"Weather file is missing coordinate {names[0]}."
    )


def _scalar(dataset, names: tuple[str, ...]) -> float | None:
    import numpy as np

    for name in names:
        if name in dataset:
            value = np.asarray(dataset[name].values).reshape(-1)[0]
            if value is None or (isinstance(value, float) and np.isnan(value)):
                return None
            return float(value)
    return None


def _numpy_time_to_utc(value) -> Any:
    from datetime import datetime, timezone

    import numpy as np
    import pandas as pd

    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    try:
        parsed = pd.to_datetime(value, utc=True).to_pydatetime()
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None
