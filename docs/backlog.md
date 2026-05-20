# Backlog

This document tracks the recommended implementation order for the next architecture cleanup phases.

---

## Current Position

Phase 3 and Phase 3.5 are complete for the active match/map/player ingestion
surface. The active codebase now has stable stage-service boundaries,
controller retry hardening, relational match/map/player storage contracts, and
the focused dbt-readiness coverage needed to start dbt staging work.

Current priorities:

- move development into an issue-driven, reviewable workflow before deployment
  hardening begins
- establish a reproducible deployment baseline before adding dbt
- then initialize dbt without moving ingestion responsibilities into dbt
- keep `docs/schema_target_pre_dbt.md` as planning guidance for later parsed
  source schema normalization
- defer demo expansion and Airflow until after the initial dbt layer exists

---

## Phase 1: Schema and Lifecycle Review

Goal:
Define the intended meaning of the scrape queue tables before changing schema or code structure around them.

Status:
Complete. The project will move from scrape queue terminology toward ingestion state tables. See `docs/ingestion_lifecycle.md`.

### Completed work

- [x] Reviewed the actual role of the scrape queue tables
- [x] Decided they are lifecycle/state tables, not simple work queues
- [x] Documented the intended status model and field semantics
- [x] Identified redundant versus meaningful timestamps
- [x] Defined naming guidance for current-state versus future-state terminology
- [x] Kept `cs2_analytics/storage/schema.sql` as the source of truth during the review

---

## Phase 2: Ingestion State Table Updates

Goal:
Renamed and updated the former scrape queue tables so they clearly support ingestion/lifecycle tracking.

Status:
Complete. The active schema, controllers, and tests now use `*_ingestion_state` naming and lifecycle fields directly.

### Completed work

- [x] Update `cs2_analytics/storage/schema.sql` to match the Phase 1 ingestion state decisions
- [x] Rename `match_scrape_queue`, `map_scrape_queue`, and `demo_scrape_queue` to `match_ingestion_state`, `map_ingestion_state`, and `demo_ingestion_state`
- [x] Update lifecycle fields to the agreed Phase 1 shape: `status`, `first_seen_at`, `last_seen_at`, `last_attempted_at`, `last_processed_at`, `last_failed_at`, `failure_count`, `last_error_message`, `source`, `priority`, and `last_updated_at`
- [x] Remove or avoid redundant fields such as `inserted_at`, `last_inserted_at`, unused `retry_count`, `run_id`, and `worker_id`
- [x] Update status values from `queued`, `parsed`, `failed` to `pending`, `processing`, `processed`, `failed`, and `skipped`
- [x] Preserve idempotency by keeping source IDs as primary keys and refreshing existing rows on rediscovery
- [x] Update Python queue/state classes, controllers, and tests to use the new table names and status values
- [x] Keep demo behavior minimal while aligning its table name and schema with ingestion state naming
- [x] Document success, retryable failure, terminal failure, skipped, and rediscovery semantics

### Completed PR sequence

1. Compatibility:
   Added `MatchIngestionState`, `MapIngestionState`, and `DemoIngestionState` as the new ingestion-state manager classes.
2. Schema:
   Updated `cs2_analytics/storage/schema.sql` to create only the `*_ingestion_state` tables with the agreed Phase 1 fields and status values.
3. Migration/package rename:
   Moved ingestion-state modules into `cs2_analytics/ingestion_state/` and updated controllers/tests/imports to use the new naming.
4. Lifecycle behavior:
   Implemented rediscovery refreshes, processing transitions, lifecycle timestamps, failure counts, and skipped semantics. Removed `queues/` and all functionality related to previous queue-based scraping.

---

## Phase 3: Match and Map Stage Service Refactor

Goal:
Thin the active controllers by separating batch concerns from per-item stage workflow.

Status:
Complete. Match, map, and demo controllers now delegate per-item workflow to stage services and consume an explicit per-item result contract for controller summaries.

### Planned work

- [x] Introduce `MatchStageService`
- [x] Introduce `MapStageService`
- [x] Introduce `DemoStageService` (even though demo service layer development is paused)
- [x] Move per-item fetch -> parse -> persist -> state-transition logic into stage services
- [x] Keep controller ownership of batch coordination, retry policy, scraper reset/rotation, and summary logging
- [x] Keep scrapers fetch-only, parsers parse-only, and persistence centralized
- [x] Add or update tests around per-item stage outcomes and controller summaries
- [x] Normalize stage service outcomes with an explicit result contract

### Suggested branch sequence

