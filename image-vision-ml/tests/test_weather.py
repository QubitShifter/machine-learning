import warnings
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest

from ml.analysis.weather_timeseries import (
    monthly_weather_summary,
    write_daily_weather,
    write_weather_chart,
)

from ml.ingestion.era5_land import (
    build_boundary_request,
    build_era5_land_request,
    cds_auth_status,
    cds_retrieval_area,
    month_days,
    partition_months,
    study_aoi_bbox,
)
from ml.ingestion.weather_config import load_weather_config, validate_weather_config
from ml.preprocessing.errors import WeatherConfigError
from ml.preprocessing.weather import (
    EVAPORATION_SIGN,
    ROLE_BOUNDARY,
    ROLE_OBSERVATION,
    aoi_centroid,
    aggregate_daily_weather,
    convert_evaporation_mm,
    era5_land_daily_total_mm,
    era5_land_grid_points,
    era5_land_hourly_increments,
    kelvin_to_celsius,
    meters_to_mm,
    nearest_era5_land_cell,
    reconcile_hourly_records,
    relative_humidity_pct,
    retrieval_area_has_grid_points,
    wind_speed,
)
from ml.validation.weather_quality import (
    build_quality_report,
    evaluate_daily_rows,
    evaluate_hourly_records,
)


def _config(**overrides):
    payload = {
        "dataset_id": "plovdiv_weather_test",
        "source": {"dataset": "reanalysis-era5-land"},
        "area": {"name": "plovdiv_test", "bbox": [24.65, 42.05, 24.68, 42.08]},
        "period": {"start": "2025-04-01", "end": "2025-04-03"},
        "variables": [
            "2m_temperature",
            "2m_dewpoint_temperature",
            "total_precipitation",
            "10m_u_component_of_wind",
            "10m_v_component_of_wind",
            "total_evaporation",
        ],
    }
    payload.update(overrides)
    return validate_weather_config(payload)


def test_unit_conversions():
    assert float(kelvin_to_celsius(273.15)) == pytest.approx(0.0)
    assert float(meters_to_mm(0.004)) == pytest.approx(4.0)
    assert float(wind_speed(3.0, 4.0)) == pytest.approx(5.0)
    humidity = float(relative_humidity_pct(20.0, 20.0))
    assert humidity == pytest.approx(100.0)
    cooler = float(relative_humidity_pct(20.0, 10.0))
    assert 0.0 < cooler < 100.0
    assert EVAPORATION_SIGN == -1.0
    assert float(convert_evaporation_mm(-0.003)) == pytest.approx(3.0)


def test_relative_humidity_keeps_large_impossibilities():
    too_high = float(relative_humidity_pct(10.0, 20.0))
    assert too_high > 100.05


def test_hourly_increments_do_not_sum_cumulatives():
    increments = era5_land_hourly_increments([0.001, 0.003, 0.004])
    assert [round(value, 6) for value in increments] == [0.001, 0.002, 0.001]
    assert sum(increments) == pytest.approx(0.004)


def test_forecast_reset_starts_new_cycle():
    increments = era5_land_hourly_increments([0.004, 0.001, 0.002])
    assert increments[0] == pytest.approx(0.004)
    assert increments[1] == pytest.approx(0.001)
    assert increments[2] == pytest.approx(0.001)


def test_daily_total_uses_next_day_00utc():
    total, method = era5_land_daily_total_mm(0.004)
    assert method == "next_day_00utc"
    assert total == pytest.approx(4.0)
    naive_sum = meters_to_mm(0.001 + 0.003 + 0.004)
    assert naive_sum == pytest.approx(8.0)
    assert total != naive_sum


def test_missing_boundary_is_not_zero_filled():
    total, method = era5_land_daily_total_mm(None)
    assert total is None
    assert method == "missing_boundary"


def test_negative_increment_artifact_is_preserved():
    increments = era5_land_hourly_increments([0.002, 0.002 - 1e-8])
    assert increments[1] == pytest.approx(-1e-8)


def test_leap_year_month_partition_and_days():
    months = partition_months("2023-11-11", "2024-02-03")
    assert months == ["2023-11", "2023-12", "2024-01", "2024-02"]
    assert "29" in month_days(2024, 2)
    assert "29" not in month_days(2025, 2)
    assert len(month_days(2024, 2)) == 29


