# Current Architecture State

This document summarizes the active architecture as of Phase 3.6. For the
longer architecture overview, see `docs/architecture/overview.md`.

## Active Runtime Flow

The active production path is:

```text
results discovery
-> match_ingestion_state refresh
-> MatchController batch processing
-> MatchStageService per-match workflow
-> map_ingestion_state refresh
-> MapController batch processing
-> MapStageService per-map workflow
-> relational storage
-> API/data consumers
```

The production path stops after map processing. Demo support exists as a
boundary but remains deferred.

## Stable Source Grains

Phase 3.5 made the active parsed-source tables ready for downstream dbt staging:

- `matches`: one row per match
- `maps`: one row per played map
- `players`: one row per player per map

`cs2_analytics/storage/schema.sql` remains the current schema source of truth
until deployment baseline work introduces versioned migrations.

`docs/schema_target_pre_dbt.md` remains planning guidance only until implemented.

## Ingestion-State Tables

The active ingestion-state tables are:

- `match_ingestion_state`
- `map_ingestion_state`
- `demo_ingestion_state`

They are lifecycle/state tables for discovered entities, not simple transient
work queues.

Lifecycle fields must stay distinct:

- `first_seen_at`
- `last_seen_at`
- `last_attempted_at`
- `last_processed_at`
- `last_failed_at`
- `failure_count`
- `last_error_message`
- `source`
- `priority`
- `last_updated_at`

Do not add `inserted_at` or `last_inserted_at` to ingestion-state tables.

## Component Boundaries

Controllers own:

- batch coordination
- retry policy and retry exhaustion behavior
- scraper reset and rotation
- run-level summaries

Stage services own:

- per-item fetch, parse, persist, and lifecycle outcome workflow
- normal processed, failed, and skipped state transitions
- returning `StageItemResult` for controller summaries

Scrapers fetch remote content only.

Parsers convert fetched content into structured outputs only.

Storage modules centralize relational writes.

Pipelines coordinate stage order and should stay thin.

## Deferred Demo Boundary

Demo URLs may be discovered during match processing, and demo-specific scraper,
parser, storage, ingestion-state, and stage-service components exist.

Full demo download, parse, event extraction, and local artifact cleanup remain
deferred until after the initial dbt layer exists and downstream demo needs are
clearer.

## Transformation And Orchestration Boundary

Phase 3.75 deployment baseline comes before dbt. The deployment baseline should
prove that runtime configuration, migrations, containers, CI, and smoke tests
work outside the local development machine.

dbt will be added after the deployment baseline and must remain downstream of
ingestion. It should transform stable source tables, not own ingestion logic or
application/source schema.

Airflow comes after dbt and must not drive schema semantics prematurely.
