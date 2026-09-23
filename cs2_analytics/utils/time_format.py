"""Presentation-layer timestamp formatting.

Storage and queries stay in UTC: the database stamps ingestion-state rows
with its own `now()` (#213) and the parsers write aware UTC. Only output
shown to an operator is converted, here, to the operator's local zone.
"""

import datetime as dt
from zoneinfo import ZoneInfo

DISPLAY_TIMEZONE = ZoneInfo("America/Chicago")
DISPLAY_FORMAT = "%Y-%m-%d %I:%M:%S %p %Z"
MISSING_TIMESTAMP = "-"


def format_local(value: dt.datetime | None) -> str:
    """Render a timestamp as Central 12-hour time for operator output.

    Naive input is treated as UTC: every stored timestamp is aware after
    migration 20260923_0005, so the only naive values left are literals
    and fixtures, which follow the storage convention.
    """
    if value is None:
        return MISSING_TIMESTAMP
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.UTC)
    return value.astimezone(DISPLAY_TIMEZONE).strftime(DISPLAY_FORMAT)
