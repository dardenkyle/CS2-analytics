"""Conversion of the source's millisecond instants to aware UTC datetimes.

Every date the source exposes is a millisecond unix instant in a `data-*`
attribute: the match page's kickoff, the map stats page's date, and each
results-listing entry's instant. Converting in UTC keeps the stored value
independent of the host's zone (#214, #215); this is the one place that
does it, so the three parsers cannot drift apart.
"""

import datetime as dt


def utc_from_unix_ms(raw: str) -> dt.datetime:
    """Returns the aware UTC datetime for a millisecond unix timestamp.

    Raises `ValueError` for anything that is not a readable instant, folding
    the lower-level failures (a non-numeric string, a value outside the
    platform's range) into one exception for callers to translate.
    """
    try:
        return dt.datetime.fromtimestamp(int(raw) / 1000, tz=dt.UTC)
    except (TypeError, ValueError, OSError, OverflowError) as e:
        raise ValueError(f"Not a millisecond unix instant: {raw!r}") from e
