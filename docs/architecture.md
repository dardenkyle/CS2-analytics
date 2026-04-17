# Architecture

## Overview

This project is moving from an older queue-oriented scraping design toward a cleaner ingestion-state-driven architecture.

The current code still uses PostgreSQL tables named `match_scrape_queue` and `map_scrape_queue`, and the active controllers still own more per-item workflow than the desired design. This document describes the current direction without implying that all refactors have already happened.

## Current Architectural Focus

- `main.py` and the top-level pipeline are not the main architectural problem
- the main cleanup target is `MatchController` and `MapController`
- the priority is to clarify ingestion/discovery state semantics before adding dbt or Airflow
- demo processing remains deferred until the match/map stages have cleaner boundaries

## Current Flow

Current code path:

results discovery -> `match_scrape_queue` row creation -> match stage processing -> `map_scrape_queue` row creation -> map stage processing -> relational storage -> API/data consumers

In the current implementation, discovery inserts newly found rows but does not yet refresh existing rows with lifecycle signals such as `last_seen_at`.

Demo processing is intentionally staged for later and remains decoupled from the active match/map flow.

## Architectural Direction

The architecture should be centered on explicit lifecycle/state tracking for discovered entities.

For match and map discovery, the PostgreSQL tables currently named `match_scrape_queue` and `map_scrape_queue` are evolving away from simple transient work queues and toward source-of-truth lifecycle tables. Their future names may move closer to that purpose, such as `match_ingestion_state` and `map_ingestion_state`, but the current code still uses the existing names.

The intended design is:

- discovery creates or refreshes lifecycle rows for matches and maps
- stage-specific processing reads from those lifecycle rows
- per-item stage workflow is handled by dedicated stage services
- controllers stay thin and focus on batch-level concerns
- dbt is added only after ingestion semantics and stage boundaries are stable
- Airflow is added only after dbt exists and the stage boundaries are clean

## Stage Responsibilities

### Results Stage

Primary responsibility:

- fetch results pages
- discover match identifiers and URLs
- create or refresh lifecycle rows for discovered matches

This stage should not parse match detail pages or write match records directly.

### Match Stage

Primary responsibility:

- select match lifecycle rows that are ready for processing
- fetch match detail pages
- parse match metadata and follow-up links
- persist match records and discovered downstream references
- update match lifecycle state and create or refresh map/demo follow-up state

### Map Stage

Primary responsibility:

- select map lifecycle rows that are ready for processing
- fetch map pages
- parse map-level player statistics
- persist parsed outputs through centralized storage modules
- update map lifecycle state

This is still the last active stage in the current hardened pipeline.

## Component Boundaries

### Pipeline Entry Point

The top-level pipeline should remain simple:

- coordinate stage order
- invoke controllers
- avoid owning per-item workflow logic

### Controllers

Controllers should mainly handle:

- batch coordination
- retry policy
- scraper reset and rotation
- run-level summary logging
- stage-level failure policy

Controllers should not remain the long-term home for per-item fetch -> parse -> persist -> state-transition logic.

### Stage Services

The next refactor should introduce `MatchStageService` and `MapStageService`.

Those services should own per-item stage workflow, including:

- reading one lifecycle row
- calling the scraper
- calling the parser
- calling storage/persistence modules
- applying lifecycle updates for success, retryable failure, or terminal failure

### Scrapers

- fetch remote content only
- no parsing
- no domain persistence
- no lifecycle-state transitions

### Parsers

- parse fetched content into structured outputs only
- no orchestration logic
- no persistence
- no lifecycle-state transitions

### Storage

- centralize relational writes
- own database access and persistence concerns
- avoid duplicating write logic inside controllers or stage services

## Ingestion and Discovery State Tables

For the active match and map stages, the PostgreSQL tables currently named `match_scrape_queue` and `map_scrape_queue` should be treated as lifecycle/state tables first and work queues second.

That means they should eventually describe:

- when an entity was first discovered
- when it was last seen in discovery
- whether it is ready for processing
- whether processing was attempted
- whether it succeeded or failed
- what run or worker last touched it

These tables are expected to gain clearer audit/lifecycle semantics before any dbt or Airflow rollout.

## Deferred Demo Stage

Demo support exists in the codebase, but end-to-end demo processing is not part of the active pipeline yet.

Current reality:

- demo URLs are discovered during match processing
- demo-specific scraper, parser, storage, and queue components exist
- the production path still stops after the map stage

Demo work stays separate because it introduces different operational concerns:

- binary download and temporary file lifecycle handling
- heavier parse cost and longer-running jobs
- event-level extraction with a larger output surface
- cleanup requirements for local demo artifacts

The demo stage should stay deferred until:

- match/map lifecycle semantics are stable
- controller responsibilities are reduced
- stage services exist for active stages
- downstream storage and transformation needs are clearer

## Recommended Implementation Sequence

1. Review schema and lifecycle semantics for the current match/map discovery tables.
2. Update the current `match_scrape_queue` and `map_scrape_queue` tables to reflect ingestion/discovery state more clearly.
3. Refactor `MatchController` and `MapController` by introducing `MatchStageService` and `MapStageService`.
4. Implement dbt models after ingestion/state semantics are stable.
5. Implement Airflow after dbt exists and the stage boundaries are clean.

## Rules

- Do not tightly couple match -> map -> demo in one synchronous flow
- Each stage should remain independently runnable
- Do not let dbt absorb ingestion responsibilities
- Do not let orchestration concerns drive schema semantics prematurely
