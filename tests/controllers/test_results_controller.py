import pytest

from cs2_analytics.controllers import results_controller as results_module
from cs2_analytics.exceptions import PipelineError, SessionScrapeError


class _FakeStageService:
    def __init__(self) -> None:
        self.batches: list[list[tuple[int, str]]] = []

    def record_batch(self, batch: list[tuple[int, str]]) -> int:
        self.batches.append(list(batch))
        return len(batch)


class _RetryThenSucceedScraper:
    def __init__(self) -> None:
        self.run_calls = 0
        self.close_calls = 0

    def iter_match_batches(self, max_matches: int = 50):
        self.run_calls += 1
        if self.run_calls == 1:
            raise SessionScrapeError("Session dropped while fetching results page.")
        yield [(111, "https://www.hltv.org/matches/111/a-vs-b")]
        yield [(222, "https://www.hltv.org/matches/222/c-vs-d")]

    def close(self) -> None:
        self.close_calls += 1


class _AlwaysFailingRetryableScraper:
    def __init__(self) -> None:
        self.run_calls = 0
        self.close_calls = 0

    def iter_match_batches(self, max_matches: int = 50):
        self.run_calls += 1
        raise SessionScrapeError("Session dropped while fetching results page.")
        yield  # pragma: no cover - makes this a generator like the real scraper

    def close(self) -> None:
        self.close_calls += 1


class _NonRetryableFailingScraper:
    def __init__(self) -> None:
        self.run_calls = 0
        self.close_calls = 0

    def iter_match_batches(self, max_matches: int = 50):
        self.run_calls += 1
        raise RuntimeError("Unexpected parse failure")
        yield  # pragma: no cover - makes this a generator like the real scraper

    def close(self) -> None:
        self.close_calls += 1


def test_results_controller_retries_retryable_scrape_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    reset_calls: list[object] = []
    monkeypatch.setattr(results_module, "ResultsScraper", _RetryThenSucceedScraper)
    monkeypatch.setattr(results_module.time, "sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        results_module.logger,
        "info",
        lambda *args, **kwargs: info_calls.append((args, kwargs)),
    )

    controller = results_module.ResultsController()
    controller.stage_service = _FakeStageService()
    monkeypatch.setattr(
        controller,
        "_reset_scraper",
        lambda scraper: reset_calls.append(scraper) or scraper,
    )

    controller.run(max_matches=25)

    assert controller.scraper.run_calls == 2
    assert len(reset_calls) == 1
    assert controller.stage_service.batches == [
        [(111, "https://www.hltv.org/matches/111/a-vs-b")],
        [(222, "https://www.hltv.org/matches/222/c-vs-d")],
    ]
    assert any(
        call_args[0]
        == "ResultsController summary: status=%s retries=%d terminal_failures=%d max_matches=%d"
        and call_args[1:] == ("succeeded", 1, 0, 25)
        for call_args, _ in info_calls
    )


def test_results_controller_raises_pipeline_error_after_exhausting_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    exception_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    info_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    reset_calls: list[object] = []
    monkeypatch.setattr(
        results_module,
        "ResultsScraper",
        _AlwaysFailingRetryableScraper,
    )
    monkeypatch.setattr(results_module.time, "sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        results_module.logger,
        "error",
        lambda *args, **kwargs: error_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        results_module.logger,
        "exception",
        lambda *args, **kwargs: exception_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        results_module.logger,
        "info",
        lambda *args, **kwargs: info_calls.append((args, kwargs)),
    )

    controller = results_module.ResultsController()
    controller.stage_service = _FakeStageService()
    monkeypatch.setattr(
        controller,
        "_reset_scraper",
        lambda scraper: reset_calls.append(scraper) or scraper,
    )

    with pytest.raises(
        PipelineError,
        match=r"Results stage failed after exhausting retries \(3/3 attempts\)\.",
    ) as exc_info:
        controller.run(max_matches=25)

    assert isinstance(exc_info.value.__cause__, SessionScrapeError)
    assert controller.scraper.run_calls == 3
    assert len(reset_calls) == 2
    assert error_calls == [
        (
            (
                "ResultsController exhausted retries after %d attempts; failing stage run.",
                3,
            ),
            {},
        )
    ]
    assert exception_calls == [
        (
            (
                "ResultsController failed on attempt %d/%d: %s",
                3,
                3,
                exc_info.value.__cause__,
            ),
            {},
        )
    ]
    assert any(
        call_args[0]
        == "ResultsController summary: status=%s retries=%d terminal_failures=%d max_matches=%d"
        and call_args[1:] == ("failed", 2, 1, 25)
        for call_args, _ in info_calls
    )


def test_results_controller_raises_pipeline_error_for_non_retryable_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    exception_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    info_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    reset_calls: list[object] = []
    monkeypatch.setattr(
        results_module,
        "ResultsScraper",
        _NonRetryableFailingScraper,
    )
    monkeypatch.setattr(results_module.time, "sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        results_module.logger,
        "error",
        lambda *args, **kwargs: error_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        results_module.logger,
        "exception",
        lambda *args, **kwargs: exception_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        results_module.logger,
        "info",
        lambda *args, **kwargs: info_calls.append((args, kwargs)),
    )

    controller = results_module.ResultsController()
    controller.stage_service = _FakeStageService()
    monkeypatch.setattr(
        controller,
        "_reset_scraper",
        lambda scraper: reset_calls.append(scraper) or scraper,
    )

    with pytest.raises(
        PipelineError,
        match=r"Results stage failed on non-retryable error at attempt 1/3\.",
    ) as exc_info:
        controller.run(max_matches=25)

    assert isinstance(exc_info.value.__cause__, RuntimeError)
    assert controller.scraper.run_calls == 1
    assert reset_calls == []
    assert error_calls == []
    assert exception_calls == [
        (
            (
                "ResultsController failed on attempt %d/%d: %s",
                1,
                3,
                exc_info.value.__cause__,
            ),
            {},
        )
    ]
    assert any(
        call_args[0]
        == "ResultsController summary: status=%s retries=%d terminal_failures=%d max_matches=%d"
        and call_args[1:] == ("failed", 0, 1, 25)
        for call_args, _ in info_calls
    )
