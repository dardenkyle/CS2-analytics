# Backlog

This document tracks the recommended implementation order for the next architecture cleanup phases.

---

## Current Position

Phases 3, 3.5, 3.6, and 3.75 are complete: the active ingestion surface has
stable stage-service boundaries, controller retry hardening, relational
match/map/player storage contracts, Alembic-managed schema, a containerized
runtime, CI gates for both stacks, and a first cloud deployment (Render API
and PostgreSQL, GitHub Pages frontend). Frontend Phase A is complete and the
public demo is live.

Current priorities:

- establish a solid ingestion baseline: run the scraper locally, persist to
  the Render database, with controllable quantity (`cs2a` caps and batch
  sizes) and a schedulable entry point
- continue Phase 4 (dbt) without moving ingestion responsibilities into
  dbt: the project is initialized (#109), staging models exist (#110), and
  intermediate models are next;
  Phase 3.9 tooling hardening (#67-#70, #86) and the Phase 4 entry bugs
  (#71, #74) are closed
- keep `docs/schema_target_pre_dbt.md` as planning guidance for later parsed
  source schema normalization
- defer demo expansion and Airflow until after the initial dbt layer exists

---

## Parallel Product Tracks

Frontend product work uses a lettered phase strategy in
`docs/frontend_backlog.md`. Phase A shipped the public React SPA demo backed
by the live top players API. Phase B is a candidate backlog gated on the
decision questions at the end of that document.

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
Complete. The `phase3.6-issue-templates` branch added GitHub issue forms and a
pull request template, the `phase3.6-label-taxonomy` branch added the
repo-tracked label taxonomy, the `phase3.6-agent-docs` branch added
agent/workflow/architecture decision documentation, and the
`phase3.6-create-deployment-issues` branch converted Phase 3.75 deployment work
into small GitHub issues.

### Planned work

- [x] Add GitHub issue templates
- [x] Add pull request template
- [x] Add labels for phase, type, priority, and risk
- [x] Ensure `CLAUDE.md` complies with repo rules and coding standards
- [x] Add `docs/workflow.md` describing issue -> branch -> PR -> merge flow
- [x] Add `docs/architecture/current_state.md` summarizing the active architecture
- [x] Add `docs/architecture/decision_log.md` for project decisions
- [x] Add documentation maintenance rules to `CLAUDE.md`, `docs/workflow.md`,
      and the pull request template
- [x] Convert Phase 3.75 deployment tasks into GitHub issues
- [x] Create small acceptance criteria for each issue
- [x] Create branch naming conventions
- [x] Define what agents are allowed to change without approval
- [x] Define what requires human review before merge

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

3. [x] `phase3.6-agent-docs`
       Add `CLAUDE.md`, workflow docs, current architecture summary, decision
       log, and agent/human review policy.

   Covers:
   - `CLAUDE.md` repo rules and coding standards
   - `docs/workflow.md` issue -> branch -> PR -> merge flow
   - `docs/architecture/current_state.md`
   - `docs/architecture/decision_log.md`
   - documentation maintenance rules in `CLAUDE.md` and `docs/workflow.md`
   - branch naming conventions
   - what agents may change without approval
   - what requires human review before merge

4. [x] `phase3.6-create-deployment-issues`
       Convert Phase 3.75 work into small GitHub issues with clear scope,
       acceptance criteria, out-of-scope notes, and verification commands.

   Covers:
   - Phase 3.75 deployment tasks converted into GitHub issues
   - small acceptance criteria for each deployment issue

### Phase 3.6 exit criteria

- [x] GitHub issues can be created from templates
- [x] Pull requests have a consistent review checklist
- [x] Pull requests include a documentation check
- [x] `CLAUDE.md` explains repo architecture, coding standards, and no-touch areas
- [x] `CLAUDE.md` explains documentation responsibilities
- [x] `docs/workflow.md` explains documentation expectations
- [x] Deployment baseline work is represented as small, reviewable issues
- [x] Branch naming and issue-to-PR workflow are documented

---

## Phase 3.75: Deployment Baseline

Goal:
Make the current ingestion pipeline and API deployable in a reproducible,
containerized environment before adding dbt.

Status:
Complete. The API is deployed on Render, Alembic migrations have run against
Render PostgreSQL, the `/health` and top players endpoints return live data,
and containerized Selenium/Chromium was validated locally. Live cloud ingestion
validation was superseded: Cloudflare blocks made cloud-based scraping
impractical, so the ingestion strategy was changed to local scraping writing
directly to the Render PostgreSQL database. That strategy does not require a
staged cloud scraper run to validate. The `phase3.75-env-config-hardening` branch completed the first
deployment-baseline slice by making runtime configuration environment-driven
and production-safe. The `phase3.75-alembic-migrations` branch added Alembic
configuration and an initial migration for the current application/source
schema. The `phase3.75-container-runtime` branch added the local Docker runtime
baseline for PostgreSQL, migrations, the API, and pipeline runs. The
`phase3.75-ci-gate` branch added the minimum GitHub Actions merge gate for
installation, focused linting, initial runtime type checking, migrations, and
tests. The `phase3.75-deployment-smoke-test` branch added a deterministic
container smoke path for migrations, fixed-ID source-row seed/read/cleanup,
API health, and a DB-backed top players read check. The
`phase3.75-first-cloud-deploy-plan` branch chose GitHub Pages, Render, Render
PostgreSQL, and GitHub Actions as the first cloud deployment shape and
documented the validation, migration, smoke database, runner, and recovery
policies needed before implementation issue #55.

Rationale:
Phase 3.5 confirms that the parsed-source tables are stable enough for dbt, but
the project still needs a reproducible runtime before adding another
architecture layer. Deployment baseline work should prove that the scraper,
database setup, API, environment variables, migrations, tests, and runtime
assumptions work outside the local development machine.

### Planned work

- [x] Add `.env.example` with all required runtime variables
- [x] Move dev-only config defaults out of production paths
- [x] Make API host, port, CORS origins, debug mode, and database settings environment-driven
- [x] Add Alembic for versioned application database migrations
- [x] Convert the current `schema.sql` source tables into an initial Alembic migration
- [x] Keep schema initialization non-destructive by default
- [x] Add migration command documentation for local Docker and deployment usage
- [x] Ensure deployed database updates through `alembic -c cs2_analytics/alembic.ini upgrade head`
- [x] Add a `Dockerfile` for the application runtime
- [x] Add `docker-compose.yml` for local deployment with app/API + PostgreSQL
- [x] Add a dedicated pipeline runner command or module entrypoint
- [x] Add a dedicated API runner command or deployment-safe Uvicorn command
- [x] Add `/health` endpoint for API health checks
- [x] Add GitHub Actions CI for lint, type check, and tests
- [x] Add a deployment smoke test path:
      migrations -> deterministic source-row seed/read/cleanup -> API health/top players check
- [x] Document local Docker startup and production deployment variables
- [x] Choose first deployment target for the API runtime
- [x] Choose first deployment target for pipeline/worker runs
- [x] Document the API + worker deployment topology
- [x] Document staging/production environment variables and secret source
- [x] Define migration order for deployment startup or release
- [x] Define read-only production validation checks:
      Alembic version -> `/health` -> DB-backed API read
- [x] Define smoke/staging database policy for write-based smoke tests
- [x] Choose temporary pre-Airflow runner strategy:
      manual job, scheduled platform job, or GitHub Actions manual dispatch
- [ ] Confirm containerized Selenium/Chromium can run in the chosen worker environment
- [ ] Confirm runtime artifacts do not rely on local machine state:
      logs, demos, parsed data, browser cache, and temporary files
- [x] Document rollback/recovery expectations for failed deploys or migrations
- [ ] Run one limited live ingestion validation in a staging/smoke environment

### Suggested branch sequence

1. [x] `phase3.75-env-config-hardening`
       Add `.env.example`, environment-driven runtime config, production-safe CORS
       config, debug toggles, and deployment-safe API host/port settings.

   Runtime configuration now uses explicit environment variables for API host,
   API port, CORS origins, debug mode, and database settings. Production mode
   fails fast when required runtime variables are missing, debug mode is enabled,
   wildcard CORS is configured, or numeric ports are invalid.

2. [x] `phase3.75-alembic-migrations`
       Add Alembic, create the initial migration from the active schema, document
       migration commands, and make migrations the source of truth for deployed
       application/source tables.

   Alembic now manages the application/source schema through an initial
   migration that mirrors the active tables, constraints, ingestion-state
   lifecycle fields, and setup indexes. `python manage_db.py --init` and
   `python manage_db.py --create-database` apply
   `alembic -c cs2_analytics/alembic.ini upgrade head`
   non-destructively, while explicit wipe behavior remains separate. Existing
   databases that already match the initial migration can be brought under
   migration tracking with `alembic -c cs2_analytics/alembic.ini stamp head`.

3. [x] `phase3.75-container-runtime`
       Add `Dockerfile`, `docker-compose.yml`, and documented local container
       startup flow for PostgreSQL, migrations, API, and pipeline runs.

   The local container runtime now builds a Python application image, runs
   PostgreSQL through compose, exposes an API service with container-safe host
   binding, and provides compose commands for migrations and one-off pipeline
   runs. Runtime artifacts such as logs, demos, and parsed data are mounted from
   the working tree and excluded from the image.

4. [x] `phase3.75-ci-gate`
       Add GitHub Actions for install, lint, type check, and tests. CI should become
       the minimum merge gate before dbt begins.

   CI now runs on pull requests and pushes to `main`. The gate installs dev
   dependencies, runs a focused `python -m ruff` `E,F` lint over runtime code,
   type checks API and runner entrypoints with `python -m mypy`, applies
   Alembic migrations against a PostgreSQL service container, and runs
   `python -m pytest`. Broader Ruff rules, formatting checks, and full-package
   MyPy remain follow-up tightening work.

5. [x] `phase3.75-deployment-smoke-test`
       Add a small deployment verification path that proves the container can run
       migrations, execute a deterministic source-row smoke pass, and start the
       API.

   The deployment smoke path now runs through compose with PostgreSQL,
   migrations, and the API, then executes `scripts/deployment_smoke.py`. The
   script verifies migrated source tables, removes stale fixed-ID smoke rows,
   seeds deterministic match/map/player rows through existing storage upserts,
   checks `/health`, confirms the API can query PostgreSQL through
   `/api/top_players`, and removes the fixed-ID smoke rows before exiting. It
   intentionally avoids live HLTV scraping so deployment checks do not fail when
   the upstream website is unavailable or changes markup.

6. [x] `phase3.75-first-cloud-deploy-plan`
       Choose the first API and worker deployment targets, document the intended
       topology, define staging/production environment variables and secret
       sources, define migration order, define smoke/staging database policy,
       define read-only production validation checks, choose the temporary
       pre-Airflow runner strategy, and document rollback/recovery expectations.

   The first cloud plan uses GitHub Pages for the frontend, a Render web
   service for the API runtime, Render PostgreSQL for the application database,
   and a manual GitHub Actions workflow for pipeline/scraper runs. Scheduled
   scraper runs are deferred until match and map batch behavior is validated.
   Migrations start as a manual local release step, write-based smoke checks use
   a separate minimal smoke/staging database, production validation is
   read-only, and recovery prefers pre-migration backups plus forward fixes.
   Follow-up implementation is tracked in issue #55.

7. [ ] `phase3.75-first-cloud-deploy`
       Deploy the API and pipeline runner to the chosen initial platform. Keep the
       deployment simple and low-cost. Run migrations in the chosen release flow,
       run the deterministic smoke path against staging or smoke infrastructure,
       run read-only production validation after deploy, confirm
       Selenium/Chromium works in the worker environment, and run one limited
       live ingestion validation in staging/smoke. Do not add Airflow yet.

   In progress: the Render API and Render PostgreSQL deployment are reachable,
   Alembic migrations have run, the production `/health` endpoint returns the
   expected payload, and the DB-backed top players API returns real ingested
   player data from Render PostgreSQL. A manual GitHub Actions worker workflow
   now builds the application Docker image, validates containerized
   Selenium/Chromium, and can run `python main.py` against the configured
   PostgreSQL database. Local Docker worker validation passed after granting
   the non-root app user access to SeleniumBase's driver scratch directory in
   the image. Deterministic write-based cloud smoke is deferred until a
   separate disposable smoke/staging database exists; production validation
   remains read-only by policy. Local Docker live pipeline execution completed
   in the worker image and reached map processing against Render PostgreSQL.
   The run exposed a map scraper validation gap: selected map pages can return
   HTML without the expected `match-info-box`. The
   `fix-map-fetch-validation-retry` branch hardened map fetch validation so
   missing, incomplete, blocked, or challenged map stats HTML is classified as
   retryable scraper/session failure before parser handling. Remaining closeout
   work is to run the workflow in GitHub Actions after it is available on
   GitHub, rotate exposed database credentials, and finalize the deployment
   documentation.

8. [x] `fix-map-fetch-validation-retry`
       Fix issue #57 by hardening map fetch validation when HLTV returns
       incomplete, challenged, redirected, or otherwise non-stats map HTML.
       Missing required map page selectors should be classified as retryable
       scraper/session failures with useful diagnostics, while real parser
       failures should remain parser failures. Previously failed map rows can be
       handled by later recovery/reset work; this branch should use the manual
       worker path to validate map processing before recurring worker runs.

   Map fetch validation now waits for the required map stats selector and logs
   requested URL, browser URL, title, page-source length, challenge marker
   flags, and a short page snippet when validation fails. Cloudflare/challenge
   pages are surfaced as retryable blocked/challenged session failures rather
   than map parser failures. A limited validation run against Render PostgreSQL
   confirmed the affected rows no longer use the old map-name parser failure
   path.

### Phase 3.75 exit criteria

- [x] Fresh clone can run through Docker without manual local setup
- [x] Required environment variables are documented
- [x] API binds correctly in a deployed/container environment
- [x] PostgreSQL connection works through environment config
- [x] Fresh database can be initialized through migrations
- [x] Existing database can be brought under migration tracking without destructive reset
- [x] App tables and ingestion-state tables are migration-managed
- [x] Schema initialization is explicit and non-destructive by default
- [x] CI passes on every PR
- [x] A deterministic source-row seed/read/cleanup smoke path works outside the local dev environment
- [x] API health endpoint works in deployed environment
- [x] First API and worker deployment targets are chosen and documented
- [x] Staging/production environment variables and secret source are documented
- [x] Deployment migration order is documented
- [x] Smoke/staging database policy is documented for write-based smoke tests
- [x] Read-only production validation checks are defined
- [x] Containerized Selenium/Chromium works in the chosen worker environment
- [x] Runtime artifacts do not rely on local machine state
- [x] Rollback/recovery expectations are documented
- [x] There is a temporary scheduled/manual runner path before Airflow
- [x] One limited live ingestion validation passes in staging/smoke — superseded:
      Cloudflare blocks made cloud-based scraping impractical. Ingestion strategy
      changed to local scraping writing directly to Render PostgreSQL. Local
      Docker pipeline execution reached the map stage against Render PostgreSQL,
      satisfying the intent of this criterion under the revised approach.

---

## Phase 3.9: Environment and Tooling Hardening

Goal:
Align the Python version targets across all tooling, adopt uv for reproducible
installs, and consolidate lint/format tooling on ruff before the public frontend
deploy (A3, #62) and Phase 4 orchestration work begin.

Status:
Complete. Tooling targets Python 3.12 (#67), uv + `uv.lock` landed (#68),
ruff is the sole lint/format tool (#70), dev/test tooling lives in
`[dependency-groups]` so plain `uv sync` installs it (#69), and the `cs2a`
CLI entry point wraps discovery, processing, and status reporting (#86).
The A3 gate this phase carried has been satisfied — the frontend is
deployed.

Convention: numeric phases track backend/pipeline/infra; letter phases track the
frontend. Phase 3.9 is the only cross-axis dependency — A3 is blocked by #67
and #68.

### Planned work

- [x] Align tooling config to Python 3.12 — fix stale 3.14 targets in mypy,
      ruff, black, and classifiers (#67)
- [x] Adopt uv + commit `uv.lock` for reproducible installs (#68)
- [x] Move dev/test tooling to `[dependency-groups]` so `uv sync` installs them
      by default (#69)
- [x] Consolidate lint/format on ruff — remove black and isort from dev deps
      (#70)
- [x] Add `cs2a` CLI entry point (#86)

### Suggested branch sequence

1. [x] `phase3.9-tooling-version-align` — resolves #67
2. [x] `phase3.9-uv-adoption` — resolves #68
3. [x] `phase3.9-dependency-groups` — resolves #69
4. [x] `phase3.9-ruff-consolidation` — resolves #70

Do #67 and #68 first — they are the actual gate for A3. #69 and #70 are
same-pass cleanup that can follow immediately after.

### Phase 3.9 exit criteria

- [x] All tooling targets Python 3.12
- [x] `uv.lock` is committed and CI uses `uv sync`
- [x] Dev/test deps install via `uv sync` without extra flags
- [x] ruff is the sole formatter and import sorter
- [x] CI passes

---

## Phase 4: dbt Transformation Layer

Goal:
Add dbt after ingestion/state semantics are stable and the current runtime has a
reproducible deployment baseline.

### Phase 4 entry criteria

- [ ] Phase 3.6 issue-driven workflow is complete
- [ ] Phase 3.75 deployment baseline is complete
- [ ] Current ingestion pipeline can run outside the local dev machine
- [x] Application/source tables are managed by Alembic migrations
- [ ] dbt will be additive and downstream of ingestion, not a replacement for ingestion logic
- [x] Scraper boundary leak resolved — no scraper module writes DB or ingestion-state rows (#71)
- [x] Manual scripts removed from `tests/` so pytest collects only real automated tests (#72)
- [x] `.coverage` artifact removed from git and ignored (#73)
- [x] Data write and ingestion-state transition are atomic — approach agreed and implemented (#74)

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

- [x] Initialize dbt project (#109): skeleton under `dbt/`, env-driven
  Postgres profile, sources declared for `matches`, `maps`, `players`
- [x] Create staging models (`stg_matches`, `stg_maps`, `stg_players`) (#110):
  thin views over the declared sources with documented grains
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

### v1.0 Polish

These are correctness and readability improvements that do not gate Phase 4 but
should be addressed before the repo is considered v1.0.

- [x] Add a coverage `fail-under` threshold and wire it into CI so the floor
      is enforced — `fail_under = 75` in `pyproject.toml`, CI runs
      `pytest --cov` (#76)
- [x] Stop silently coercing parse failures to `0` — required stats now raise
      `MapParseError` into the failed ingestion state, secondary stats log a
      warning before defaulting (#75)
- [x] Test untested failure branches: date-parse warning, scraper
      close-failure, parser fallback paths — scraper branches gained tests in
      #106; the parser fallback branches were already covered by the tests
      added in #103, which made them raise `MapParseError` (#77)
- [x] Batch N+1 storage writes using `executemany` (`match_storage.py`,
      `map_storage.py`, `player_storage.py`) — each store call now issues one
      `executemany` batch instead of per-row `execute`, matching the
      `record_many` pattern (#78)
- [x] Widen mypy CI target to cover `cs2_analytics` ingestion core, not just
      the API layer — CI now type-checks `cs2_analytics`; the errors that
      surfaced were fixed with real annotations (generic
      `BaseIngestionState[IdT]`, a `_MatchMetadata` TypedDict, typed locals)
      rather than suppressions (#79)
- [x] Break up overlong controller and utility functions
      (`match_controller.py`, `map_controller.py`, `results_controller.py`,
      `retry_utils.py`) — controller run loops now delegate to cohesive
      rotate/retry/outcome helpers over a shared `BatchRunState`, and
      `reset_scraper` gained close/build/discard helpers; behavior unchanged
      (#80)
- [x] Move non-working demo subsystem to a `feature/demo-parsing` branch; add
      deferral note to README — demo link discovery and `demo_ingestion_state`
      remain on `main` (#81, ADR-0014)
- [ ] Add a "Design decisions & tradeoffs" section to the README explaining key architectural choices
