"""Tests for the results controller's modes, retries, and stop reasons.

The scraper and stage service are faked; the real ResultsScraper's STOP_*
constants are used so the controller's scraper-to-run reason mapping is
exercised against the real vocabulary.
"""

import datetime as dt

import pytest

from cs2_analytics.controllers import results_controller as results_module
from cs2_analytics.exceptions import PipelineError, SessionScrapeError
from cs2_analytics.scrapers.results_scraper import ResultsScraper

_D1 = dt.date(2026, 8, 30)

SUMMARY_FORMAT = (
    "ResultsController summary: status=%s stop_reason=%s seen=%d "
    "newly_discovered=%d retries=%d terminal_failures=%d max_matches=%d"
)


class _FakeStageService:
    """Records batches; new-row counts come from a configurable plan."""

    def __init__(self, new_counts: list[int] | None = None) -> None:
        self.batches: list[list[tuple[int, str, dt.date]]] = []
        self.new_counts = new_counts

    def record_batch(self, batch):
        self.batches.append(list(batch))
        if self.new_counts is not None:
            return len(batch), self.new_counts.pop(0)
        return len(batch), len(batch)


class _FakeMatchState:
    def __init__(self, min_match_date: dt.date | None) -> None:
        self.min_match_date = min_match_date

    def fetch_min_match_date(self) -> dt.date | None:
        return self.min_match_date


class _RetryThenSucceedScraper:
    def __init__(self) -> None:
        self.run_calls = 0
        self.close_calls = 0
        self.stop_reason = ResultsScraper.STOP_EMPTY_PAGE

    def iter_match_batches(
        self, max_matches, start_date, end_date, use_source_date_filter=False
    ):
        self.run_calls += 1
        if self.run_calls == 1:
            raise SessionScrapeError("Session dropped while fetching results page.")
        yield [(111, "https://www.hltv.org/matches/111/a-vs-b", _D1)]
        yield [(222, "https://www.hltv.org/matches/222/c-vs-d", _D1)]
        self.stop_reason = ResultsScraper.STOP_WINDOW_FLOOR

    def close(self) -> None:
        self.close_calls += 1


class _AlwaysFailingRetryableScraper:
    def __init__(self) -> None:
        self.run_calls = 0
        self.close_calls = 0
        self.stop_reason = ResultsScraper.STOP_EMPTY_PAGE

    def iter_match_batches(
        self, max_matches, start_date, end_date, use_source_date_filter=False
    ):
        self.run_calls += 1
        raise SessionScrapeError("Session dropped while fetching results page.")
        yield  # pragma: no cover - makes this a generator like the real scraper

    def close(self) -> None:
        self.close_calls += 1


class _NonRetryableFailingScraper:
    def __init__(self) -> None:
        self.run_calls = 0
        self.close_calls = 0
        self.stop_reason = ResultsScraper.STOP_EMPTY_PAGE

    def iter_match_batches(
        self, max_matches, start_date, end_date, use_source_date_filter=False
    ):
        self.run_calls += 1
        raise RuntimeError("Unexpected parse failure")
        yield  # pragma: no cover - makes this a generator like the real scraper

    def close(self) -> None:
        self.close_calls += 1


class _SlicingScraper:
    """Backfill fake: records each slice request and yields per-slice matches."""

    def __init__(self, per_slice: int = 1) -> None:
        self.per_slice = per_slice
        self.slice_calls: list[tuple[int, dt.date, dt.date, bool]] = []
        self.close_calls = 0
        self.next_id = 1000
        self.stop_reason = ResultsScraper.STOP_EMPTY_PAGE

    def iter_match_batches(
        self, max_matches, start_date, end_date, use_source_date_filter=False
    ):
        self.slice_calls.append(
            (max_matches, start_date, end_date, use_source_date_filter)
        )
        yielded = min(self.per_slice, max_matches)
        batch = []
        for _ in range(yielded):
            self.next_id += 1
            batch.append(
                (self.next_id, f"https://www.hltv.org/matches/{self.next_id}/x", end_date)
            )
        if batch:
            yield batch
        self.stop_reason = (
            ResultsScraper.STOP_BUDGET
            if yielded >= max_matches
            else ResultsScraper.STOP_WINDOW_FLOOR
        )

    def close(self) -> None:
        self.close_calls += 1


