from datetime import date, timedelta

from ml.integration.satellite_weather import (
    historical_weather_features,
    integrate_satellite_weather,
    prior_window_dates,
)


def _weather(start: str, days: int, rain: float = 0.0, temp: float = 10.0) -> list[dict]:
    first = date.fromisoformat(start)
    rows = []
    for offset in range(days):
        day = first + timedelta(days=offset)
        precip = rain
        if isinstance(rain, list):
            precip = rain[offset]
        rows.append({
            "date_utc": day.isoformat(),
            "temperature_mean_c": temp,
            "relative_humidity_mean_pct": 50.0,
            "wind_speed_mean_ms": 2.0,
            "precipitation_total_mm": precip,
            "evaporation_total_mm": 0.5,
            "source_grid_id": "42.1,24.7",
        })
    return rows


def test_previous_windows_exclude_observation_and_future_days():
    weather = _weather("2025-03-22", 40, rain=1.0)
    weather_by_date = {row["date_utc"]: row for row in weather}
    weather_by_date["2025-04-20"]["precipitation_total_mm"] = 50.0
    weather_by_date["2025-04-21"]["precipitation_total_mm"] = 80.0
    weather_by_date["2025-04-22"]["precipitation_total_mm"] = 90.0
    features = historical_weather_features(
        weather_by_date,
        date(2025, 4, 21),
    )
    assert prior_window_dates(date(2025, 4, 21), 7)[0] == date(2025, 4, 14)
    assert prior_window_dates(date(2025, 4, 21), 7)[-1] == date(2025, 4, 20)
    assert features["window_7d_start_utc"] == "2025-04-14"
    assert features["window_7d_end_utc"] == "2025-04-20"
    assert features["precip_prev_7d_mm"] == 6.0 + 50.0
    assert features["precip_prev_7d_mm"] != 6.0 + 50.0 + 80.0
    assert features["window_7d_complete"] is True
    assert features["window_7d_expected_days"] == 7
    assert features["window_7d_observed_days"] == 7
    assert features["window_30d_complete"] is True
    assert features["temp_mean_prev_7d_c"] == 10.0
    assert features["dry_days_prev_30d"] == 0
    assert features["evap_prev_7d_mm"] == 3.5


def test_fourteen_and_thirty_day_window_alignment():
    weather = _weather("2025-03-01", 60, rain=2.0)
    features = historical_weather_features(
        {row["date_utc"]: row for row in weather},
        date(2025, 4, 21),
    )
    assert features["window_14d_start_utc"] == "2025-04-07"
    assert features["window_14d_end_utc"] == "2025-04-20"
    assert features["window_30d_start_utc"] == "2025-03-22"
    assert features["window_30d_end_utc"] == "2025-04-20"
    assert features["precip_prev_14d_mm"] == 28.0
    assert features["precip_prev_30d_mm"] == 60.0
    assert features["window_14d_expected_days"] == 14
    assert features["window_30d_expected_days"] == 30


def test_utc_leap_day_is_included_in_prior_window():
    weather = _weather("2024-02-01", 40, rain=1.0)
    features = historical_weather_features(
        {row["date_utc"]: row for row in weather},
        date(2024, 3, 1),
    )
    assert date(2024, 2, 29) in prior_window_dates(date(2024, 3, 1), 7)
    assert features["window_7d_start_utc"] == "2024-02-23"
    assert features["window_7d_end_utc"] == "2024-02-29"
    assert features["precip_prev_7d_mm"] == 7.0


def test_first_day_of_month_uses_previous_month_days():
    weather = _weather("2024-03-01", 40, rain=3.0)
    features = historical_weather_features(
        {row["date_utc"]: row for row in weather},
        date(2024, 4, 1),
    )
    assert features["window_7d_start_utc"] == "2024-03-25"
    assert features["window_7d_end_utc"] == "2024-03-31"
    assert features["precip_prev_7d_mm"] == 21.0


def test_near_midnight_uses_utc_calendar_date_not_invented_cutoff():
    weather = _weather("2024-04-01", 20, rain=1.0)
    weather_by_date = {row["date_utc"]: row for row in weather}
    weather_by_date["2024-04-11"]["precipitation_total_mm"] = 50.0
    weather = list(weather_by_date.values())
    early = integrate_satellite_weather(
        weather,
        [{"scene_id": "MIDNIGHT", "date": "2024-04-12T00:05:00Z", "mean": 0.4}],
        weather_dataset_id="weather",
        satellite_dataset_id="sat",
        aoi_id="plovdiv_test",
    )[0]
    late_previous = integrate_satellite_weather(
        weather,
        [{"scene_id": "PREV", "date": "2024-04-11T23:55:00Z", "mean": 0.4}],
        weather_dataset_id="weather",
        satellite_dataset_id="sat",
        aoi_id="plovdiv_test",
    )[0]
    assert early["observation_date_utc"] == "2024-04-12"
    assert early["acquisition_time_precision"] == "utc_datetime"
    assert early["window_7d_start_utc"] == "2024-04-05"
    assert early["window_7d_end_utc"] == "2024-04-11"
    assert late_previous["observation_date_utc"] == "2024-04-11"
    assert late_previous["window_7d_end_utc"] == "2024-04-10"
    assert early["precip_prev_7d_mm"] != late_previous["precip_prev_7d_mm"]


