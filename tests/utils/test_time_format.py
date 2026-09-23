"""Tests for the presentation-layer timestamp formatter (#213)."""

import datetime as dt
from zoneinfo import ZoneInfo

from cs2_analytics.utils.time_format import MISSING_TIMESTAMP, format_local


def test_aware_utc_renders_as_central_daylight_time() -> None:
    value = dt.datetime(2026, 7, 10, 18, 0, 5, tzinfo=dt.UTC)

    assert format_local(value) == "2026-07-10 01:00:05 PM CDT"


def test_aware_utc_renders_as_central_standard_time_in_winter() -> None:
    value = dt.datetime(2026, 1, 10, 18, 0, 0, tzinfo=dt.UTC)

    assert format_local(value) == "2026-01-10 12:00:00 PM CST"


def test_naive_input_is_treated_as_utc() -> None:
    naive = dt.datetime(2026, 7, 10, 18, 0, 5)
    aware = naive.replace(tzinfo=dt.UTC)

    assert format_local(naive) == format_local(aware)


def test_other_zones_are_converted_not_relabelled() -> None:
    value = dt.datetime(2026, 7, 10, 20, 0, 5, tzinfo=ZoneInfo("Europe/Berlin"))

    assert format_local(value) == "2026-07-10 01:00:05 PM CDT"


def test_none_renders_as_the_missing_marker() -> None:
    assert format_local(None) == MISSING_TIMESTAMP == "-"
