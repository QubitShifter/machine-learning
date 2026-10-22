"""Validate study-area bounding boxes and polygons.

Geometry checks are independent of satellite processing. Passing validation
does not create a dataset or start a download.
"""

from __future__ import annotations

import math
from typing import Any


MIN_AREA_KM2 = 0.01
MAX_AREA_KM2 = 2500.0
MAX_EDGE_DEG = 2.0
STATUS_OPERATIONAL = "operational"
STATUS_DRAFT = "draft"


class AoiGeometryError(ValueError):
    """Raised when a proposed study area is not a valid geographic geometry."""


def validate_bbox(bbox: list[float] | tuple[float, ...]) -> list[float]:
    if bbox is None or len(bbox) != 4:
        raise AoiGeometryError("Bounding box must be [west, south, east, north].")
    west, south, east, north = (float(value) for value in bbox)
    if not (-180.0 <= west <= 180.0 and -180.0 <= east <= 180.0):
        raise AoiGeometryError("Longitude must be within [-180, 180].")
    if not (-90.0 <= south <= 90.0 and -90.0 <= north <= 90.0):
        raise AoiGeometryError("Latitude must be within [-90, 90].")
    if west >= east:
        raise AoiGeometryError("Bounding box west must be less than east.")
    if south >= north:
        raise AoiGeometryError("Bounding box south must be less than north.")
    if (east - west) > MAX_EDGE_DEG or (north - south) > MAX_EDGE_DEG:
        raise AoiGeometryError(
            f"Draft AOI edges must be at most {MAX_EDGE_DEG} degrees in this phase."
        )
    area = bbox_area_km2(west, south, east, north)
    if area < MIN_AREA_KM2:
        raise AoiGeometryError(
            f"Draft AOI area {area:.4f} km² is below the {MIN_AREA_KM2} km² minimum."
        )
    if area > MAX_AREA_KM2:
        raise AoiGeometryError(
            f"Draft AOI area {area:.1f} km² exceeds the {MAX_AREA_KM2:.0f} km² maximum."
        )
    return [west, south, east, north]


def validate_polygon(coordinates: list[list[float]]) -> list[list[float]]:
    if not coordinates or len(coordinates) < 3:
        raise AoiGeometryError("Polygon requires at least three vertices.")
    ring = [[float(vertex[0]), float(vertex[1])] for vertex in coordinates]
    if ring[0] != ring[-1]:
        ring.append(ring[0][:])
    if len(ring) < 4:
        raise AoiGeometryError("Closed polygon requires at least three distinct vertices.")
    for lon, lat in ring:
        if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
            raise AoiGeometryError("Polygon vertices must be valid WGS84 coordinates.")
    unique = ring[:-1]
    if len({(round(lon, 7), round(lat, 7)) for lon, lat in unique}) < 3:
        raise AoiGeometryError("Polygon vertices are not distinct.")
    lons = [vertex[0] for vertex in unique]
    lats = [vertex[1] for vertex in unique]
    bbox = validate_bbox([min(lons), min(lats), max(lons), max(lats)])
    if _self_intersects(ring):
        raise AoiGeometryError("Draft polygon edges must not self-intersect.")
    area = polygon_area_km2(ring)
    if area < MIN_AREA_KM2:
        raise AoiGeometryError(
            f"Draft polygon area {area:.4f} km² is below the {MIN_AREA_KM2} km² minimum."
        )
    return ring


def bbox_area_km2(west: float, south: float, east: float, north: float) -> float:
    mean_lat = math.radians((south + north) / 2.0)
    meters_per_deg_lat = 110574.0
    meters_per_deg_lon = 111320.0 * math.cos(mean_lat)
    width_m = abs(east - west) * meters_per_deg_lon
    height_m = abs(north - south) * meters_per_deg_lat
    return (width_m * height_m) / 1_000_000.0


def polygon_area_km2(ring: list[list[float]]) -> float:
    if len(ring) < 4:
        return 0.0
    origin_lat = sum(vertex[1] for vertex in ring[:-1]) / (len(ring) - 1)
    meters_per_deg_lat = 110574.0
    meters_per_deg_lon = 111320.0 * math.cos(math.radians(origin_lat))
    xs = [(vertex[0] - ring[0][0]) * meters_per_deg_lon for vertex in ring]
    ys = [(vertex[1] - ring[0][1]) * meters_per_deg_lat for vertex in ring]
    twice = 0.0
    for index in range(len(xs) - 1):
        twice += xs[index] * ys[index + 1] - xs[index + 1] * ys[index]
    return abs(twice) / 2.0 / 1_000_000.0


