# Decision Log

This file records accepted architecture and workflow decisions. Entries use a
lightweight ADR style: status, date, context, decision, and consequences.

## ADR-0001: Use Ingestion-State Tables Instead Of Scrape Queues

Status:
Accepted

Date:
Phase 1 / Phase 2

Context:
The old queue terminology did not describe the real lifecycle of discovered
matches, maps, and demos. The system needed rediscovery, retry, processed,
failed, and skipped semantics without treating rows as disposable work items.

Decision:
Use PostgreSQL-backed `match_ingestion_state`, `map_ingestion_state`, and
`demo_ingestion_state` tables as lifecycle/state tables.

Consequences:
- Source IDs remain primary keys.
- Rediscovery refreshes existing rows instead of duplicating work.
- Lifecycle fields stay explicit and distinct.
- Ingestion-state tables must not use parsed-source audit fields such as
  `inserted_at` or `last_inserted_at`.

## ADR-0002: Split Batch Controllers From Per-Item Stage Services

Status:
Accepted

Date:
Phase 3

Context:
Controllers had grown too responsible for one-item fetch, parse, persist, and
lifecycle behavior. The project needed clearer boundaries before stabilizing
storage outputs and adding downstream transformation work.

Decision:
Controllers own batch-level concerns, while stage services own per-item stage
workflow.

Consequences:
- Controllers own retry policy, scraper reset/rotation, summaries, and retry
  exhaustion.
- Stage services own per-item fetch, parse, persist, and lifecycle outcomes.
- Scrapers remain fetch-only.
- Parsers remain parse-only.
- Storage modules centralize relational writes.

## ADR-0003: Stabilize Match, Map, And Player Source Grains Before dbt

Status:
Accepted

Date:
Phase 3.5

Context:
dbt staging models need stable relational source tables and joinable
relationships. The project needed to avoid parsing stringified links or
duplicating rows during reruns.

Decision:
Make `matches`, `maps`, and `players` stable, idempotent parsed-source tables
before initializing dbt.

Consequences:
- `matches` is one row per match.
- `maps` is one row per played map.
- `players` is one row per player per map.
- Storage upserts refresh trusted fields without duplicating rows.
- dbt staging can start from `stg_matches`, `stg_maps`, and `stg_players`
  after deployment baseline work is complete.

## ADR-0004: Complete Deployment Baseline Before dbt

Status:
Accepted

Date:
2026-05-20

Context:
Phase 3.5 made the active source tables ready for dbt, but the project still
needs reproducible runtime setup, environment-driven configuration, migrations,
containers, CI, and deployment smoke tests.

Decision:
Complete Phase 3.75 deployment baseline before Phase 4 dbt initialization.

Consequences:
- Phase 3.75 follows Phase 3.6.
- dbt remains the next analytics layer, but starts only after runtime and
  deployment assumptions are reproducible.
- Application/source schema moves to Alembic during deployment baseline work
  before dbt owns downstream transformation models.
- Airflow remains deferred until after dbt.

## ADR-0005: Keep Demo Expansion Deferred

Status:
Accepted

Date:
Phase 3 / Phase 3.5

Context:
Demo processing introduces binary downloads, temporary file lifecycle,
long-running parse work, event-level extraction, and cleanup requirements.
Those concerns are larger than the active match/map ingestion surface.

Decision:
Keep demo support as a boundary, but defer full demo download and parsing until
after the initial dbt layer exists and downstream demo needs are clearer.

Consequences:
- `DemoStageService` can preserve the stage boundary without expanding active
  runtime scope.
- The production path still stops after map processing.
- Demo expansion should not be bundled into deployment baseline or dbt staging
  work.

## ADR-0006: Use Alembic For Application Source Schema

Status:
Accepted

Date:
2026-05-21

Context:
Deployment baseline work needs a reproducible, non-destructive way to create
and upgrade application/source tables outside one local development database.
The previous setup path executed `schema.sql` directly and created indexes from
Python setup code.

Decision:
Use Alembic migrations for application/source schema ownership. The initial
migration mirrors the active `schema.sql` table shape, constraints,
ingestion-state lifecycle fields, and setup indexes. Normal setup runs
`alembic -c cs2_analytics/alembic.ini upgrade head` through
`python manage_db.py --init`.

Consequences:
- Deployed environments update schema through Alembic.
- `schema.sql` remains a readable schema reference during the migration
  ownership transition and must stay aligned when schema changes occur.
- Ingestion-state tables keep their lifecycle fields and do not gain
  parsed-source audit fields.
- dbt remains downstream and will not manage application/source schema.

## ADR-0007: Use Issue-Driven, Reviewable Branches

Status:
Accepted

Date:
Phase 3.6

Context:
The project is moving from ad hoc development toward small, reviewable changes
before deployment hardening begins.

Decision:
Use issue-driven branches, a PR template with scope/risk/documentation checks,
repo-tracked labels, and explicit agent/human review policy.

Consequences:
- Branches should be scoped to one issue or one clear roadmap item.
- PRs must document scope, out-of-scope work, risk, verification, and
  documentation impact.
- Medium-risk, high-risk, schema, deployment, dependency, CI, and architecture
  changes require human review before merge.
