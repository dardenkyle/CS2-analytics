"""Controller for scraping and recording match result links."""

import datetime as dt
import time
from dataclasses import dataclass

from cs2_analytics.controllers.retry_utils import (
    is_retryable_scraper_error,
    reset_scraper,
)
from cs2_analytics.exceptions import PipelineError
from cs2_analytics.ingestion_state import MatchIngestionState
from cs2_analytics.scrapers.results_scraper import ResultsScraper
from cs2_analytics.stage_services import ResultsStageService
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger("results_controller")

RETRY_BACKOFF_SECONDS = 3.0
MAX_ATTEMPTS = 3

# Run-level stop reasons reported in the controller summary (#121).
STOP_UP_TO_DATE = "up_to_date"
STOP_WINDOW_COVERED = "window_covered"
STOP_BUDGET_EXHAUSTED = "budget_exhausted"
STOP_EMPTY_PAGE = "empty_page"

# Backfill walks backward one date slice at a time; a week keeps slices
# small enough that a budget-stopped run loses at most a few days of
# re-sweep on resume.
BACKFILL_CHUNK_DAYS = 7

SCRAPER_STOP_TO_RUN_REASON = {
    ResultsScraper.STOP_BUDGET: STOP_BUDGET_EXHAUSTED,
    ResultsScraper.STOP_WINDOW_FLOOR: STOP_WINDOW_COVERED,
    ResultsScraper.STOP_EMPTY_PAGE: STOP_EMPTY_PAGE,
}


@dataclass
class _ResultsRunState:
    """Tracks the active scraper and outcome counters for one results run."""

    scraper: ResultsScraper
    status: str = "failed"
    retries: int = 0
    terminal_failures: int = 0
    seen: int = 0
    newly_discovered: int = 0
    stop_reason: str | None = None


