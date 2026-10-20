"""Earth Search STAC discovery for Sentinel-2 time series."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Callable

from shapely import transform as shapely_transform_coords
from shapely.geometry import box, mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

from ml.preprocessing.errors import CatalogSearchError


logger = logging.getLogger(__name__)

DEFAULT_STAC_URL = "https://earth-search.aws.element84.com/v1"
DEFAULT_COLLECTION = "sentinel-2-l2a"
DEFAULT_AREA_CRS = "EPSG:32635"

ASSET_NAMES = {
    "blue": "blue",
    "green": "green",
    "red": "red",
    "nir": "nir",
    "scl": "scl",
}


def search_sentinel2(
    bbox: tuple[float, float, float, float],
    start_date: str,
    end_date: str,
    max_cloud_cover: float = 20.0,
    *,
    stac_url: str = DEFAULT_STAC_URL,
    collection: str = DEFAULT_COLLECTION,
    client_factory: Callable[..., Any] | None = None,
    timeout: int = 30,
    retries: int = 3,
    min_footprint_overlap_pct: float = 0.0,
    target_crs: str = DEFAULT_AREA_CRS,
) -> list[dict[str, Any]]:
    """Search Sentinel-2 L2A items overlapping ``bbox`` in ``start_date``/``end_date``.

    Returns structured scene records. Does not download rasters.
    Pagination is consumed fully; no silent item cap is applied.
    Geometric eligibility uses projected polygon intersection when a
    STAC footprint is present. Bounding-box overlap is stored separately.
    """
    if bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
        raise CatalogSearchError("bbox must be west, south, east, north.")
    start_date, end_date = _normalize_dates(start_date, end_date)
    factory = client_factory or _default_client_factory
    datetime_range = f"{start_date}/{end_date}"

    last_error: Exception | None = None
    items: list[Any] = []
    for attempt in range(1, retries + 1):
        try:
            client = factory(stac_url, timeout=timeout)
            search = client.search(
                collections=[collection],
                bbox=bbox,
                datetime=datetime_range,
                query={"eo:cloud_cover": {"lt": max_cloud_cover}},
            )
            items = list(search.items())
            last_error = None
            break
        except Exception as exc:
            last_error = exc
            logger.warning(
                "STAC search attempt %s/%s failed: %s",
                attempt,
                retries,
                exc,
            )
            time.sleep(min(2 ** (attempt - 1), 8))

    if last_error is not None:
        raise CatalogSearchError(
            "Earth Search STAC query failed after retries."
        ) from last_error

    records = [
        _item_to_record(item, bbox, collection, stac_url, target_crs)
        for item in items
    ]
    records = _deduplicate(records)
    if min_footprint_overlap_pct > 0:
        records = [
            record for record in records
            if (record.get("footprint_overlap_pct") or 0) >= min_footprint_overlap_pct
        ]
    records.sort(key=lambda record: record["acquisition_datetime"])
    logger.info("Discovered %s Sentinel-2 scenes.", len(records))
    return records


def _default_client_factory(stac_url: str, timeout: int = 30):
    from pystac_client import Client

    return Client.open(stac_url, timeout=timeout)


def _normalize_dates(start_date: str, end_date: str) -> tuple[str, str]:
    start = start_date[:10]
    end = end_date[:10]
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except ValueError as exc:
        raise CatalogSearchError("Dates must use YYYY-MM-DD.") from exc
    if start_dt > end_dt:
        raise CatalogSearchError("start_date must be on or before end_date.")
    return start, end


def _item_to_record(
    item: Any,
    aoi_bbox: tuple[float, float, float, float],
    collection: str,
    stac_url: str,
    target_crs: str,
) -> dict[str, Any]:
    properties = getattr(item, "properties", {}) or {}
    datetime_value = _item_datetime(item, properties)
    scene_bbox = list(getattr(item, "bbox", None) or [])
    geometry = getattr(item, "geometry", None)
    assets = {}
    raw_assets = getattr(item, "assets", {}) or {}
    for name in ASSET_NAMES.values():
        asset = raw_assets.get(name)
        if asset is None:
            continue
        fields = _asset_fields(asset)
        href = fields.get("href") or getattr(asset, "href", None)
        if href:
            assets[name] = {
                "href": href,
                "raster:bands": fields.get("raster:bands", []),
            }
    bbox_overlap = aoi_coverage_fraction(aoi_bbox, scene_bbox)
    footprint = footprint_overlap_pct(
        aoi_bbox,
        geometry,
        target_crs=target_crs,
    )
    return {
        "scene_id": item.id,
        "acquisition_datetime": datetime_value,
        "acquisition_date": datetime_value[:10],
        "cloud_cover": properties.get("eo:cloud_cover"),
        "bbox": scene_bbox,
        "geometry": geometry,
        "collection": collection,
        "stac_url": stac_url,
        "platform": properties.get("platform") or properties.get("constellation"),
        "mgrs_tile": properties.get("grid:code") or properties.get("s2:mgrs_tile"),
        "processing_baseline": properties.get("s2:processing_baseline"),
        "boa_offset_applied": properties.get("earthsearch:boa_offset_applied"),
        "bbox_overlap_pct": bbox_overlap,
        "footprint_overlap_pct": footprint,
        "aoi_coverage": footprint if footprint is not None else bbox_overlap,
        "geometry_status": (
            "invalid" if geometry is not None and footprint is None
            else "present" if geometry is not None
            else "missing"
        ),
        "assets": assets,
        "properties": {
            "platform": properties.get("platform"),
            "mgrs": properties.get("grid:code"),
            "eo:cloud_cover": properties.get("eo:cloud_cover"),
        },
    }


def _asset_fields(asset: Any) -> dict[str, Any]:
    if hasattr(asset, "to_dict"):
        payload = asset.to_dict()
        if isinstance(payload, dict):
            return payload
    extra = getattr(asset, "extra_fields", None) or {}
    return dict(extra)


def _item_datetime(item: Any, properties: dict[str, Any]) -> str:
    value = getattr(item, "datetime", None)
    if value is not None:
        text = value.isoformat() if hasattr(value, "isoformat") else str(value)
        return text.replace("+00:00", "Z")
    return str(properties.get("datetime") or "")


def aoi_coverage_fraction(
    aoi_bbox: tuple[float, float, float, float],
    scene_bbox: list[float] | None,
) -> float | None:
    """Approximate AOI coverage from bounding-box intersection.

    Scene-level cloud cover is not the same as AOI cloud cover.
    This value is axis-aligned bbox overlap, not cloudy-pixel fraction
    and not a polygon footprint intersection.
    """
    if not scene_bbox or len(scene_bbox) != 4:
        return None
    west = max(aoi_bbox[0], scene_bbox[0])
    south = max(aoi_bbox[1], scene_bbox[1])
    east = min(aoi_bbox[2], scene_bbox[2])
    north = min(aoi_bbox[3], scene_bbox[3])
    if east <= west or north <= south:
        return 0.0
    aoi_area = (aoi_bbox[2] - aoi_bbox[0]) * (aoi_bbox[3] - aoi_bbox[1])
    if aoi_area <= 0:
        return None
    overlap = (east - west) * (north - south)
    return round(100.0 * overlap / aoi_area, 2)


def footprint_overlap_pct(
    aoi_bbox: tuple[float, float, float, float],
    scene_geometry: dict[str, Any] | BaseGeometry | None,
    *,
    target_crs: str = DEFAULT_AREA_CRS,
    source_crs: str = "EPSG:4326",
) -> float | None:
    """Projected polygon intersection of a STAC footprint and the AOI.

    ``footprint_overlap_pct = 100 * intersection_area / aoi_area``.
    Areas are computed in ``target_crs``. Longitude/latitude degree units
    are never used as a proxy for area.
    """
    aoi = _aoi_polygon(aoi_bbox)
    scene = _scene_polygon(scene_geometry)
    if scene is None:
        return None
    try:
        aoi_proj = _project_geometry(aoi, source_crs, target_crs)
        scene_proj = _project_geometry(scene, source_crs, target_crs)
    except Exception:
        logger.warning("Could not project scene footprint for AOI intersection.")
        return None
    aoi_area = float(aoi_proj.area)
    if aoi_area <= 0:
        return None
    intersection = aoi_proj.intersection(scene_proj)
    return round(100.0 * float(intersection.area) / aoi_area, 2)


def _aoi_polygon(aoi_bbox: tuple[float, float, float, float]) -> BaseGeometry:
    return box(aoi_bbox[0], aoi_bbox[1], aoi_bbox[2], aoi_bbox[3])


def _scene_polygon(geometry: dict[str, Any] | BaseGeometry | None) -> BaseGeometry | None:
    if geometry is None:
        return None
    try:
        geom = geometry if isinstance(geometry, BaseGeometry) else shape(geometry)
    except Exception:
        return None
    if geom.is_empty:
        return None
    if not geom.is_valid:
        geom = make_valid(geom)
    if geom.is_empty:
        return None
    return geom


def _project_geometry(
    geometry: BaseGeometry,
    source_crs: str,
    target_crs: str,
) -> BaseGeometry:
    if source_crs == target_crs:
        return geometry
    from pyproj import Transformer

    transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)

    def _project(coords):
        xs, ys = transformer.transform(coords[:, 0], coords[:, 1])
        projected = coords.copy()
        projected[:, 0] = xs
        projected[:, 1] = ys
        return projected

    projected = shapely_transform_coords(geometry, _project)
    if projected.is_empty:
        raise ValueError("Projected geometry is empty.")
    return projected


def geometry_to_geojson(geometry: Any) -> dict[str, Any] | None:
    if geometry is None:
        return None
    if isinstance(geometry, dict):
        return geometry
    try:
        return mapping(geometry)
    except Exception:
        return None


def _deduplicate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for record in records:
        scene_id = record["scene_id"]
        if scene_id not in unique:
            unique[scene_id] = record
    return list(unique.values())
