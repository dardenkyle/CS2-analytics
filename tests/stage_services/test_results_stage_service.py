"""Tests for the results discovery persistence service."""

import datetime as dt

from cs2_analytics.stage_services import ResultsStageService


class _FakeMatchState:
    def __init__(self, new_rows: int = 0) -> None:
        self.new_rows = new_rows
        self.record_calls: list[tuple[list[tuple[int, str, dt.date | None]], str]] = []

    def record_discovered(
        self,
        items: list[tuple[int, str, dt.date | None]],
        source: str = "results_scraper",
        priority: int = 0,
    ) -> int:
        self.record_calls.append((list(items), source))
        return self.new_rows


def test_record_batch_records_dated_items_with_source() -> None:
    state = _FakeMatchState(new_rows=1)
    service = ResultsStageService(match_state=state)
    batch = [
        (1001, "https://example.test/matches/1001", dt.date(2026, 5, 1)),
        (1002, "https://example.test/matches/1002", dt.date(2026, 5, 2)),
    ]

    recorded, newly_discovered = service.record_batch(batch)

    assert recorded == 2
    assert newly_discovered == 1
    assert len(state.record_calls) == 1
    items, source = state.record_calls[0]
    assert items == batch
    assert source == "results_scraper"


def test_record_batch_empty_is_a_no_op() -> None:
    state = _FakeMatchState()
    service = ResultsStageService(match_state=state)

    assert service.record_batch([]) == (0, 0)
    assert state.record_calls == []


def test_record_batch_reports_all_known_batches() -> None:
    # newly_discovered == 0 on a non-empty batch is the incremental
    # early-stop signal (#121).
    state = _FakeMatchState(new_rows=0)
    service = ResultsStageService(match_state=state)
    batch = [(1001, "https://example.test/matches/1001", None)]

    recorded, newly_discovered = service.record_batch(batch)

    assert recorded == 1
    assert newly_discovered == 0