def test_missing_weather_days_are_not_zero_filled():
    weather = _weather("2025-04-10", 7, rain=2.0)
    features = historical_weather_features(
        {row["date_utc"]: row for row in weather},
        date(2025, 4, 21),
    )
    assert features["precip_prev_7d_mm"] is None
    assert features["window_7d_complete"] is False
    assert features["window_7d_available_days"] == 3
    assert features["window_7d_observed_days"] == 3
    assert features["window_7d_expected_days"] == 7
    assert features["window_7d_missing_days"] == 4


def test_missing_monthly_source_status_is_not_usable():
    weather = _weather("2025-04-01", 30, rain=1.0)
    for row in weather:
        if row["date_utc"] >= "2025-04-10":
            row["quality_status"] = "missing"
            row["precipitation_total_mm"] = None
            row["hourly_records_available"] = 0
            row["boundary_00utc_available"] = False
    features = historical_weather_features(
        {row["date_utc"]: row for row in weather},
        date(2025, 4, 21),
    )
    assert features["precip_prev_7d_mm"] is None
    assert features["window_7d_complete"] is False
    assert features["window_7d_observed_days"] == 0


def test_incomplete_hours_do_not_count_as_completed_days():
    weather = _weather("2025-04-01", 30, rain=1.0)
    weather_by_date = {row["date_utc"]: row for row in weather}
    weather_by_date["2025-04-18"]["hourly_records_available"] = 12
    features = historical_weather_features(weather_by_date, date(2025, 4, 21))
    assert features["precip_prev_7d_mm"] is None
    assert features["window_7d_observed_days"] == 6


def test_dry_days_keep_same_calendar_date_distinct_scenes():
    rains = [0.0] * 20 + [0.4] * 5 + [2.0] * 5
    weather = _weather("2025-03-22", 30, rain=rains)
    rows = integrate_satellite_weather(
        weather,
        [
            {"scene_id": "A", "date": "2025-04-21T09:18:47Z", "mean": 0.4, "quality_status": "valid"},
            {"scene_id": "B", "date": "2025-04-21", "mean": 0.9, "quality_status": "valid"},
            {"scene_id": "C", "date": "2025-04-22", "mean": 0.5, "quality_status": "valid"},
        ],
        weather_dataset_id="weather",
        satellite_dataset_id="sat",
        aoi_id="plovdiv_test",
    )
    assert [row["scene_id"] for row in rows] == ["A", "B", "C"]
    first = rows[0]
    assert first["observation_date_utc"] == "2025-04-21"
    assert first["dry_days_prev_30d"] == 25
    assert first["precip_prev_30d_mm"] == sum(rains)
    assert first["ndvi_mean"] == 0.4
    assert first["satellite_observation_valid"] is True
    assert first["weather_feature_window_complete"] is True
    assert first["suitable_for_modeling"] is False


def test_duplicate_scene_ids_keep_first_occurrence():
    weather = _weather("2025-03-22", 30, rain=1.0)
    dropped: list[str] = []
    rows = integrate_satellite_weather(
        weather,
        [
            {"scene_id": "A", "date": "2025-04-21", "mean": 0.4},
            {"scene_id": "A", "date": "2025-04-21", "mean": 0.9},
        ],
        weather_dataset_id="weather",
        satellite_dataset_id="sat",
        aoi_id="plovdiv_test",
        duplicate_scene_ids=dropped,
    )
    assert len(rows) == 1
    assert rows[0]["ndvi_mean"] == 0.4
    assert dropped == ["A"]


def test_satellite_without_weather_match_stays_missing():
    rows = integrate_satellite_weather(
        [],
        [{"scene_id": "A", "date": "2025-04-21", "mean": 0.4}],
        weather_dataset_id="weather",
        satellite_dataset_id="sat",
        aoi_id="plovdiv_test",
    )
    assert rows[0]["precip_prev_7d_mm"] is None
    assert rows[0]["window_7d_complete"] is False
    assert rows[0]["satellite_observation_valid"] is True
    assert rows[0]["integrated_observation_complete"] is False
    assert "missing_weather_window_7d" in rows[0]["quality_warnings"]


def test_missing_timestamp_keeps_the_scene():
    rows = integrate_satellite_weather(
        _weather("2025-04-01", 10, rain=1.0),
        [{"scene_id": "NO_DATE", "mean": 0.3, "quality_status": "valid"}],
        weather_dataset_id="weather",
        satellite_dataset_id="sat",
        aoi_id="plovdiv_test",
    )
    assert len(rows) == 1
    assert rows[0]["scene_id"] == "NO_DATE"
    assert rows[0]["observation_date_utc"] is None
    assert rows[0]["precip_prev_7d_mm"] is None
    assert rows[0]["satellite_observation_valid"] is False


def test_quality_status_warning_does_not_zero_fill_future_rain():
    weather = _weather("2025-03-22", 40, rain=1.0)
    weather_by_date = {row["date_utc"]: row for row in weather}
    weather_by_date["2025-04-21"]["precipitation_total_mm"] = 100.0
    features = historical_weather_features(weather_by_date, date(2025, 4, 21))
    assert features["precip_prev_7d_mm"] == 7.0
    assert features["precip_prev_14d_mm"] == 14.0
    assert features["precip_prev_30d_mm"] == 30.0
