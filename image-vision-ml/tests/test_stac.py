from datetime import datetime, timezone

from ml.ingestion.stac import aoi_coverage_fraction, footprint_overlap_pct, search_sentinel2
from ml.preprocessing.errors import CatalogSearchError


class FakeAsset:
    def __init__(self, href):
        self.href = href
        self.extra_fields = {
            "raster:bands": [{"scale": 0.0001, "offset": -0.1}],
        }


class FakeItem:
    def __init__(self, scene_id, when, cloud, bbox, geometry=None):
        self.id = scene_id
        self.datetime = when
        self.bbox = bbox
        self.geometry = geometry
        self.properties = {
            "eo:cloud_cover": cloud,
            "s2:processing_baseline": "05.11",
            "earthsearch:boa_offset_applied": True,
        }
        self.assets = {
            "red": FakeAsset(f"https://example/{scene_id}/B04.tif"),
            "nir": FakeAsset(f"https://example/{scene_id}/B08.tif"),
        }


class FakeSearch:
    def __init__(self, items):
        self._items = items

    def items(self):
        yield from self._items


class FakeClient:
    def __init__(self, items):
        self.items = items
        self.calls = []

    def search(self, **kwargs):
        self.calls.append(kwargs)
        return FakeSearch(self.items)


def _factory(items, error=None):
    client = FakeClient(items)

    def factory(stac_url, timeout=30):
        if error:
            raise error
        return client

    factory.client = client
    return factory


def test_search_query_construction_and_order():
    bbox = (24.65, 42.05, 24.68, 42.08)
    items = [
        FakeItem(
            "S2B_35TLG_20250916_1_L2A",
            datetime(2025, 9, 16, tzinfo=timezone.utc),
            1.0,
            list(bbox),
        ),
        FakeItem(
            "S2A_35TLG_20250319_1_L2A",
            datetime(2025, 3, 19, tzinfo=timezone.utc),
            5.0,
            list(bbox),
        ),
    ]
    factory = _factory(items)
    records = search_sentinel2(
        bbox, "2025-01-01", "2025-12-31", 20.0, client_factory=factory
    )
    call = factory.client.calls[0]
    assert call["collections"] == ["sentinel-2-l2a"]
    assert call["bbox"] == bbox
    assert call["datetime"] == "2025-01-01/2025-12-31"
    assert call["query"]["eo:cloud_cover"]["lt"] == 20.0
    assert [item["scene_id"] for item in records] == [
        "S2A_35TLG_20250319_1_L2A",
        "S2B_35TLG_20250916_1_L2A",
    ]


def test_search_pagination_is_fully_consumed():
    bbox = (24.65, 42.05, 24.68, 42.08)
    items = [
        FakeItem(
            f"S2B_35TLG_20250{index:02d}01_1_L2A",
            datetime(2025, index, 1, tzinfo=timezone.utc),
            1.0,
            list(bbox),
        )
        for index in range(1, 6)
    ]
    records = search_sentinel2(
        bbox, "2025-01-01", "2025-12-31", client_factory=_factory(items)
    )
    assert len(records) == 5


def test_duplicate_scene_ids_are_removed():
    bbox = (24.65, 42.05, 24.68, 42.08)
    item = FakeItem(
        "S2B_35TLG_20250916_1_L2A",
        datetime(2025, 9, 16, tzinfo=timezone.utc),
        1.0,
        list(bbox),
    )
    records = search_sentinel2(
        bbox, "2025-01-01", "2025-12-31", client_factory=_factory([item, item])
    )
    assert len(records) == 1


def test_empty_search_results():
    records = search_sentinel2(
        (24.65, 42.05, 24.68, 42.08),
        "2025-01-01",
        "2025-12-31",
        client_factory=_factory([]),
    )
    assert records == []


def test_network_error_is_wrapped():
    try:
        search_sentinel2(
            (24.65, 42.05, 24.68, 42.08),
            "2025-01-01",
            "2025-12-31",
            client_factory=_factory([], error=ConnectionError("offline")),
            retries=1,
        )
    except CatalogSearchError:
        return
    raise AssertionError("Expected CatalogSearchError")


def test_invalid_date_range():
    try:
        search_sentinel2(
            (24.65, 42.05, 24.68, 42.08),
            "2025-12-31",
            "2025-01-01",
            client_factory=_factory([]),
        )
    except CatalogSearchError:
        return
    raise AssertionError("Expected CatalogSearchError")


def test_adjacent_tile_is_filtered_by_footprint():
    aoi = (24.65, 42.05, 24.68, 42.08)
    adjacent_geom = {
        "type": "Polygon",
        "coordinates": [[
            [23.90, 41.70],
            [24.64, 41.70],
            [24.64, 42.20],
            [23.90, 42.20],
            [23.90, 41.70],
        ]],
    }
    covering_geom = {
        "type": "Polygon",
        "coordinates": [[
            [24.60, 42.00],
            [24.80, 42.00],
            [24.80, 42.20],
            [24.60, 42.20],
            [24.60, 42.00],
        ]],
    }
    items = [
        FakeItem(
            "S2C_34TGM_20250203_0_L2A",
            datetime(2025, 2, 3, tzinfo=timezone.utc),
            1.0,
            [23.90, 41.70, 24.66, 42.20],
            adjacent_geom,
        ),
        FakeItem(
            "S2B_35TLG_20250916_1_L2A",
            datetime(2025, 9, 16, tzinfo=timezone.utc),
            1.0,
            list(aoi),
            covering_geom,
        ),
    ]
    records = search_sentinel2(
        aoi,
        "2025-01-01",
        "2025-12-31",
        client_factory=_factory(items),
        min_footprint_overlap_pct=95.0,
    )
    assert [item["scene_id"] for item in records] == ["S2B_35TLG_20250916_1_L2A"]
    assert records[0]["footprint_overlap_pct"] == 100.0
    assert aoi_coverage_fraction(aoi, items[0].bbox) > 0
    assert footprint_overlap_pct(aoi, adjacent_geom) == 0.0


def test_aoi_coverage_from_bbox():
    coverage = aoi_coverage_fraction(
        (24.65, 42.05, 24.68, 42.08),
        [24.0, 41.0, 26.0, 43.0],
    )
    assert coverage == 100.0
    assert aoi_coverage_fraction((24.65, 42.05, 24.68, 42.08), [10, 10, 11, 11]) == 0.0