Keep each branch small enough to review independently, and keep the active
pipeline runnable after every merge. Phase 3 should avoid schema changes unless
a later branch proves they are necessary.

1. [x] `phase3-stage-service-shells`
       Add `cs2_analytics/stage_services/`, lightweight service classes, package
       exports, and import-level tests. Do not change controller behavior yet.

2. [x] `phase3-match-stage-service`
       Move one-match fetch -> parse -> persist -> follow-up state refresh ->
       lifecycle update behavior into `MatchStageService`. Keep `MatchController`
       responsible for batch fetching, retry policy, scraper reset/rotation, and
       summary logging.

3. [x] `phase3-map-stage-service`
       Move one-map fetch -> parse -> persist -> lifecycle update behavior into
       `MapStageService`. Preserve existing controller retry and summary behavior.

4. [x] `phase3-demo-stage-placeholder`
       Add a minimal `DemoStageService` that reflects current demo behavior without
       expanding the deferred demo pipeline scope.

5. [x] `phase3-controller-thinning-cleanup`
       Remove controller helper code made obsolete by the services, normalize any
       service result contracts, and update docs to reflect the completed Phase 3
       boundary.

### Phase 3 verification rule

Before merging each Phase 3 branch:

- [x] Run `python -m pytest` from the venv
- [x] Smoke test `python main.py` when the local scraper/database environment is available
- [x] Confirm controllers still own batch concerns and services own only per-item workflow
- [x] Confirm no dbt, Airflow, or schema work slipped into the branch

---

## Phase 3.5: dbt Readiness

Goal:
Make ingestion outputs stable, relational, and idempotent before adding dbt.

Status:
Complete. The active ingestion outputs have stable grains, duplicate-safe
upserts, relationship-readiness tests, and focused integration coverage for the
match-stage to map-stage handoff. dbt can begin with staging models over
`matches`, `maps`, and `players`.

### Schema target reference

`docs/schema_target_pre_dbt.md` captures the intended Phase 3.5 parsed-source
schema target for `matches`, `maps`, and `players`. Treat it as planning
guidance until implemented; `cs2_analytics/storage/schema.sql` remains the
active schema source of truth. The remaining schema-normalization items in that
document are deferred follow-up work, not blockers for initial dbt staging.

### Planned work

- [x] Add match context to discovered map rows so each map can be tied back to
      its parent match without parsing stringified link fields
- [x] Decide whether `map_order`, `map_name`, map scores, and map winner come
      from match pages, map pages, or both
- [x] Ensure the map stage writes one row per played map to `maps`
- [x] Keep `players` at the grain of one row per player per map
- [x] Make `cs2_analytics/storage/map_storage.py` match the active
      `cs2_analytics/storage/schema.sql`
- [x] Update `store_maps` to upsert all trusted map fields, or remove stale map
      storage code if it no longer has a role
- [x] Update `store_matches` conflict behavior to refresh trusted parsed fields,
      not only `last_updated_at`
- [x] Decide which player context fields should refresh on rerun, such as
      `player_name`, `player_url`, `map_name`, `team_name`, and
      `last_scraped_at`
- [x] Update `store_players` conflict behavior to refresh the agreed trusted
      fields
- [x] Keep `matches.map_links` and `matches.demo_links` as trace/debug fields
      only if useful; dbt should not parse Python-list strings
- [x] Add storage idempotency tests for match, map, and player upserts
- [x] Add relationship readiness tests proving `players.map_id` joins to
      `maps.map_id` and `maps.match_id` joins to `matches.match_id`
- [x] Add a focused integration-style test for match discovery -> map discovery
      -> map/player persistence
- [x] Separate destructive schema reset behavior from normal schema
      initialization
- [x] Move `ALTER TABLE` and index mutation out of `Database.__init__` into an
      explicit schema/setup path
- [x] Clean up import-time global database connection behavior so importing
      storage modules does not require a live PostgreSQL database
- [x] Rename queue-era exception and test names where they affect active code
      readability

### Suggested branch sequence

Keep each branch focused and reviewable. Phase 3.5 should produce stable
relational ingestion outputs without starting dbt models yet.

1. [x] `phase3.5-map-discovery-context`
       Add parent `match_id` context to discovered map ingestion rows and document
       which map fields are known at match-discovery time.

   Match-discovery now records `match_id`, `map_id`, and `map_url` in
   `map_ingestion_state`. Richer map identity fields such as `map_order`,
   `map_name`, map scores, and map winner still need a separate source-of-truth
   decision before the map stage writes relational `maps` rows.

