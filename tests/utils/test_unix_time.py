"""Tests for the shared millisecond-instant conversion (#215)."""

import datetime as dt

import pytest

from cs2_analytics.utils.unix_time import utc_from_unix_ms


def test_converts_milliseconds_to_an_aware_utc_datetime() -> None:
    assert utc_from_unix_ms("1793205600000") == dt.datetime(
        2026, 10, 28, 16, 40, tzinfo=dt.UTC
    )


@pytest.mark.parametrize("raw", ["soon", "", None, "1e12", "9" * 25])
def test_rejects_unreadable_values_as_value_error(raw) -> None:
    with pytest.raises(ValueError):
        utc_from_unix_ms(raw)
