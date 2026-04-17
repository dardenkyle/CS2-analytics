# Conventions

## Scrapers

- Fetch remote content only
- No parsing
- No domain-table writes
- Match/map scrapers should not own lifecycle-state transitions

Current implementation note:

- `ResultsScraper` still performs discovery-time queue insertion into `match_scrape_queue`
- that behavior reflects the current codebase, not the long-term target boundary
- over time, discovery-state mutation should move out of `ResultsScraper` and into a cleaner stage-oriented boundary

## Parsers

- Extract structured data only
- No orchestration logic
- No lifecycle-state transitions
- No storage writes
- Raise typed parse exceptions with specific helper-level messages

## Stage Services

- Own per-item stage workflow
- Call scrapers, parsers, and storage modules in order
- Apply lifecycle updates for success, retryable failure, and terminal failure
- Keep stage-specific processing rules out of controllers

Planned near-term services:

- `MatchStageService`
- `MapStageService`

## Controllers

- Coordinate batches of work
- Own retry policy and retry exhaustion behavior
- Own scraper reset and rotation behavior
- Own run-level summaries and terminal logging
- Avoid owning detailed per-item fetch -> parse -> persist workflow

## Pipelines

- Coordinate stage order
- Invoke controllers rather than reaching into stage internals

The top-level pipeline is intentionally thin and is not the primary architectural cleanup target.

## Storage

- Match/player writes belong in storage modules (`match_storage.py`, `player_storage.py`)
- Shared DB connection/cursor concerns belong in `storage/database.py`
- Structured data stays in relational tables
- Raise typed storage/database exceptions instead of logging terminal errors

## Ingestion and Discovery State Tables

- Stored in PostgreSQL
- Current code uses names like `match_scrape_queue` and `map_scrape_queue`
- Treat those tables as lifecycle/state tables for discovered entities, not only transient queues
- Keep lifecycle fields distinct and avoid redundant timestamps
- Raise typed state-table exceptions instead of logging terminal errors