def describe_scope(bbox: list[float]) -> dict[str, Any]:
    west, south, east, north = bbox
    area = bbox_area_km2(west, south, east, north)
    width_m = abs(east - west) * 111320.0 * math.cos(math.radians((south + north) / 2.0))
    height_m = abs(north - south) * 110574.0
    pixels_10m = int(round((width_m * height_m) / 100.0))
    return {
        "area_km2": area,
        "width_m": width_m,
        "height_m": height_m,
        "approximate_10m_pixels": pixels_10m,
        "approximate_era5_cells": max(1, math.ceil((east - west) / 0.1))
        * max(1, math.ceil((north - south) / 0.1)),
        "sentinel2_note": (
            "Sentinel-2 L2A would be requested as a new dataset in a later phase. "
            "This phase does not download imagery."
        ),
        "weather_note": (
            "ERA5-Land weather/soil cells are ~0.1°. A new AOI does not create "
            "weather or soil datasets automatically."
        ),
        "download_started": False,
    }


def geometry_payload(
    *,
    kind: str,
    bbox: list[float] | None = None,
    coordinates: list[list[float]] | None = None,
) -> dict[str, Any]:
    kind = str(kind).lower()
    if kind == "bbox":
        validated = validate_bbox(bbox or [])
        ring = [
            [validated[0], validated[1]],
            [validated[2], validated[1]],
            [validated[2], validated[3]],
            [validated[0], validated[3]],
            [validated[0], validated[1]],
        ]
        return {
            "type": "bbox",
            "bbox": validated,
            "coordinates": ring,
            "crs": "EPSG:4326",
            "valid": True,
            **describe_scope(validated),
        }
    if kind == "polygon":
        ring = validate_polygon(coordinates or [])
        lons = [vertex[0] for vertex in ring[:-1]]
        lats = [vertex[1] for vertex in ring[:-1]]
        validated = [min(lons), min(lats), max(lons), max(lats)]
        payload = {
            "type": "polygon",
            "bbox": validated,
            "coordinates": ring,
            "crs": "EPSG:4326",
            "valid": True,
            **describe_scope(validated),
        }
        payload["area_km2"] = polygon_area_km2(ring)
        return payload
    raise AoiGeometryError("Geometry type must be bbox or polygon.")


def _segments(ring: list[list[float]]) -> list[tuple[list[float], list[float]]]:
    return [(ring[index], ring[index + 1]) for index in range(len(ring) - 1)]


def _orientation(a: list[float], b: list[float], c: list[float]) -> int:
    value = (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])
    if abs(value) < 1e-15:
        return 0
    return 1 if value > 0 else 2


def _on_segment(a: list[float], b: list[float], c: list[float]) -> bool:
    return (
        min(a[0], c[0]) - 1e-12 <= b[0] <= max(a[0], c[0]) + 1e-12
        and min(a[1], c[1]) - 1e-12 <= b[1] <= max(a[1], c[1]) + 1e-12
    )


def _intersect(p1: list[float], q1: list[float], p2: list[float], q2: list[float]) -> bool:
    o1 = _orientation(p1, q1, p2)
    o2 = _orientation(p1, q1, q2)
    o3 = _orientation(p2, q2, p1)
    o4 = _orientation(p2, q2, q1)
    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and _on_segment(p1, p2, q1):
        return True
    if o2 == 0 and _on_segment(p1, q2, q1):
        return True
    if o3 == 0 and _on_segment(p2, p1, q2):
        return True
    if o4 == 0 and _on_segment(p2, q1, q2):
        return True
    return False


def _self_intersects(ring: list[list[float]]) -> bool:
    segments = _segments(ring)
    count = len(segments)
    for i in range(count):
        for j in range(i + 1, count):
            if abs(i - j) <= 1 or (i == 0 and j == count - 1):
                continue
            if _intersect(*segments[i], *segments[j]):
                return True
    return False