class ResultsController:
    """Orchestrates the results scraping stage."""

    def __init__(self) -> None:
        self.scraper = ResultsScraper()
        self.match_state = MatchIngestionState()
        self.stage_service = ResultsStageService(match_state=self.match_state)

    def run(
        self,
        max_matches: int,
        start_date: dt.date,
        end_date: dt.date,
        mode: str = "incremental",
    ) -> None:
        """Scrapes result pages and records match URLs for downstream stages.

        Run parameters are explicit (ADR-0015): the invoker owns the
        discovery window, cap, and mode. The cap is a per-run budget,
        never a completion signal (#121). Incremental scans newest-first
        and stops early once a page yields nothing new; backfill resumes
        at the derived frontier (oldest recorded match_date) and walks
        backward in date slices toward the window floor, exiting
        immediately with `window_covered` when the floor is reached.
        """
        logger.info(
            "Running ResultsController mode=%s max_matches=%d window=%s..%s",
            mode,
            max_matches,
            start_date,
            end_date,
        )

        run_state = _ResultsRunState(scraper=self.scraper)
        try:
            if mode == "backfill":
                self._run_backfill(max_matches, start_date, end_date, run_state)
            else:
                self._run_incremental(max_matches, start_date, end_date, run_state)
            run_state.status = "succeeded"
            logger.info(
                "ResultsController complete. seen=%d newly_discovered=%d stop_reason=%s",
                run_state.seen,
                run_state.newly_discovered,
                run_state.stop_reason,
            )
        finally:
            self._close_scraper(run_state)
            logger.info(
                "ResultsController summary: status=%s stop_reason=%s seen=%d "
                "newly_discovered=%d retries=%d terminal_failures=%d max_matches=%d",
                run_state.status,
                run_state.stop_reason,
                run_state.seen,
                run_state.newly_discovered,
                run_state.retries,
                run_state.terminal_failures,
                max_matches,
            )

    def _run_incremental(
        self,
        max_matches: int,
        start_date: dt.date,
        end_date: dt.date,
        run_state: _ResultsRunState,
    ) -> None:
        """Scans newest-first from the top of the results listing."""

        def scan(state: _ResultsRunState) -> None:
            iterator = state.scraper.iter_match_batches(
                max_matches=max_matches, start_date=start_date, end_date=end_date
            )
            for batch in iterator:
                recorded, new_rows = self.stage_service.record_batch(batch)
                state.seen += recorded
                state.newly_discovered += new_rows
                if recorded and new_rows == 0:
                    state.stop_reason = STOP_UP_TO_DATE
                    iterator.close()
                    return
            state.stop_reason = SCRAPER_STOP_TO_RUN_REASON[state.scraper.stop_reason]

        self._attempt_with_retries(scan, run_state)

    def _run_backfill(
        self,
        max_matches: int,
        start_date: dt.date,
        end_date: dt.date,
        run_state: _ResultsRunState,
    ) -> None:
        """Walks backward from the frontier toward the window floor.

        The frontier is derived as min(match_date) over recorded rows, so
        consecutive runs resume where the last one stopped; the frontier
        day itself is re-swept (idempotent) to heal a run that stopped
        mid-slice. A retried slice may count some matches toward the
        budget twice; that only makes the budget conservative.
        """
        frontier = self.match_state.fetch_min_match_date()
        if frontier is not None and frontier <= start_date:
            run_state.stop_reason = STOP_WINDOW_COVERED
            logger.info(
                "Backfill window already covered: frontier %s at or below floor %s.",
                frontier,
                start_date,
            )
            return

        chunk_end = frontier if frontier is not None else end_date
        while True:
            chunk_start = max(
                start_date, chunk_end - dt.timedelta(days=BACKFILL_CHUNK_DAYS - 1)
            )
            budget_left = max_matches - run_state.seen

            def scan_chunk(
                state: _ResultsRunState,
                chunk_start: dt.date = chunk_start,
                chunk_end: dt.date = chunk_end,
                budget_left: int = budget_left,
            ) -> None:
                for batch in state.scraper.iter_match_batches(
                    max_matches=budget_left,
                    start_date=chunk_start,
                    end_date=chunk_end,
                    use_source_date_filter=True,
                ):
                    recorded, new_rows = self.stage_service.record_batch(batch)
                    state.seen += recorded
                    state.newly_discovered += new_rows

            self._attempt_with_retries(scan_chunk, run_state)

            slice_reason = SCRAPER_STOP_TO_RUN_REASON.get(
                run_state.scraper.stop_reason
            )
            if slice_reason == STOP_BUDGET_EXHAUSTED:
                run_state.stop_reason = STOP_BUDGET_EXHAUSTED
                return
            if chunk_start <= start_date:
                run_state.stop_reason = STOP_WINDOW_COVERED
                logger.info(
                    "Backfill reached the window floor %s; window covered.",
                    start_date,
                )
                return
            chunk_end = chunk_start - dt.timedelta(days=1)

    def _attempt_with_retries(self, action, run_state: _ResultsRunState) -> None:
        """Runs one scrape action until it succeeds or retries are exhausted."""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                action(run_state)
                return
            except Exception as e:
                self._handle_attempt_failure(e, attempt, run_state)

    def _handle_attempt_failure(
        self, error: Exception, attempt: int, run_state: _ResultsRunState
    ) -> None:
        """Backs off and resets for retryable errors; raises PipelineError otherwise."""
        is_retryable = self._is_recoverable_scraper_error(error)

        if attempt < MAX_ATTEMPTS and is_retryable:
            run_state.retries += 1
            logger.warning(
                "Retryable results scraper error (attempt %d/%d): %s",
                attempt,
                MAX_ATTEMPTS,
                error,
            )
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)
            run_state.scraper = self._reset_scraper(run_state.scraper)
            return

        run_state.terminal_failures += 1
        if is_retryable:
            logger.error(
                "ResultsController exhausted retries after %d attempts; failing stage run.",
                MAX_ATTEMPTS,
            )
            failure_message = (
                "Results stage failed after exhausting retries "
                f"({attempt}/{MAX_ATTEMPTS} attempts)."
            )
        else:
            failure_message = (
                "Results stage failed on non-retryable error "
                f"at attempt {attempt}/{MAX_ATTEMPTS}."
            )
        logger.exception(
            "ResultsController failed on attempt %d/%d: %s",
            attempt,
            MAX_ATTEMPTS,
            error,
        )
        raise PipelineError(failure_message) from error

    def _close_scraper(self, run_state: _ResultsRunState) -> None:
        """Closes the active scraper, downgrading close failures to a warning."""
        try:
            run_state.scraper.close()
        except Exception as e:
            logger.warning("Failed to close results scraper: %s", e)

    def _is_recoverable_scraper_error(self, error: Exception) -> bool:
        return is_retryable_scraper_error(error)

    def _reset_scraper(self, scraper: ResultsScraper) -> ResultsScraper:
        self.scraper = reset_scraper(
            scraper,
            ResultsScraper,
            logger=logger,
            close_warning_message="Failed to close results scraper during recovery: %s",
            startup_delay_seconds=1.0,
        )
        return self.scraper
