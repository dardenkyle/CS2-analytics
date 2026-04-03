# Conventions

## Scrapers

- Fetch remote content only
- No parsing
- No domain-table writes
- Queue failure/status updates are allowed when needed

## Parsers

- Extract structured data only
- No orchestration logic
- No queue state transitions in normal flow

## Pipelines

- Coordinate workflow
- Handle queue interaction
- Call scrapers and parsers

## Storage

- Match/player writes belong in storage modules (`match_storage.py`, `player_storage.py`)
- Shared DB connection/cursor concerns belong in `storage/database.py`
- Structured data stays in relational tables

## Queues

- Stored in PostgreSQL
- Current statuses: `queued`, `parsed`, `failed`
- Include retry and error tracking metadata