2. [x] `phase3.5-map-storage-contract`
       Align the `maps` schema, model, parser output, and `store_maps` behavior so
       the map stage can persist one row per played map.

   Map storage now uses `map_order` from match discovery order and parses
   `map_name`, map scores, map winner, and date from the map stats page. The
   active `maps` table includes map audit fields and `map_url`, and the map
   stage persists the map row before player rows.

3. [x] `phase3.5-storage-upsert-idempotency`
       Strengthen match, map, and player upserts so reruns refresh trusted fields
       without duplicating rows or overwriting first-seen style timestamps.

   Match storage now refreshes trusted parsed match fields on conflict while
   preserving `last_inserted_at`. Player storage refreshes the agreed context
   fields, metrics, scrape/update timestamps, and completeness flag on conflict
   while preserving `last_inserted_at`. Map storage already had the same update
   shape, and storage tests now assert the idempotent upsert contracts for all
   three parsed source tables.

   Audit-field naming cleanup is intentionally deferred to a later focused
   schema/model/storage branch. That branch should normalize parsed source
   tables toward `inserted_at`, `last_scraped_at`, `updated_at`, and
   `data_complete`, replacing current mixed names such as `last_inserted_at`
   and `last_updated_at`.

4. [x] `phase3.5-relationship-readiness-tests`
       Add focused tests that prove `players -> maps -> matches` joins work and
       that dbt will not need to parse stringified link fields.

5. [x] `phase3.5-schema-initialization-cleanup`
       Separate destructive schema reset behavior from normal initialization and
       move runtime schema mutation out of `Database.__init__`.

6. [x] `phase3.5-database-access-cleanup`
       Remove remaining import-time global database connection behavior, such as
       module-level `db = Database()` access paths, and move toward lazy or
       injectable database access where it improves tests and setup commands.

   Storage modules no longer create a live global `Database` connection at
   import time. Database access now favors explicit, lazy, or injectable paths
   so imports, tests, and setup commands do not require PostgreSQL until work
   actually needs a connection.

7. [x] `phase3.5-ingestion-terminology-cleanup`
       Rename queue-era exception and test names where they affect active
       ingestion-state readability.

   Queue-era typed exceptions are now named for ingestion-state operations,
   and the related tests live under `tests/ingestion_state/`. Active helper
   and call-site terminology now uses record/refresh language, including the
   ingestion-state chunk helper and batch refresh method, while preserving the
   existing per-item `queue()` API for discovered follow-up links.

8. [x] `phase3.5-dbt-readiness-final`
       Add the final focused integration coverage for match discovery -> map
       discovery -> map/player persistence, confirm the `matches`, `maps`, and
       `players` grains are stable, and update the dbt entry criteria once Phase
       3.5 is fully satisfied. Do not initialize dbt in this branch.

   Final readiness coverage now exercises the active match-stage to map-stage
   handoff with in-memory fakes and confirms the parsed-source grains:
   `matches` is one row per match, `maps` is one row per played map, and
   `players` is one row per player per map. Schema normalization items captured
   in `docs/schema_target_pre_dbt.md` remain deferred follow-up work rather than
   blockers for initial dbt staging.

### Source-table dbt readiness criteria

- [x] `matches`, `maps`, and `players` have stable grains
- [x] Map-player-match relationships are queryable without parsing strings
- [x] Storage upserts are duplicate-safe and refresh trusted fields
- [x] Tests pass
- [x] Source tables are ready for clean dbt staging models: `stg_matches`,
      `stg_maps`, and `stg_players`

---

## Phase 3.6: Issue-Driven Workflow and Agent Readiness

Goal:
Move the project from ad hoc development into issue-driven, reviewable,
agent-friendly implementation before deployment hardening begins.

Status:
In progress. The `phase3.6-issue-templates` branch has added GitHub issue
forms and a pull request template, and the `phase3.6-label-taxonomy` branch has
added the repo-tracked label taxonomy. Agent docs, workflow docs, and deployment
issue creation remain open.

### Planned work

- [x] Add GitHub issue templates
- [x] Add pull request template
- [x] Add labels for phase, type, priority, and risk
- [ ] Ensure `AGENTS.md` complies with repo rules and coding standards
- [ ] Add `docs/workflow.md` describing issue -> branch -> PR -> merge flow
- [ ] Add `docs/architecture/current_state.md` summarizing the active architecture
- [ ] Add `docs/architecture/decision_log.md` for project decisions
- [ ] Add documentation maintenance rules to `AGENTS.md`, `docs/workflow.md`,
      and the pull request template
