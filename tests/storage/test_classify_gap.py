"""Tests for the shared gap classifier used by the CLI and the ops page."""

import datetime as dt

from cs2_analytics.storage.discovery_coverage import classify_gap

FRONTIER = dt.date(2026, 9, 7)


def test_gap_entirely_below_the_frontier_is_unswept() -> None:
    assert classify_gap(dt.date(2026, 8, 24), dt.date(2026, 8, 31), FRONTIER) == "unswept"


def test_gap_at_or_above_the_frontier_was_swept() -> None:
    assert classify_gap(dt.date(2026, 9, 7), dt.date(2026, 9, 14), FRONTIER) == "swept, no matches"


def test_gap_straddling_the_frontier_is_partly_unswept() -> None:
    assert classify_gap(dt.date(2026, 8, 31), dt.date(2026, 9, 7), FRONTIER) == "partly unswept"


def test_no_frontier_means_no_classification() -> None:
    assert classify_gap(dt.date(2026, 8, 31), dt.date(2026, 9, 7), None) == "unclassified"
