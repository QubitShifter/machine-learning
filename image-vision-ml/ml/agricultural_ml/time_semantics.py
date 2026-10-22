"""Issue-time, feature-cutoff and target-period semantics.

Issue time t_D is 00:00 UTC on calendar day D. Completed daily observations
through D−1 are temporally eligible for research_reanalysis features.
That is not operational publication proof.
"""

from __future__ import annotations

import calendar
import math
from datetime import date, datetime, timedelta, timezone
from typing import Any

from ml.integration.satellite_weather import prior_window_dates


ISSUE_CLOCK = "00:00:00Z"
DATA_AVAILABILITY_MODE = "research_reanalysis"


def parse_utc_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).date()
    if isinstance(value, date):
        return value
    text = str(value).replace("Z", "+00:00")[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def issue_datetime_utc(issue_date: date) -> datetime:
    return datetime(issue_date.year, issue_date.month, issue_date.day, tzinfo=timezone.utc)


def iso_z(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def last_observation_date(issue_date: date) -> date:
    return issue_date - timedelta(days=1)


def feature_cutoff_utc(issue_date: date) -> datetime:
    return issue_datetime_utc(issue_date)


def target_date(issue_date: date, horizon_days: int) -> date:
    return issue_date + timedelta(days=int(horizon_days))


def target_period(issue_date: date, horizon_days: int) -> tuple[datetime, datetime]:
    """Daily-mean target for D+h: [D+h 00:00, D+h+1 00:00) UTC."""
    start_day = target_date(issue_date, horizon_days)
    start = issue_datetime_utc(start_day)
    end = start + timedelta(days=1)
    return start, end


def daterange(start: date, end: date) -> list[date]:
    days = []
    cursor = start
    while cursor <= end:
        days.append(cursor)
        cursor += timedelta(days=1)
    return days


def year_length_days(year: int) -> int:
    return 366 if calendar.isleap(year) else 365


def calendar_features(issue_date: date) -> dict[str, Any]:
    """Known-at-issue-time calendar encodings. Leap years use L=366."""
    length = year_length_days(issue_date.year)
    doy = issue_date.timetuple().tm_yday
    angle = 2.0 * math.pi * (doy - 1) / length
    return {
        "calendar_year": issue_date.year,
        "calendar_month": issue_date.month,
        "day_of_year": doy,
        "day_of_year_length": length,
        "day_of_year_sin": math.sin(angle),
        "day_of_year_cos": math.cos(angle),
        "leap_year": calendar.isleap(issue_date.year),
    }


def window_bounds(issue_date: date, window: int) -> tuple[date, date]:
    days = prior_window_dates(issue_date, window)
    return days[0], days[-1]
