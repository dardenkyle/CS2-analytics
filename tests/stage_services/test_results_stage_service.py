"""Tests for the results discovery persistence service."""

from cs2_analytics.stage_services import ResultsStageService


class _FakeMatchState:
    def __init__(self) -> None:
        self.record_many_calls: list[tuple[list[tuple[int, str]], str, int]] = []

    def record_many(
        self,
        items: list[tuple[int, str]],
        source: str = "unknown",
        priority: int = 0,
    ) -> None:
        self.record_many_calls.append((list(items), source, priority))


def test_record_batch_records_items_with_source() -> None:
    state = _FakeMatchState()
    service = ResultsStageService(match_state=state)
    batch = [
        (1001, "https://example.test/matches/1001"),
        (1002, "https://example.test/matches/1002"),
    ]

    recorded = service.record_batch(batch)

    assert recorded == 2
    assert len(state.record_many_calls) == 1
    items, source, _priority = state.record_many_calls[0]
    assert items == batch
    assert source == "results_scraper"


def test_record_batch_empty_is_a_no_op() -> None:
    state = _FakeMatchState()
    service = ResultsStageService(match_state=state)

    assert service.record_batch([]) == 0
    assert state.record_many_calls == []


def test_record_batch_chunks_large_batches() -> None:
    state = _FakeMatchState()
    service = ResultsStageService(match_state=state, chunk_size=2)
    batch = [(n, f"https://example.test/matches/{n}") for n in range(5)]

    recorded = service.record_batch(batch)

    assert recorded == 5
    assert len(state.record_many_calls) == 3
    assert [len(items) for items, _, _ in state.record_many_calls] == [2, 2, 1]