def _build_controller(monkeypatch, scraper_cls, stage_service=None):
    monkeypatch.setattr(results_module, "ResultsScraper", scraper_cls)
    monkeypatch.setattr(results_module.time, "sleep", lambda *_args, **_kwargs: None)
    controller = results_module.ResultsController()
    controller.stage_service = stage_service or _FakeStageService()
    return controller


def _capture_logger(monkeypatch, level: str):
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    monkeypatch.setattr(
        getattr(results_module, "logger"),
        level,
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    return calls


def _summary_args(info_calls):
    for call_args, _ in info_calls:
        if call_args[0] == SUMMARY_FORMAT:
            return call_args[1:]
    raise AssertionError("Summary log line not found")


def test_results_controller_retries_retryable_scrape_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info_calls = _capture_logger(monkeypatch, "info")
    reset_calls: list[object] = []
    controller = _build_controller(monkeypatch, _RetryThenSucceedScraper)
    monkeypatch.setattr(
        controller,
        "_reset_scraper",
        lambda scraper: reset_calls.append(scraper) or scraper,
    )

    controller.run(
        max_matches=25,
        start_date=dt.date(2025, 10, 1),
        end_date=dt.date(2026, 8, 31),
    )

    assert controller.scraper.run_calls == 2
    assert len(reset_calls) == 1
    assert controller.stage_service.batches == [
        [(111, "https://www.hltv.org/matches/111/a-vs-b", _D1)],
        [(222, "https://www.hltv.org/matches/222/c-vs-d", _D1)],
    ]
    assert _summary_args(info_calls) == (
        "succeeded",
        results_module.STOP_WINDOW_COVERED,
        2,
        2,
        1,
        0,
        25,
    )


def test_results_controller_raises_pipeline_error_after_exhausting_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info_calls = _capture_logger(monkeypatch, "info")
    error_calls = _capture_logger(monkeypatch, "error")
    exception_calls = _capture_logger(monkeypatch, "exception")
    reset_calls: list[object] = []
    controller = _build_controller(monkeypatch, _AlwaysFailingRetryableScraper)
    monkeypatch.setattr(
        controller,
        "_reset_scraper",
        lambda scraper: reset_calls.append(scraper) or scraper,
    )

    with pytest.raises(
        PipelineError,
        match=r"Results stage failed after exhausting retries \(3/3 attempts\)\.",
    ) as exc_info:
        controller.run(
            max_matches=25,
            start_date=dt.date(2025, 10, 1),
            end_date=dt.date(2026, 8, 31),
        )

    assert isinstance(exc_info.value.__cause__, SessionScrapeError)
    assert controller.scraper.run_calls == 3
    assert len(reset_calls) == 2
    assert len(error_calls) == 1
    assert len(exception_calls) == 1
    assert _summary_args(info_calls) == ("failed", None, 0, 0, 2, 1, 25)


def test_results_controller_raises_pipeline_error_for_non_retryable_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info_calls = _capture_logger(monkeypatch, "info")
    exception_calls = _capture_logger(monkeypatch, "exception")
    reset_calls: list[object] = []
    controller = _build_controller(monkeypatch, _NonRetryableFailingScraper)
    monkeypatch.setattr(
        controller,
        "_reset_scraper",
        lambda scraper: reset_calls.append(scraper) or scraper,
    )

    with pytest.raises(
        PipelineError,
        match=r"Results stage failed on non-retryable error at attempt 1/3\.",
    ) as exc_info:
        controller.run(
            max_matches=25,
            start_date=dt.date(2025, 10, 1),
            end_date=dt.date(2026, 8, 31),
        )

    assert isinstance(exc_info.value.__cause__, RuntimeError)
    assert controller.scraper.run_calls == 1
    assert reset_calls == []
    assert len(exception_calls) == 1
    assert _summary_args(info_calls) == ("failed", None, 0, 0, 0, 1, 25)


def test_incremental_stops_early_when_a_page_yields_nothing_new(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info_calls = _capture_logger(monkeypatch, "info")

    class _TwoPageScraper(_RetryThenSucceedScraper):
        def __init__(self) -> None:
            super().__init__()
            self.run_calls = 1  # skip the failure on first call

    stage = _FakeStageService(new_counts=[0, 99])
    controller = _build_controller(monkeypatch, _TwoPageScraper, stage)

    controller.run(
        max_matches=25,
        start_date=dt.date(2025, 10, 1),
        end_date=dt.date(2026, 8, 31),
    )

    # The first batch is all-known (0 new), so the second page is never
    # consumed - only one batch reaches the stage service.
    assert len(stage.batches) == 1
    assert _summary_args(info_calls) == (
        "succeeded",
        results_module.STOP_UP_TO_DATE,
        1,
        0,
        0,
        0,
        25,
    )


def test_backfill_exits_immediately_when_window_already_covered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info_calls = _capture_logger(monkeypatch, "info")
    scraper = _SlicingScraper()
    controller = _build_controller(monkeypatch, lambda: scraper)
    controller.match_state = _FakeMatchState(min_match_date=dt.date(2025, 9, 30))

    controller.run(
        max_matches=25,
        start_date=dt.date(2025, 10, 1),
        end_date=dt.date(2026, 8, 31),
        mode="backfill",
    )

    assert scraper.slice_calls == []
    assert _summary_args(info_calls) == (
        "succeeded",
        results_module.STOP_WINDOW_COVERED,
        0,
        0,
        0,
        0,
        25,
    )


def test_backfill_resumes_at_frontier_and_walks_to_the_floor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info_calls = _capture_logger(monkeypatch, "info")
    scraper = _SlicingScraper(per_slice=1)
    controller = _build_controller(monkeypatch, lambda: scraper)
    controller.match_state = _FakeMatchState(min_match_date=dt.date(2026, 8, 20))

    controller.run(
        max_matches=25,
        start_date=dt.date(2026, 8, 1),
        end_date=dt.date(2026, 8, 31),
        mode="backfill",
    )

    # Slice 1 re-sweeps the frontier day; later slices step back a week at
    # a time until the floor, each passing the remaining budget and the
    # source date filter.
    assert scraper.slice_calls == [
        (25, dt.date(2026, 8, 14), dt.date(2026, 8, 20), True),
        (24, dt.date(2026, 8, 7), dt.date(2026, 8, 13), True),
        (23, dt.date(2026, 8, 1), dt.date(2026, 8, 6), True),
    ]
    assert _summary_args(info_calls) == (
        "succeeded",
        results_module.STOP_WINDOW_COVERED,
        3,
        3,
        0,
        0,
        25,
    )


def test_backfill_starts_at_window_end_when_nothing_is_dated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scraper = _SlicingScraper(per_slice=1)
    controller = _build_controller(monkeypatch, lambda: scraper)
    controller.match_state = _FakeMatchState(min_match_date=None)

    controller.run(
        max_matches=25,
        start_date=dt.date(2026, 8, 20),
        end_date=dt.date(2026, 8, 31),
        mode="backfill",
    )

    assert scraper.slice_calls[0] == (
        25,
        dt.date(2026, 8, 25),
        dt.date(2026, 8, 31),
        True,
    )


def test_backfill_stops_when_the_budget_is_spent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info_calls = _capture_logger(monkeypatch, "info")
    scraper = _SlicingScraper(per_slice=5)
    controller = _build_controller(monkeypatch, lambda: scraper)
    controller.match_state = _FakeMatchState(min_match_date=dt.date(2026, 8, 20))

    controller.run(
        max_matches=2,
        start_date=dt.date(2026, 8, 1),
        end_date=dt.date(2026, 8, 31),
        mode="backfill",
    )

    assert len(scraper.slice_calls) == 1
    assert _summary_args(info_calls) == (
        "succeeded",
        results_module.STOP_BUDGET_EXHAUSTED,
        2,
        2,
        0,
        0,
        2,
    )