def test_cds_request_uses_current_schema():
    request = build_era5_land_request(_config(), year=2025, month=4)
    assert request["variable"][0] == "2m_temperature"
    assert request["year"] == ["2025"]
    assert request["month"] == ["04"]
    assert request["day"][0] == "01"
    assert request["day"][-1] == "30"
    assert request["time"][0] == "00:00"
    assert request["data_format"] == "netcdf"
    assert request["area"] != [42.08, 24.65, 42.05, 24.68]
    assert retrieval_area_has_grid_points(request["area"])
    boundary = build_boundary_request(_config(), 2025, 4)
    assert boundary["year"] == ["2025"]
    assert boundary["month"] == ["05"]
    assert boundary["day"] == ["01"]
    assert boundary["time"] == ["00:00"]
    assert boundary["area"] == request["area"]


def test_weather_config_file_and_rejects_unknown_variable():
    config = load_weather_config(Path("configs/weather_era5_land.yaml"))
    assert config["dataset_id"] == "plovdiv_weather_2023_2025"
    assert config["area"]["bbox"] == (24.65, 42.05, 24.68, 42.08)
    assert list(config["spatial"]["retrieval_area"]) == [42.20, 24.50, 41.90, 24.90]
    with pytest.raises(WeatherConfigError):
        validate_weather_config({
            "dataset_id": "bad",
            "area": {"bbox": [24.65, 42.05, 24.68, 42.08]},
            "period": {"start": "2025-01-01", "end": "2025-01-31"},
            "variables": ["soil_temperature_level_1"],
        })


def test_study_aoi_is_not_used_as_cds_crop():
    config = load_weather_config(Path("configs/weather_era5_land.yaml"))
    assert study_aoi_bbox(config) == [24.65, 42.05, 24.68, 42.08]
    assert cds_retrieval_area(config) == [42.20, 24.50, 41.90, 24.90]
    tiny = [42.08, 24.65, 42.05, 24.68]
    assert not retrieval_area_has_grid_points(tiny)
    assert retrieval_area_has_grid_points(cds_retrieval_area(config))
    longitudes, latitudes = era5_land_grid_points(cds_retrieval_area(config))
    assert 24.7 in longitudes
    assert 42.1 in latitudes
    request = build_era5_land_request(config, year=2025, month=4)
    boundary = build_boundary_request(config, 2025, 4)
    assert request["area"] == [42.20, 24.50, 41.90, 24.90]
    assert boundary["area"] == [42.20, 24.50, 41.90, 24.90]
    with pytest.raises(WeatherConfigError):
        validate_weather_config({
            "dataset_id": "too_small",
            "area": {"bbox": [24.65, 42.05, 24.68, 42.08]},
            "period": {"start": "2025-04-01", "end": "2025-04-30"},
            "variables": [
                "2m_temperature",
                "2m_dewpoint_temperature",
                "total_precipitation",
                "10m_u_component_of_wind",
                "10m_v_component_of_wind",
                "total_evaporation",
            ],
            "spatial": {"retrieval_area": tiny},
        })


def test_nearest_cell_uses_study_aoi_not_retrieval_centroid():
    study = aoi_centroid((24.65, 42.05, 24.68, 42.08))
    retrieval = aoi_centroid((24.50, 41.90, 24.90, 42.20))
    longitudes = [24.5, 24.6, 24.7, 24.8, 24.9]
    latitudes = [41.9, 42.0, 42.1, 42.2]
    from_study = nearest_era5_land_cell(study[0], study[1], longitudes, latitudes)
    from_box = nearest_era5_land_cell(retrieval[0], retrieval[1], longitudes, latitudes)
    assert study == pytest.approx((24.665, 42.065))
    assert from_study["source_longitude"] == pytest.approx(24.7)
    assert from_study["source_latitude"] == pytest.approx(42.1)
    assert from_study["query_longitude"] == pytest.approx(study[0])
    assert from_study["query_latitude"] == pytest.approx(study[1])
    assert (
        from_study["source_latitude"] != from_box["source_latitude"]
        or from_study["source_longitude"] != from_box["source_longitude"]
        or from_study["query_latitude"] != from_box["query_latitude"]
    )


