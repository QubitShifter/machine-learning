from ml.validation.coverage import build_monthly_coverage, period_months


def test_period_months_include_leap_february():
    months = period_months("2024-01-01", "2024-03-31")
    assert months == ["2024-01", "2024-02", "2024-03"]


def test_empty_dataset_unknown_discovery_is_null_not_zero():
    coverage = build_monthly_coverage(
        period={"start": "2023-01-01", "end": "2023-03-31"},
        catalog_records=None,
        quality_scenes=[],
        catalog_known=False,
    )
    assert coverage["catalog_known"] is False
    assert [row["discovered_candidate_scenes"] for row in coverage["months"]] == [None, None, None]
    assert all(row["coverage_status"] == "unknown_discovery_evidence" for row in coverage["months"])
    assert coverage["summary"]["validated_observations"] == 0


def test_empty_catalog_search_is_no_scene_discovered():
    coverage = build_monthly_coverage(
        period={"start": "2023-01-01", "end": "2023-02-28"},
        catalog_records=[],
        quality_scenes=[],
        catalog_known=True,
    )
    assert coverage["months"][0]["discovered_candidate_scenes"] == 0
    assert coverage["months"][0]["coverage_status"] == "no_scene_discovered"


def test_leap_day_and_month_boundary_acquisitions():
    coverage = build_monthly_coverage(
        period={"start": "2024-02-01", "end": "2024-03-31"},
        catalog_records=[
            {"scene_id": "a", "acquisition_date": "2024-02-29", "status": "processed"},
            {"scene_id": "b", "acquisition_date": "2024-03-01", "status": "discovered"},
        ],
        quality_scenes=[
            {"scene_id": "a", "acquisition_date": "2024-02-29", "quality_status": "valid"},
        ],
        catalog_known=True,
    )
    by_month = {row["month"]: row for row in coverage["months"]}
    assert by_month["2024-02"]["validated_observations"] == 1
    assert by_month["2024-02"]["available_acquisition_dates"] == ["2024-02-29"]
    assert by_month["2024-03"]["coverage_status"] == "discovered_not_downloaded"
    assert by_month["2024-03"]["discovered_candidate_scenes"] == 1


def test_duplicates_and_mixed_statuses_in_one_month():
    coverage = build_monthly_coverage(
        period={"start": "2023-06-01", "end": "2023-06-30"},
        catalog_records=[
            {"scene_id": "ok", "acquisition_date": "2023-06-10", "status": "processed"},
            {"scene_id": "dup", "acquisition_date": "2023-06-10", "status": "processed"},
            {"scene_id": "rev", "acquisition_date": "2023-06-20", "status": "processed"},
            {"scene_id": "bad", "acquisition_date": "2023-06-25", "status": "processed"},
        ],
        quality_scenes=[
            {"scene_id": "ok", "acquisition_date": "2023-06-10", "quality_status": "valid"},
            {"scene_id": "dup", "acquisition_date": "2023-06-10", "quality_status": "valid"},
            {"scene_id": "rev", "acquisition_date": "2023-06-20", "quality_status": "requires_review"},
            {"scene_id": "bad", "acquisition_date": "2023-06-25", "quality_status": "rejected"},
        ],
        catalog_known=True,
    )
    row = coverage["months"][0]
    assert row["validated_observations"] == 2
    assert row["requires_review"] == 1
    assert row["rejected"] == 1
    assert row["coverage_status"] == "validated_observation"
    assert coverage["summary"]["acquisition_dates"] == ["2023-06-10"]
    assert coverage["summary"]["maximum_interval_days"] is None


def test_missing_months_and_gap_statistics():
    coverage = build_monthly_coverage(
        period={"start": "2023-01-01", "end": "2023-06-30"},
        catalog_records=[
            {"scene_id": "jan", "acquisition_date": "2023-01-31", "status": "processed"},
            {"scene_id": "jun", "acquisition_date": "2023-06-01", "status": "processed"},
        ],
        quality_scenes=[
            {"scene_id": "jan", "acquisition_date": "2023-01-31", "quality_status": "valid"},
            {"scene_id": "jun", "acquisition_date": "2023-06-01", "quality_status": "valid"},
        ],
        catalog_known=True,
    )
    assert coverage["summary"]["months_with_validated_observation"] == 2
    assert coverage["summary"]["longest_observation_gap_days"] == 121
    assert coverage["summary"]["consecutive_months_without_validated_observation"][0]["months"] == 4
    assert coverage["summary"]["observations_by_season"]["DJF"] == 1
