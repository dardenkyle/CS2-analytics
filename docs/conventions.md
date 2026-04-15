# Conventions

## Scrapers

- Fetch remote content only
- No parsing
- No domain-table writes
- No queue status transitions in the active controller-driven flow

## Parsers

- Extract structured data only
- No orchestration logic
- No queue state transitions
- No storage writes
- Raise typed parse exceptions with specific helper-level messages

## Controllers

- Coordinate workflow
- Handle queue interaction and queue status transitions
- Call scrapers, parsers, and storage modules
- Own terminal error logging and queue failure outcomes

## Pipelines

- Coordinate stage order
- Invoke controllers rather than reaching into scraper/parser internals

## Storage

- Match/player writes belong in storage modules (`match_storage.py`, `player_storage.py`)
- Shared DB connection/cursor concerns belong in `storage/database.py`
- Structured data stays in relational tables
- Raise typed storage/database exceptions instead of logging terminal errors

## Queues

- Stored in PostgreSQL
- Current statuses: `queued`, `parsed`, `failed`
- Include retry and error tracking metadata
- Raise typed queue exceptions instead of logging terminal errors