def test_cds_auth_status_does_not_expose_secrets(tmp_path: Path):
    path = tmp_path / ".cdsapirc"
    path.write_text(
        "url: https://cds.climate.copernicus.eu/api\nkey: SUPER_SECRET_TOKEN\n",
        encoding="utf-8",
    )
    status = cds_auth_status(path)
    assert status["configured"] is True
    assert status["key_present"] is True
    assert "SUPER_SECRET_TOKEN" not in str(status)
    missing = cds_auth_status(tmp_path / "missing")
    assert missing["configured"] is False


def test_nearest_grid_cell_keeps_native_resolution():
    west, south, east, north = 24.65, 42.05, 24.68, 42.08
    lon, lat = aoi_centroid((west, south, east, north))
    spatial = nearest_era5_land_cell(lon, lat, [24.6, 24.7], [42.0, 42.1])
    assert spatial["method"] == "nearest_grid_cell"
    assert spatial["native_resolution_deg"] == 0.1
    assert spatial["source_longitude"] == pytest.approx(24.7)
    assert spatial["source_latitude"] == pytest.approx(42.1)


def _hour(day: str, hour: int, **fields) -> dict:
    stamp = datetime.fromisoformat(f"{day}T{hour:02d}:00:00").replace(tzinfo=timezone.utc)
    record = {
        "timestamp_utc": stamp.isoformat().replace("+00:00", "Z"),
        "t2m": 283.15,
        "d2m": 278.15,
        "u10": 3.0,
        "v10": 4.0,
        "tp": 0.0,
        "e": 0.0,
    }
    record.update(fields)
    return record


def test_daily_temperature_and_wind_and_humidity():
    hours = [_hour("2025-04-01", hour, t2m=273.15 + hour) for hour in range(24)]
    hours.append(_hour("2025-04-02", 0, tp=0.005, e=-0.002))
    rows = aggregate_daily_weather(
        hours,
        period_start=datetime(2025, 4, 1).date(),
        period_end=datetime(2025, 4, 1).date(),
        aoi_id="plovdiv_test",
        spatial={"source_latitude": 42.1, "source_longitude": 24.7},
    )
    row = rows[0]
    assert row["temperature_min_c"] == pytest.approx(0.0)
    assert row["temperature_max_c"] == pytest.approx(23.0)
    assert row["temperature_mean_c"] == pytest.approx(11.5)
    assert row["wind_speed_mean_ms"] == pytest.approx(5.0)
    assert row["precipitation_total_mm"] == pytest.approx(5.0)
    assert row["precipitation_method"] == "next_day_00utc"
    assert row["evaporation_total_mm"] == pytest.approx(2.0)
    assert row["quality_status"] == "valid"
    assert 0.0 < row["relative_humidity_mean_pct"] <= 100.0


def test_incomplete_and_leap_day_rows_are_not_fabricated():
    hours = [_hour("2024-02-29", 12, t2m=280.15)]
    rows = aggregate_daily_weather(
        hours,
        period_start=datetime(2024, 2, 28).date(),
        period_end=datetime(2024, 3, 1).date(),
        aoi_id="plovdiv_test",
        spatial={"source_latitude": 42.1, "source_longitude": 24.7},
    )
    assert [row["date_utc"] for row in rows] == ["2024-02-28", "2024-02-29", "2024-03-01"]
    assert rows[0]["temperature_mean_c"] is None
    assert rows[0]["precipitation_total_mm"] is None
    assert rows[1]["hourly_records_available"] == 1
    assert rows[1]["quality_status"] == "requires_review"


def test_duplicate_hourly_timestamps_are_detected():
    hours = [_hour("2025-04-01", 0), _hour("2025-04-01", 0)]
    report = evaluate_hourly_records(hours)
    assert report["status"] == "rejected"
    assert any(issue["code"] == "duplicate_timestamps" for issue in report["issues"])


def test_quality_flags_negative_rainfall_and_missing_boundary():
    rows = aggregate_daily_weather(
        [_hour("2025-04-01", hour) for hour in range(24)],
        period_start=datetime(2025, 4, 1).date(),
        period_end=datetime(2025, 4, 1).date(),
        aoi_id="plovdiv_test",
        spatial={"source_latitude": 42.1, "source_longitude": 24.7},
    )
    rows[0]["precipitation_total_mm"] = -1.2
    evaluated = evaluate_daily_rows(rows)
    assert evaluated["days"][0]["quality_status"] == "requires_review"
    assert "negative_precipitation" in evaluated["days"][0]["quality_reasons"]
    assert "daily_total_without_boundary" in evaluated["days"][0]["quality_reasons"]


