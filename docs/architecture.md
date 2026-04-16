# Architecture

## Overview

This project is a backend and data-engineering pipeline for collecting and analyzing CS2 match data.

## Current Flow

Results scraping -> match queue -> match scraping/parsing -> map queue -> map scraping/parsing -> storage/API consumption

Demo processing is intentionally staged for later and remains decoupled.

## Stage Responsibilities

### Results Stage

Primary responsibility:

- scrape results pages
- discover match URLs
- enqueue match jobs into `match_scrape_queue` with initial status `queued`

This stage does not parse match detail pages or write match records directly.

### Match Stage

Primary responsibility:

- fetch queued match jobs
- scrape match detail pages
- parse match metadata and follow-up links
- persist match records
- enqueue map and demo follow-up jobs
- mark processed queue rows as `parsed` or `failed`

This stage is the handoff point between result discovery and downstream map/demo work.

### Map Stage

Primary responsibility:

- fetch queued map jobs
- scrape map pages
- parse map-level player statistics
- persist player stat rows derived from the map page
- mark processed queue rows as `parsed` or `failed`

This is the last active stage in the current hardened pipeline.

## Principles

- Separation of concerns
- Queue-based handoff between stages
- Restartable and retry-aware processing
- Domain writes owned by storage modules
- Controllers own orchestration logic

## Key Decisions

- Scrapers fetch content only
- Parsers extract structured data only
- Controllers orchestrate queue transitions and persistence handoff
- Results-stage retry exhaustion fails the run; match/map item exhaustion marks failed and continues
- Queues stay PostgreSQL-backed
- Demo-related work remains deferred until much later in development (TBD)
- The next major phase is dbt

## Deferred Demo Stage

Demo support exists in the codebase, but end-to-end demo processing is not part of the active pipeline yet.

Current reality:

- demo URLs are discovered and queued during match processing
- demo-specific scraper, parser, storage, and queue components exist
- the production path still stops after the map stage

Demo work stays separate because it introduces different operational concerns:

- binary download and temporary file lifecycle handling
- heavier parse cost and longer-running jobs
- event-level extraction with a larger output surface
- cleanup requirements for local demo artifacts

The demo stage should stay deferred until:

- match/map ingestion hardening is stable
- queue handling behavior is reliable
- orchestration strategy is chosen
- downstream storage and transformation needs are clearer

When enabled, the demo stage should be responsible for:

- fetching queued demo jobs
- downloading the demo file
- parsing the `.dem` payload into structured outputs
- persisting demo-derived results and error metadata
- cleaning up temporary demo files after processing

## Rules

- Do not tightly couple match -> map -> demo in one synchronous flow
- Each stage should remain independently runnable
