# Current Architecture State

This document summarizes the active architecture as of the shipped dbt
transformation layer and its operations baseline (Phases 2-4 and frontend
Phase A complete; Phase 4.5 dbt operations and depth in progress). For
the longer architecture overview, see `docs/architecture/overview.md`.

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

Phase 3.5 stabilized the active parsed-source tables, which the dbt staging
layer now consumes as sources:

- `matches`: one row per match
- `maps`: one row per played map
- `players`: one row per player per map

Alembic now owns the application/source schema for deployed environments. The
initial migration mirrors the active `cs2_analytics/storage/schema.sql` tables,
constraints, ingestion-state lifecycle fields, and setup indexes. Keep
`schema.sql` aligned as a readable schema reference while migration ownership is
being established.

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

Lifecycle reconciliation (#141): the claim is not crash-safe -
`mark_as_processing` commits before an item is processed and the terminal
status is written only afterward - so an interrupted run (Ctrl+C, crash,
kill) leaves rows stuck in `processing`, which `fetch()` never selects.
`MatchController.run()` and `MapController.run()` therefore start by
resetting every `processing` row in their table back to `discovered`
(logging a warning with the count), before batch selection. This relies
on the pipeline being single-process; parallel runs would require
lease-based claiming instead.

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
- results discovery persistence (`ResultsStageService` records discovered
  matches; the scraper only yields them)

Scrapers fetch remote content only. This is enforced by
`tests/scrapers/test_scraper_boundaries.py`, which fails if any scraper
module imports storage or ingestion-state modules.

Parsers convert fetched content into structured outputs only.

Storage modules centralize relational writes.

Pipelines coordinate stage order and should stay thin.

## Deferred Demo Boundary

Demo URLs may be discovered during match processing and are recorded in
`demo_ingestion_state`. The non-working demo scraper, parser, storage,
controller, and stage-service implementation was moved off `main` to the
`feature/demo-parsing` branch.

Full demo download, parse, event extraction, and local artifact cleanup remain
deferred; the initial dbt layer now exists, but downstream demo needs are
still unclear.

## Transformation And Orchestration Boundary

The Phase 3.75 deployment baseline is complete and deployed: the API runs as
a Render web service against Render PostgreSQL, the React SPA frontend
publishes to GitHub Pages from `main`, and a manual GitHub Actions workflow
exists for the pipeline/scraper runner (currently paused; its containerized
browser validation is tracked by #91, and cloud scraping remains blocked by
#66, so data refreshes run locally against the production database).
Scheduled scraper runs stay deferred until match and map batch behavior is
validated. Manual migrations remain the release path, with write-based smoke
checks limited to separate smoke or staging databases and production
validation kept read-only.

The Phase 4 dbt transformation layer is built and is now a scheduled
production runtime component (#146): the Scheduled dbt Build workflow
(`.github/workflows/scheduled-dbt-build.yml`) runs a `dbt source freshness`
gate and then `dbt build` daily against the deployed database, using the
repository's `DB_*` Actions secrets through the `prod` profile target. Its
read/write boundary: dbt reads the Alembic-owned `public` ingestion tables
as sources only and writes exclusively to the `analytics` schema (models
and the SCD2 snapshot). The API's read path consumes the `analytics`
marts (#150), so the marts are the serving contract and the ingestion
schema has no direct API consumers. The read-only rule for production validation above
applies to the application/ingestion surface; the scheduled dbt build's
`analytics`-schema writes are the deliberate exception.

Normal database setup applies Alembic migrations through
`alembic -c cs2_analytics/alembic.ini upgrade head` or
`python manage_db.py --init`. Destructive table wipes remain explicit and
interactive.

The local container runtime now packages the existing Python entrypoints without
changing ingestion responsibilities:

- API: `python run_api.py`
- migrations: `python manage_db.py --init`
- pipeline: `python main.py`
- deployment smoke: `python scripts/deployment_smoke.py`
- worker browser validation: `python scripts/validate_worker_browser.py`

`docker-compose.yml` provides local PostgreSQL plus app, migration, pipeline,
and smoke services. The smoke service is deterministic: it verifies migrated
source tables, removes stale fixed-ID smoke rows, seeds source rows through
existing storage upserts, checks `/health`, confirms the top players API can
query PostgreSQL, and removes the fixed-ID rows before exiting. It should run
against a local or deployment-validation database rather than a production
analytics database. Runtime artifacts such as logs stay mounted from the
working tree and are not baked into the image.

The first cloud worker path is a manual GitHub Actions workflow,
`Manual Pipeline Worker`, that builds the same Docker image, validates
Selenium/Chromium inside the container, and optionally runs `python main.py`
against the configured PostgreSQL database. It is manual-only and serialized so
scheduled ingestion remains deferred until live match/map batch behavior is
validated.

The first Render API deployment is reachable at
`https://cs2-analytics.onrender.com`. Production `/health` and DB-backed
`/api/top_players` validation have passed against Render PostgreSQL, and local
Docker worker validation has proven that Selenium/Chromium can start inside the
same application image used by the manual worker path.

Local Docker live pipeline execution also completed in the worker image against
Render PostgreSQL and reached map processing. That run exposed a map scraper
validation gap where fetched map HTML could lack the expected
`match-info-box` page content. Issue #57 hardened the map scraper so missing,
incomplete, blocked, or challenged map stats HTML is classified as a retryable
scraper/session failure before parser handling, with diagnostics for the
requested URL, current browser URL, page title, source length, challenge marker
flags, and a short page snippet. Real map parser failures remain parser
failures.

Write-based deterministic smoke checks are intentionally not run against the
production Render PostgreSQL database. A separate smoke/staging database is
deferred until recurring deployment validation needs one; until then,
production validation stays read-only and limited live ingestion validation is
used to prove the deployed pipeline path.

dbt is in place and remains downstream of ingestion: it transforms the stable
source tables and owns neither ingestion logic nor the application/source
schema. It runs on the daily scheduled workflow described under
Transformation And Orchestration Boundary.

Airflow comes after dbt maturity and must not drive schema semantics
prematurely; the scheduled dbt workflow is the interim orchestration Airflow
would replace.
