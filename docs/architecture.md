# Architecture

## Overview

This project has moved from an older queue-oriented scraping design toward a cleaner ingestion-state-driven architecture.

The schema uses PostgreSQL ingestion-state tables directly, and the active match, map, and demo stages now separate batch orchestration from per-item workflow through stage services.

## Current Architectural Focus

- `main.py` and the top-level pipeline remain intentionally thin
- `MatchController`, `MapController`, and `DemoController` own batch-level concerns
- stage services own per-item fetch, parse, persist, and lifecycle outcome work
- demo processing remains deferred even though it now has a placeholder stage service boundary
- dbt is the next planned phase; Airflow remains later

## Current Flow

Current code path:

results discovery -> `match_ingestion_state` refresh -> match stage processing -> `map_ingestion_state` refresh -> map stage processing -> relational storage -> API/data consumers

In the current implementation, discovery refreshes existing rows with lifecycle signals such as `last_seen_at` while preserving source IDs as primary keys.

Demo processing is intentionally staged for later and remains decoupled from the active match/map flow.

## Architectural Direction

The architecture is centered on explicit lifecycle/state tracking for discovered entities.

For match and map discovery, the PostgreSQL tables `match_ingestion_state` and `map_ingestion_state` are source-of-truth lifecycle tables rather than simple transient work queues.

The intended design is:

- discovery creates or refreshes lifecycle rows for matches and maps
- stage-specific processing reads from those lifecycle rows
- per-item stage workflow is handled by dedicated stage services
- controllers stay thin and focus on batch-level concerns
- dbt is added after ingestion semantics and stage boundaries are stable
- Airflow is added only after dbt exists and the stage boundaries are clean

## Stage Responsibilities

### Results Stage

Primary responsibility:

- fetch results pages
- discover match identifiers and URLs
- create or refresh match lifecycle rows for discovered matches

Current implementation note:

- `ResultsScraper` currently performs discovery-time lifecycle-row refreshes in `match_ingestion_state`
- rediscovery refreshes already happen in the current implementation

This stage should not parse match detail pages or write match records directly.

### Match Stage

Primary responsibility:

- select match lifecycle rows that are ready for processing
- delegate one-match workflow to `MatchStageService`
- apply retry, reset, rotation, and summary policy at the batch level

`MatchStageService` owns match detail fetch, parsing, match persistence, follow-up map/demo discovery refreshes, and normal lifecycle outcomes.

### Map Stage

Primary responsibility:

- select map lifecycle rows that are ready for processing
- delegate one-map workflow to `MapStageService`
- apply retry, reset, rotation, and summary policy at the batch level

`MapStageService` owns map fetch, parsing, player persistence, and normal lifecycle outcomes.

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

Controllers should not own per-item fetch -> parse -> persist -> state-transition logic.

### Stage Services

Stage services own per-item stage workflow, including:

- calling the scraper
- calling the parser
- calling storage/persistence modules
- applying normal lifecycle updates for processed, failed, or skipped outcomes
- returning `StageItemResult` to controllers for summary counting

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

For the active match and map stages, the PostgreSQL tables `match_ingestion_state` and `map_ingestion_state` are lifecycle/state tables first and work queues second.

They now describe:

- when an entity was first discovered
- when it was last seen in discovery
- whether it is ready for processing
- whether processing was attempted
- whether it succeeded or failed
- the latest failure or skipped reason, when applicable

## Deferred Demo Stage

Demo support exists in the codebase, but end-to-end demo processing is not part of the active pipeline yet.

Current reality:

- demo URLs are discovered during match processing
- demo-specific scraper, parser, storage, ingestion-state, and stage-service components exist
- the production path still stops after the map stage

Demo work stays separate because it introduces different operational concerns:

- binary download and temporary file lifecycle handling
- heavier parse cost and longer-running jobs
- event-level extraction with a larger output surface
- cleanup requirements for local demo artifacts

The demo processing implementation should stay deferred until:

- the initial dbt transformation layer exists
- downstream demo storage and transformation needs are clearer

## Recommended Implementation Sequence

1. Keep the current `*_ingestion_state` tables stable.
2. Keep controller/stage-service responsibilities clean as ingestion evolves.
3. Implement dbt models over the stable `matches`, `maps`, and `players`
   parsed-source grains.
4. Implement Airflow after dbt exists and the stage boundaries are clean.

## Rules

- Do not tightly couple match -> map -> demo in one synchronous flow
- Each stage should remain independently runnable
- Do not let dbt absorb ingestion responsibilities
- Do not let orchestration concerns drive schema semantics prematurely