def test_expected_01utc_forecast_cycle_is_not_a_warning():
    hours = []
    # Matches the live April pattern: 00:00 is the previous day's total,
    # 01:00 starts a new accumulation, next 00:00 is the daily total.
    hours.append(_hour("2025-04-01", 0, tp=0.0101296, e=-0.0014842))
    hours.append(_hour("2025-04-01", 1, tp=0.0005594, e=0.0000002))
    hours.append(_hour("2025-04-01", 2, tp=0.0014775, e=-0.0000020))
    hours.append(_hour("2025-04-01", 23, tp=0.0179999, e=-0.0005684))
    hours.append(_hour("2025-04-02", 0, tp=0.0188420, e=-0.0005696))
    hours.append(_hour("2025-04-02", 1, tp=0.0008458, e=-0.0000019))
    hours.append(_hour("2025-04-02", 23, tp=0.0150000, e=-0.0007000))
    hours.append(_hour("2025-04-03", 0, tp=0.0151219, e=-0.0007011))
    hours.append(_hour("2025-04-03", 1, tp=0.0, e=0.0000007))
    report = evaluate_hourly_records(hours)
    assert report["accumulation"]["forecast_cycle_resets"] == 3
    assert report["accumulation"]["unexpected_resets"] == 0
    assert report["status"] == "valid"
    assert not any(issue["code"] == "accumulation_resets" for issue in report["issues"])
    assert not any(
        issue["code"] == "unexpected_accumulation_resets" for issue in report["issues"]
    )
    total, method = era5_land_daily_total_mm(0.0188420)
    assert method == "next_day_00utc"
    assert total == pytest.approx(18.8420)
    evap = float(convert_evaporation_mm(-0.0005696))
    assert evap == pytest.approx(0.5696)


def test_unexpected_midday_accumulation_reset_still_warns():
    hours = [
        _hour("2025-04-01", 10, tp=0.004),
        _hour("2025-04-01", 11, tp=0.006),
        _hour("2025-04-01", 12, tp=0.001),
    ]
    report = evaluate_hourly_records(hours)
    assert report["accumulation"]["unexpected_resets"] == 1
    assert report["accumulation"]["forecast_cycle_resets"] == 0
    assert report["status"] == "warning"
    assert any(
        issue["code"] == "unexpected_accumulation_resets" for issue in report["issues"]
    )


def test_live_like_daily_total_and_monthly_sum():
    day1 = 0.018842030316591263
    day2 = 0.01512195449322462
    hours = []
    running = 0.0
    hours.append(_hour("2025-04-01", 0, tp=0.0101296, e=-0.0014842))
    for hour in range(1, 24):
        running = day1 * hour / 24.0
        hours.append(_hour("2025-04-01", hour, tp=running, e=-running * 0.03))
    hours.append(_hour("2025-04-02", 0, tp=day1, e=-0.0005695857107639313))
    running = 0.0
    hours.append(_hour("2025-04-02", 1, tp=0.0008458, e=-0.00000186))
    for hour in range(2, 24):
        running = day2 * hour / 24.0
        hours.append(_hour("2025-04-02", hour, tp=running, e=-running * 0.05))
    hours.append(_hour("2025-04-03", 0, tp=day2, e=-0.0007011378183960915))
    rows = aggregate_daily_weather(
        hours,
        period_start=datetime(2025, 4, 1).date(),
        period_end=datetime(2025, 4, 2).date(),
        aoi_id="plovdiv_test",
        spatial={"source_latitude": 42.1, "source_longitude": 24.7},
    )
    assert rows[0]["precipitation_total_mm"] == pytest.approx(18.842030316591263)
    assert rows[1]["precipitation_total_mm"] == pytest.approx(15.12195449322462)
    assert rows[0]["evaporation_total_mm"] == pytest.approx(0.5695857107639313)
    assert rows[1]["evaporation_total_mm"] == pytest.approx(0.7011378183960915)
    assert rows[0]["precipitation_method"] == "next_day_00utc"
    hourly = evaluate_hourly_records(hours)
    assert hourly["status"] == "valid"
    assert hourly["accumulation"]["forecast_cycle_resets"] >= 1
    assert hourly["accumulation"]["unexpected_resets"] == 0


