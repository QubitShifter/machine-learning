from pathlib import Path

from ml.analysis.timeseries import build_ndvi_timeseries, write_timeseries_outputs


def _obs(date, mean, scene="scene", valid=90.0, coverage=100.0, valid_pixels=10):
    return {
        "scene_id": scene,
        "date": date,
        "mean": mean,
        "median": mean,
        "standard_deviation": 0.1,
        "minimum": None if mean is None else mean - 0.1,
        "maximum": None if mean is None else mean + 0.1,
        "valid_pixels": valid_pixels,
        "valid_percentage": valid,
        "cloud_cover": 1.0,
        "aoi_coverage": coverage,
    }


def test_chronological_order_and_changes():
    payload = build_ndvi_timeseries([
        _obs("2025-09-16", 0.59, "late"),
        _obs("2025-03-19", 0.34, "early"),
    ])
    assert [item["date"] for item in payload["observations"]] == [
        "2025-03-19",
        "2025-09-16",
    ]
    change = payload["consecutive_changes"][0]
    assert round(change["absolute_change"], 2) == 0.25
    assert change["direction"] == "increase"


def test_duplicate_dates_keep_higher_quality():
    payload = build_ndvi_timeseries([
        _obs("2025-09-16", 0.10, "cloudy", valid=40.0),
        _obs("2025-09-16", 0.58, "clear", valid=90.0),
    ])
    assert len(payload["observations"]) == 1
    assert payload["observations"][0]["scene_id"] == "clear"


def test_missing_months_are_listed_not_filled():
    payload = build_ndvi_timeseries([
        _obs("2025-01-15", 0.18),
        _obs("2025-03-19", 0.34),
    ])
    assert "2025-02" in payload["missing_months"]
    assert all(item["month"] != "2025-02" for item in payload["monthly"])


def test_zero_valid_pixels_and_partial_coverage():
    payload = build_ndvi_timeseries([
        _obs("2025-01-15", None, valid_pixels=0, valid=0.0, coverage=40.0),
        _obs("2025-03-19", 0.34, coverage=60.0),
    ])
    assert payload["quality"]["zero_valid_pixel_observations"] == 1
    assert payload["observations"][1]["partial_coverage"] is True


def test_monthly_and_yearly_aggregation():
    payload = build_ndvi_timeseries([
        _obs("2023-01-15", 0.20, "a"),
        _obs("2023-01-28", 0.30, "b"),
        _obs("2024-01-16", 0.40, "c"),
        _obs("2024-07-01", 0.70, "d"),
    ], deduplicate_by_date=False)
    january = next(item for item in payload["monthly"] if item["month"] == "2023-01")
    assert january["observation_count"] == 2
    assert round(january["mean"], 2) == 0.25
    year_2024 = next(item for item in payload["yearly"] if item["year"] == "2024")
    assert year_2024["annual_maximum_observed"] == 0.70
    january_compare = next(
        item for item in payload["comparison"]["months"]
        if item["calendar_month"] == "01"
    )
    assert january_compare["years"]["2023"]["mean"] == 0.25
    assert january_compare["years"]["2024"]["mean"] == 0.40


def test_unvalidated_scenes_can_be_excluded():
    payload = build_ndvi_timeseries(
        [
            _obs("2023-01-15", 0.20, "keep"),
            _obs("2023-02-15", 0.90, "drop"),
        ],
        validated_scene_ids={"keep"},
    )
    assert [item["scene_id"] for item in payload["observations"]] == ["keep"]


def test_empty_dataset():
    payload = build_ndvi_timeseries([])
    assert payload["observation_count"] == 0
    assert payload["monthly"] == []
    assert payload["yearly"] == []


def test_json_and_csv_output(tmp_path: Path):
    payload = build_ndvi_timeseries([
        _obs("2025-01-15", 0.18),
        _obs("2025-03-19", 0.34),
    ])
    files = write_timeseries_outputs(payload, tmp_path)
    assert (tmp_path / files["json"]).is_file()
    assert (tmp_path / files["csv"]).is_file()
    assert (tmp_path / files["png"]).is_file()
    csv_text = (tmp_path / files["csv"]).read_text(encoding="utf-8")
    assert "2025-01-15" in csv_text
    assert ",0.0," not in csv_text.splitlines()[1] or "0.18" in csv_text
