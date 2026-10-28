# Conventions

## Scrapers

- Fetch remote content only
- No parsing
- No domain-table writes
- Match/map scrapers should not own lifecycle-state transitions

Current implementation note:

- `ResultsScraper` is fetch-only: it yields discovered match batches, and
  `ResultsStageService` owns the `match_ingestion_state` refreshes (#71)
- a test in `tests/scrapers/test_scraper_boundaries.py` fails if any scraper
  module imports storage or ingestion-state modules
- every scraper waits for a required selector through the shared
  `scrapers/page_wait.py` helper: `div.match-page` (match), `div.match-info-box`
  (map stats), and `div.results` (results listing, the container that
  is present even when a date range has no results); a page that never
  renders it, including the source's challenge interstitial, raises
  `SessionScrapeError` (retryable) with a diagnostic warning that carries the
  challenge-marker flags, so `cs2a failures` groups such rows under "appears
  blocked or challenged" or "missing required content" rather than under a
  parser message; parser errors are reserved for pages that rendered the
  selector (#57, #224, #230)
- `ResultsScraper` holds no HTML parsing: `parsers/results_parser.py` turns a
  rendered listing into a `ResultsPage` (in-window matches with section
  dates, the page's result count, and whether the window floor was reached),
  and the scraper only fetches and paginates on that outcome (#230)

## Parsers

- Extract structured data only
- No orchestration logic
- No lifecycle-state transitions
- No storage writes
- Raise typed parse exceptions with specific helper-level messages
- Treat the source's dash placeholder as a missing value, not a parse
  failure, for metrics the source can leave blank: ADR parses to `None`
  (stored as NULL) when a player was substituted mid-map and has no damage
  figure (#202), and KAST parses to `None` the same way (#210). Any other
  non-numeric text still raises. Rating and the kill, assist, and death
  cells stay strict: on the rows where KAST and ADR were dashes they were
  still numeric, so a non-numeric value there is a parse failure until a
  placeholder is observed

## Stage Services

- Own per-item stage workflow
- Call scrapers, parsers, and storage modules in order
- Apply normal lifecycle updates for processed, failed, and skipped outcomes
- Return `StageItemResult` so controllers can count outcomes explicitly
- Keep stage-specific processing rules out of controllers

Implemented services:

- `MatchStageService`
- `MapStageService`
- `DemoStageService`

## Controllers

- Coordinate batches of work
- Own retry policy and retry exhaustion behavior
- Retry two error classes within an item's attempt budget (`MAX_ATTEMPTS`):
  `RetryableScrapeError` (backoff, then a scraper reset) and a lost database
  connection, meaning `DatabaseConnectionError` anywhere in the error's
  explicit cause chain (backoff only; the scraper session is kept). Every
  other exception fails the item on the attempt that raised it (#208)
- Halt a match or map batch with a circuit breaker after
  `CIRCUIT_BREAKER_THRESHOLD` (five) consecutive `RetryableScrapeError`
  attempts with no successful fetch between them, counted across items.
  The halt returns the in-flight row and the rows the streak marked
  `failed` to `discovered`, and the returned summary's outcome is
  `BatchOutcome.HALTED`. Lost database connections do not count toward
  the breaker (#175, ADR-0017)
- Return a `RunSummary` from `run()` (stage, outcome, selected,
  succeeded, failed, retries, rotations, stop reason), built and logged
  in `finally` so an escaping exception still leaves the summary line
  behind, reported as `BatchOutcome.ABORTED` with the exception
  propagating; the CLI maps the summary to an exit status and tests
  assert on the value rather than the log format (#238)
- Own scraper reset and rotation behavior
- Own run-level summaries and terminal logging
- Avoid owning detailed per-item fetch -> parse -> persist workflow
- Mark items as `processing` at the attempt boundary
- Mark terminal exception failures when retry policy is exhausted

## Pipelines

- Coordinate stage order
- Invoke controllers rather than reaching into stage internals

The `cs2a` CLI entry point is intentionally thin and is not the primary architectural cleanup target.

## Storage

- Match/map/player writes belong in storage modules (`match_storage.py`,
  `map_storage.py`, `player_storage.py`)
- Shared DB connection/cursor concerns belong in `storage/database.py`
- `Database.transaction()` and `get_cursor()` raise `DatabaseConnectionError`
  when the connection was lost (closed, or unable to roll back) and
  `DatabaseOperationError` for a failure on a live connection, so callers can
  tell a transient transport failure from a data or statement error (#208)
- Structured data stays in relational tables
- Raise typed storage/database exceptions instead of logging terminal errors

## Timestamps

- Store and compute in UTC. The source audit columns on `matches`,
  `maps`, and `players` (#132) and the lifecycle columns on the three
  ingestion-state tables (#213) are `TIMESTAMPTZ`; the parsers write
  aware UTC and the ingestion-state writers let the database stamp rows
  with `now()`, so no client clock or timezone reaches storage. Older
  tables still declare plain `TIMESTAMP` columns and are converted as
  they are touched
- Source dates are UTC instants derived from the source's unix timestamp,
  never from the local clock: both the match and map parsers convert with
  `tz=dt.UTC` and keep the time of day (#214). The source stamps every
  map of a match with the match's start instant, so `MIN(maps.date)` is
  the match instant wherever a map parsed with a timestamp; migration
  `20261027_0007` used it to correct rows the old parser wrote.
  `matches.date` and `maps.date` are still naive `TIMESTAMP` columns
  holding those UTC values
- Discovery dates (`match_ingestion_state.match_date`) are the UTC
  calendar day the match started, written by the match stage from the
  match page and never overwritten by discovery; until a match is
  processed the row carries the UTC day of its listing entry's own
  instant, never the rendered section header, which the source groups in
  the browser's zone (#215, ADR-0020)
- Never pass a Python `datetime.now()` as a lifecycle timestamp parameter
- Convert only at the presentation layer: operator output goes through
  `cs2_analytics.utils.time_format.format_local`, which renders
  America/Chicago in 12-hour form. Queries, logs, and JSON stay in UTC

## Ingestion and Discovery State Tables

- Stored in PostgreSQL
- Current code uses `match_ingestion_state`, `map_ingestion_state`, and `demo_ingestion_state`
- Treat those tables as lifecycle/state tables for discovered entities, not only transient queues
- Keep lifecycle fields distinct and avoid redundant timestamps
- Raise typed state-table exceptions instead of logging terminal errors