def test_weather_chart_uses_dates_and_csv_does_not_need_parquet(tmp_path: Path):
    rows = [
        {
            "date_utc": "2025-04-01",
            "temperature_mean_c": 8.4,
            "precipitation_total_mm": 18.8,
            "aoi_id": "plovdiv_test",
            "quality_status": "valid",
        },
        {
            "date_utc": "2025-04-02",
            "temperature_mean_c": 8.3,
            "precipitation_total_mm": 15.1,
            "aoi_id": "plovdiv_test",
            "quality_status": "valid",
        },
    ]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        write_weather_chart(rows, tmp_path / "weather_timeseries.png")
    categorical = [
        str(item.message)
        for item in caught
        if "categorical" in str(item.message).lower()
        or "units" in str(item.message).lower()
    ]
    assert categorical == []
    assert (tmp_path / "weather_timeseries.png").is_file()
    outputs = write_daily_weather(rows, tmp_path)
    assert outputs["daily_csv"] == "daily_weather.csv"
    assert (tmp_path / "daily_weather.csv").is_file()


def _tagged_hour(day: str, hour: int, *, role: str, source_month: str, **fields) -> dict:
    record = _hour(day, hour, **fields)
    record["record_role"] = role
    record["source_month"] = source_month
    record["source_file"] = (
        f"{source_month}.boundary.json" if role == ROLE_BOUNDARY else f"{source_month}.json"
    )
    record["source_longitude"] = 24.7
    record["source_latitude"] = 42.1
    return record


def _complete_month_hours(
    year: int,
    month: int,
    *,
    rain_m: float = 0.002,
    evap_m: float = -0.001,
    previous_close: tuple[float, float] | None = None,
    include_closing_boundary: bool = True,
) -> tuple[list[dict], tuple[float, float]]:
    source_month = f"{year}-{month:02d}"
    days = monthrange(year, month)[1]
    hours = []
    for day in range(1, days + 1):
        for hour in range(24):
            if day == 1 and hour == 0 and previous_close is not None:
                tp, evap = previous_close
            else:
                tp = rain_m * ((hour or 24) / 24.0)
                evap = evap_m * ((hour or 24) / 24.0)
            hours.append(_tagged_hour(
                f"{year}-{month:02d}-{day:02d}",
                hour,
                role=ROLE_OBSERVATION,
                source_month=source_month,
                tp=tp,
                e=evap,
            ))
    if include_closing_boundary:
        next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
        hours.append(_tagged_hour(
            f"{next_year}-{next_month:02d}-01",
            0,
            role=ROLE_BOUNDARY,
            source_month=source_month,
            tp=rain_m,
            e=evap_m,
        ))
    return hours, (rain_m, evap_m)


def test_matching_boundary_overlap_is_reconciled():
    january, close = _complete_month_hours(2023, 1, rain_m=0.004, evap_m=-0.002)
    february, _ = _complete_month_hours(
        2023,
        2,
        rain_m=0.003,
        evap_m=-0.0015,
        previous_close=close,
    )
    merged = reconcile_hourly_records(
        january + february,
        downloaded_months=["2023-01", "2023-02"],
    )
    stamps = [
        item["timestamp_utc"]
        for item in merged["records"]
        if item["timestamp_utc"].startswith("2023-02-01T00:00")
    ]
    assert len(stamps) == 1
    assert merged["overlaps"]
    assert merged["overlaps"][0]["status"] == "reconciled"
    assert merged["conflicts"] == []
    hourly = evaluate_hourly_records(merged["records"])
    assert hourly["status"] == "valid"
    assert not any(issue["code"] == "duplicate_timestamps" for issue in hourly["issues"])
    rows = aggregate_daily_weather(
        merged["records"],
        period_start=date(2023, 1, 31),
        period_end=date(2023, 2, 1),
        aoi_id="plovdiv_test",
        spatial={"source_latitude": 42.1, "source_longitude": 24.7},
    )
    assert rows[0]["precipitation_total_mm"] == pytest.approx(4.0)
    assert rows[0]["evaporation_total_mm"] == pytest.approx(2.0)
    assert rows[0]["quality_status"] == "valid"
    assert rows[1]["hourly_records_available"] == 24