- [ ] Convert Phase 3.75 deployment tasks into GitHub issues
- [ ] Create small acceptance criteria for each issue
- [ ] Create branch naming conventions
- [ ] Define what agents are allowed to change without approval
- [ ] Define what requires human review before merge

### Documentation maintenance rule

Agents must check whether their coding session changes any
documentation-relevant behavior.

Documentation must be updated when a change affects:

- architecture or module responsibilities
- setup/install commands
- environment variables or configuration
- database schema or migrations
- API routes, request/response behavior, or health checks
- pipeline execution flow
- deployment/runtime behavior
- test commands or CI behavior
- agent/developer workflow rules

Documentation does not need to be updated for purely internal refactors that do
not change behavior, setup, architecture boundaries, commands, or public
interfaces.

Every pull request must include a documentation check section:

## Documentation Check

- [ ] Docs updated
- [ ] Docs not needed

Reason:

If `Docs not needed` is selected, the PR must briefly explain why.

### Suggested branch sequence

1. [x] `phase3.6-issue-templates`
       Add GitHub issue templates and a pull request template.

   Covers:

   - GitHub issue templates
   - pull request template
   - pull request documentation check

2. [x] `phase3.6-label-taxonomy`
       Add labels for phase, type, priority, and risk.

   Covers:

   - phase labels
   - type labels
   - priority labels
   - risk labels

3. [ ] `phase3.6-agent-docs`
       Add `AGENTS.md`, workflow docs, current architecture summary, decision
       log, and agent/human review policy.

   Covers:

   - `AGENTS.md` repo rules and coding standards
   - `docs/workflow.md` issue -> branch -> PR -> merge flow
   - `docs/architecture/current_state.md`
   - `docs/architecture/decision_log.md`
   - documentation maintenance rules in `AGENTS.md` and `docs/workflow.md`
   - branch naming conventions
   - what agents may change without approval
   - what requires human review before merge

4. [ ] `phase3.6-create-deployment-issues`
       Convert Phase 3.75 work into small GitHub issues with clear scope,
       acceptance criteria, out-of-scope notes, and verification commands.

   Covers:

   - Phase 3.75 deployment tasks converted into GitHub issues
   - small acceptance criteria for each deployment issue

### Phase 3.6 exit criteria

- [ ] GitHub issues can be created from templates
- [ ] Pull requests have a consistent review checklist
- [ ] Pull requests include a documentation check
- [ ] `AGENTS.md` explains repo architecture, coding standards, and no-touch areas
- [ ] `AGENTS.md` explains documentation responsibilities
- [ ] `docs/workflow.md` explains documentation expectations
- [ ] Deployment baseline work is represented as small, reviewable issues
- [ ] Branch naming and issue-to-PR workflow are documented

---

## Phase 3.75: Deployment Baseline

Goal:
Make the current ingestion pipeline and API deployable in a reproducible,
containerized environment before adding dbt.

Status:
Not started.

Rationale:
Phase 3.5 confirms that the parsed-source tables are stable enough for dbt, but
the project still needs a reproducible runtime before adding another
architecture layer. Deployment baseline work should prove that the scraper,
database setup, API, environment variables, migrations, tests, and runtime
assumptions work outside the local development machine.

### Planned work

- [ ] Add `.env.example` with all required runtime variables
- [ ] Move dev-only config defaults out of production paths
- [ ] Make API host, port, CORS origins, debug mode, and database settings environment-driven
- [ ] Add Alembic for versioned application database migrations
- [ ] Convert the current `schema.sql` source tables into an initial Alembic migration
- [ ] Keep schema initialization non-destructive by default
- [ ] Add migration command documentation for local Docker and deployment usage
- [ ] Ensure deployed database updates through `alembic upgrade head`
- [ ] Add a `Dockerfile` for the application runtime
- [ ] Add `docker-compose.yml` for local deployment with app/API + PostgreSQL
- [ ] Add a dedicated pipeline runner command or module entrypoint
- [ ] Add a dedicated API runner command or deployment-safe Uvicorn command
- [ ] Add `/health` endpoint for API health checks
- [ ] Add GitHub Actions CI for lint, type check, and tests
- [ ] Add a deployment smoke test path:
      migrations -> limited ingestion -> API health/top players check
- [ ] Document local Docker startup and production deployment variables
- [ ] Choose first deployment target for the API and worker
- [ ] Choose temporary scheduling strategy for scraper runs before Airflow
- [ ] Confirm the system can run without relying on local machine state

### Suggested branch sequence

