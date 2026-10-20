from ml.ingestion.stac import aoi_coverage_fraction, footprint_overlap_pct


AOI = (24.65, 42.05, 24.68, 42.08)


def _polygon(west, south, east, north):
    return {
        "type": "Polygon",
        "coordinates": [[
            [west, south],
            [east, south],
            [east, north],
            [west, north],
            [west, south],
        ]],
    }


def test_full_aoi_coverage():
    coverage = footprint_overlap_pct(AOI, _polygon(24.60, 42.00, 24.80, 42.20))
    assert coverage == 100.0


def test_partial_aoi_coverage():
    coverage = footprint_overlap_pct(AOI, _polygon(24.665, 42.05, 24.80, 42.20))
    assert coverage is not None
    assert 40.0 < coverage < 60.0


def test_no_intersection():
    coverage = footprint_overlap_pct(AOI, _polygon(23.00, 41.00, 23.20, 41.20))
    assert coverage == 0.0


def test_adjacent_mgrs_tile_bbox_false_positive():
    adjacent_bbox = [23.90, 41.70, 24.66, 42.20]
    adjacent_geom = _polygon(23.90, 41.70, 24.64, 42.20)
    bbox_overlap = aoi_coverage_fraction(AOI, adjacent_bbox)
    footprint = footprint_overlap_pct(AOI, adjacent_geom)
    assert bbox_overlap > 0
    assert footprint == 0.0


def test_invalid_geometry_returns_none():
    coverage = footprint_overlap_pct(AOI, {"type": "Polygon", "coordinates": []})
    assert coverage is None


def test_multipolygon_geometry():
    geometry = {
        "type": "MultiPolygon",
        "coordinates": [
            _polygon(23.0, 41.0, 23.2, 41.2)["coordinates"],
            _polygon(24.60, 42.00, 24.80, 42.20)["coordinates"],
        ],
    }
    coverage = footprint_overlap_pct(AOI, geometry)
    assert coverage == 100.0


def test_missing_geometry_returns_none():
    assert footprint_overlap_pct(AOI, None) is None