def test_conflicting_boundary_values_require_review():
    observation = _tagged_hour(
        "2023-02-01",
        0,
        role=ROLE_OBSERVATION,
        source_month="2023-02",
        tp=0.004,
        e=-0.002,
    )
    boundary = _tagged_hour(
        "2023-02-01",
        0,
        role=ROLE_BOUNDARY,
        source_month="2023-01",
        tp=0.009,
        e=-0.003,
    )
    merged = reconcile_hourly_records(
        [observation, boundary],
        downloaded_months=["2023-01", "2023-02"],
    )
    assert len(merged["records"]) == 1
    assert merged["records"][0]["tp"] == pytest.approx(0.004)
    assert merged["conflicts"]
    assert merged["conflicts"][0]["status"] == "requires_review"
    assert merged["conflicts"][0]["values"]["tp"] == [pytest.approx(0.004), pytest.approx(0.009)]
    assert merged["overlaps"] == []


def test_unexpected_internal_duplicates_remain_rejected():
    hours = [
        _tagged_hour("2025-04-01", 0, role=ROLE_OBSERVATION, source_month="2025-04"),
        _tagged_hour("2025-04-01", 0, role=ROLE_OBSERVATION, source_month="2025-04"),
    ]
    merged = reconcile_hourly_records(hours, downloaded_months=["2025-04"])
    assert len(merged["records"]) == 2
    assert merged["unexpected_duplicates"]
    report = evaluate_hourly_records(merged["records"])
    assert report["status"] == "rejected"
    assert any(issue["code"] == "duplicate_timestamps" for issue in report["issues"])


def test_boundary_only_does_not_populate_missing_month():
    march, _ = _complete_month_hours(2023, 3, rain_m=0.0, evap_m=-0.0020056236535310745)
    april, _ = _complete_month_hours(2025, 4, rain_m=0.0, evap_m=-0.003766368143260479)
    merged = reconcile_hourly_records(
        march + april,
        downloaded_months=["2023-03", "2025-04"],
    )
    assert "2023-04-01T00:00:00Z" in merged["boundary_only_timestamps"]
    assert "2025-05-01T00:00:00Z" in merged["boundary_only_timestamps"]
    rows = aggregate_daily_weather(
        merged["records"],
        period_start=date(2023, 3, 31),
        period_end=date(2023, 4, 1),
        aoi_id="plovdiv_test",
        spatial={"source_latitude": 42.1, "source_longitude": 24.7},
    )
    assert rows[0]["precipitation_total_mm"] == pytest.approx(0.0)
    assert rows[0]["evaporation_total_mm"] == pytest.approx(2.0056236535310745)
    assert rows[0]["quality_status"] == "valid"
    assert rows[1]["hourly_records_available"] == 0
    assert rows[1]["temperature_mean_c"] is None
    assert rows[1]["precipitation_total_mm"] is None
    assert rows[1]["observation_kind"] == "missing"
    evaluated = evaluate_daily_rows(rows)
    assert evaluated["days"][1]["quality_status"] == "missing"
    assert evaluated["days"][1]["quality_status"] != "rejected"
    monthly = monthly_weather_summary(
        aggregate_daily_weather(
            merged["records"],
            period_start=date(2023, 3, 1),
            period_end=date(2023, 4, 30),
            aoi_id="plovdiv_test",
            spatial={"source_latitude": 42.1, "source_longitude": 24.7},
        ),
        downloaded_months=["2023-03", "2025-04"],
    )
    by_month = {item["month"]: item for item in monthly}
    assert by_month["2023-04"]["availability"] == "missing_source"
    assert by_month["2023-04"]["complete_days"] == 0
    assert by_month["2023-04"]["temperature_mean_c"] is None
    assert by_month["2023-04"]["precipitation_total_mm"] is None
    assert by_month["2023-03"]["complete_days"] == 31
    assert by_month["2023-03"]["availability"] == "downloaded"