1. [ ] `phase3.75-env-config-hardening`
       Add `.env.example`, environment-driven runtime config, production-safe CORS
       config, debug toggles, and deployment-safe API host/port settings.

2. [ ] `phase3.75-alembic-migrations`
       Add Alembic, create the initial migration from the active schema, document
       migration commands, and make migrations the source of truth for deployed
       application/source tables.

3. [ ] `phase3.75-container-runtime`
       Add `Dockerfile`, `docker-compose.yml`, and documented local container
       startup flow for PostgreSQL, migrations, API, and pipeline runs.

4. [ ] `phase3.75-ci-gate`
       Add GitHub Actions for install, lint, type check, and tests. CI should become
       the minimum merge gate before dbt begins.

5. [ ] `phase3.75-deployment-smoke-test`
       Add a small deployment verification path that proves the container can run
       migrations, execute a limited ingestion pass, and start the API.

6. [ ] `phase3.75-first-cloud-deploy`
       Deploy the API and pipeline runner to the chosen initial platform. Keep the
       deployment simple and low-cost. Do not add Airflow yet.

### Phase 3.75 exit criteria

- [ ] Fresh clone can run through Docker without manual local setup
- [ ] Required environment variables are documented
- [ ] API binds correctly in a deployed/container environment
- [ ] PostgreSQL connection works through environment config
- [ ] Fresh database can be initialized through migrations
- [ ] Existing database can be upgraded without destructive reset
- [ ] App tables and ingestion-state tables are migration-managed
- [ ] Schema initialization is explicit and non-destructive by default
- [ ] CI passes on every PR
- [ ] A limited ingestion run works outside the local dev environment
- [ ] API health endpoint works in deployed environment
- [ ] There is a temporary scheduled/manual runner path before Airflow

---

## Phase 4: dbt Transformation Layer

Goal:
Add dbt after ingestion/state semantics are stable and the current runtime has a
reproducible deployment baseline.

### Phase 4 entry criteria

- [ ] Phase 3.6 issue-driven workflow is complete
- [ ] Phase 3.75 deployment baseline is complete
- [ ] Current ingestion pipeline can run outside the local dev machine
- [ ] Application/source tables are managed by Alembic migrations
- [ ] dbt will be additive and downstream of ingestion, not a replacement for ingestion logic

### Database ownership boundary

Alembic owns application/source schema:

- `matches`
- `maps`
- `players`
- `match_ingestion_state`
- `map_ingestion_state`
- `demo_ingestion_state`
- indexes
- constraints
- source-table schema changes

dbt owns analytics transformations:

- `stg_matches`
- `stg_maps`
- `stg_players`
- intermediate models
- fact models
- dimension models
- analytics tests
- lineage/docs

dbt should not manage the core ingestion schema that the Python application
writes into.

### Planned work

- [ ] Initialize dbt project
- [ ] Create staging models (`stg_matches`, `stg_maps`, `stg_players`)
- [ ] Create intermediate models for reusable joins
- [ ] Create marts (`fact_*`, `dim_*`)
- [ ] Add dbt tests (`not_null`, `unique`, `relationships`)
- [ ] Generate lineage/docs
- [ ] Prefer dbt as the transformation layer, not as a replacement for ingestion logic

---

## Phase 5: Airflow Orchestration

Goal:
Introduce orchestration only after dbt exists and the stage boundaries are clean.

### Planned work

- [ ] Choose orchestration strategy
- [ ] Define jobs for results, match, and map stages
- [ ] Add run scheduling, retries, and monitoring
- [ ] Pass run-level identifiers through stage execution where useful
- [ ] Keep orchestration concerns from leaking back into parser or storage responsibilities

---

## Deferred Work

These items remain important, but they are not ahead of workflow hardening,
deployment baseline work, and dbt.

### API Expansion

- [ ] Keep minimum API deployment readiness in Phase 3.75, including `/health`,
      environment-driven host/port settings, and CORS configuration
- [ ] Add endpoints for matches and teams
- [ ] Add pagination/filtering patterns
- [ ] Evaluate querying transformed dbt models for read paths after dbt marts
      exist

### Demo Pipeline

- [ ] Validate the long-term lifecycle semantics of `demo_ingestion_state`
- [ ] Implement downloader/parser pipeline with cleanup strategy
- [ ] Persist structured demo outputs and error metadata
- [ ] Revisit demo orchestration after the active match/map stages are cleaner

### Scheduling and Orchestration

- [ ] Keep temporary/manual scraper scheduling in Phase 3.75
- [ ] Keep Airflow as Phase 5 after dbt exists