def test_full_period_120_complete_days_are_not_corrupt():
    hours = []
    previous = None
    for year, month in ((2023, 1), (2023, 2), (2023, 3), (2025, 4)):
        if (year, month) == (2025, 4):
            previous = None
        chunk, previous = _complete_month_hours(
            year,
            month,
            rain_m=0.001 * month,
            previous_close=previous,
        )
        hours.extend(chunk)
    merged = reconcile_hourly_records(
        hours,
        downloaded_months=["2023-01", "2023-02", "2023-03", "2025-04"],
    )
    hourly = evaluate_hourly_records(merged["records"])
    assert hourly["status"] == "valid"
    assert not any(issue["code"] == "duplicate_timestamps" for issue in hourly["issues"])
    rows = aggregate_daily_weather(
        merged["records"],
        period_start=date(2023, 1, 1),
        period_end=date(2025, 12, 31),
        aoi_id="plovdiv_test",
        spatial={"source_latitude": 42.1, "source_longitude": 24.7},
    )
    assert len(rows) == 1096
    assert any(row["date_utc"] == "2024-02-29" for row in rows)
    leap = next(row for row in rows if row["date_utc"] == "2024-02-29")
    assert leap["hourly_records_available"] == 0
    assert leap["quality_status"] == "missing"
    evaluated = evaluate_daily_rows(rows)
    assert evaluated["complete_days"] == 120
    assert evaluated["missing_days"] == 976
    assert evaluated["incomplete_days"] == 976
    assert evaluated["statuses"].get("missing") == 976
    assert evaluated["statuses"].get("valid") == 120
    assert evaluated["statuses"].get("rejected") is None
    assert evaluated["status"] == "valid"
    report = build_quality_report(
        dataset_id="plovdiv_weather_2023_2025",
        config={
            "source": {"dataset": "reanalysis-era5-land"},
            "period": {"start": "2023-01-01", "end": "2025-12-31"},
            "time": {"timezone": "UTC"},
            "variables": [],
        },
        hourly=hourly,
        daily=evaluated,
        coverage={
            "downloaded_months": ["2023-01", "2023-02", "2023-03", "2025-04"],
            "missing_months": ["2023-04"],
        },
    )
    assert report["status"] == "valid"
    assert report["source_integrity"] == "valid"
    assert report["observation_validity"] == "valid"
    assert report["period_completeness"] == "incomplete"
    assert report["integration_readiness"] == "limited"
    assert report["daily"]["completeness_pct"] == 10.95
    assert any(issue["code"] == "incomplete_historical_period" for issue in report["issues"])
    march_31 = next(row for row in rows if row["date_utc"] == "2023-03-31")
    april_30 = next(row for row in rows if row["date_utc"] == "2025-04-30")
    april_1 = next(row for row in rows if row["date_utc"] == "2023-04-01")
    may_1 = next(row for row in rows if row["date_utc"] == "2025-05-01")
    assert march_31["precipitation_total_mm"] == pytest.approx(3.0)
    assert april_30["precipitation_total_mm"] == pytest.approx(4.0)
    assert april_1["hourly_records_available"] == 0
    assert may_1["hourly_records_available"] == 0


def test_safe_integration_skips_missing_weather_windows():
    from ml.integration.satellite_weather import integrate_satellite_weather

    complete = []
    for offset in range(30):
        day = date(2025, 4, 1) + timedelta(days=offset)
        complete.append({
            "date_utc": day.isoformat(),
            "temperature_mean_c": 10.0,
            "relative_humidity_mean_pct": 50.0,
            "wind_speed_mean_ms": 2.0,
            "precipitation_total_mm": 1.0,
            "hourly_records_available": 24,
            "boundary_00utc_available": True,
            "quality_status": "valid",
            "source_grid_id": "42.1,24.7",
        })
    missing = []
    for offset in range(31, 61):
        day = date(2025, 4, 1) + timedelta(days=offset)
        missing.append({
            "date_utc": day.isoformat(),
            "temperature_mean_c": None,
            "precipitation_total_mm": None,
            "hourly_records_available": 0,
            "boundary_00utc_available": False,
            "quality_status": "missing",
            "source_grid_id": "42.1,24.7",
        })
    rows = integrate_satellite_weather(
        complete + missing,
        [
            {"scene_id": "IN_WINDOW", "date": "2025-04-21", "mean": 0.4},
            {"scene_id": "MISSING_WINDOW", "date": "2025-05-21", "mean": 0.5},
        ],
        weather_dataset_id="weather",
        satellite_dataset_id="sat",
        aoi_id="plovdiv_test",
    )
    by_id = {item["scene_id"]: item for item in rows}
    assert by_id["IN_WINDOW"]["precip_prev_7d_mm"] == pytest.approx(7.0)
    assert by_id["IN_WINDOW"]["window_7d_complete"] is True
    assert by_id["MISSING_WINDOW"]["precip_prev_7d_mm"] is None
    assert by_id["MISSING_WINDOW"]["window_7d_complete"] is False
