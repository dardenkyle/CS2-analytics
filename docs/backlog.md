# Backlog

This document tracks the recommended implementation order for the next architecture cleanup phases.

---

## Current Position

Phase 3 is complete, and the active codebase now has stable stage-service
boundaries, controller retry hardening, and relational match/map/player storage
contracts. Phase 3.5 remains the active stabilization phase before dbt.

Current priorities:

- keep `matches`, `maps`, and `players` stable, relational, and idempotent
- close the remaining focused integration coverage around discovery through
  map/player persistence
- clean up remaining queue-era terminology where it affects active
  ingestion-state readability
- defer dbt, demo expansion, and Airflow until the Phase 3.5 entry criteria are
  satisfied

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
In progress. Most storage, schema initialization, relationship, and database
access cleanup work is complete. Remaining work should stay focused on
integration coverage and ingestion terminology before dbt begins.

### Schema target reference

`docs/schema_target_pre_dbt.md` captures the intended Phase 3.5 parsed-source
schema target for `matches`, `maps`, and `players` before dbt work begins.
Treat it as planning guidance until implemented; `cs2_analytics/storage/schema.sql`
remains the active schema source of truth.

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
- [ ] Add a focused integration-style test for match discovery -> map discovery
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

8. [ ] `phase3.5-dbt-readiness-final`
   Add the final focused integration coverage for match discovery -> map
   discovery -> map/player persistence, confirm the `matches`, `maps`, and
   `players` grains are stable, and update the dbt entry criteria once Phase
   3.5 is fully satisfied. Do not initialize dbt in this branch.

### dbt entry criteria

- [ ] `matches`, `maps`, and `players` have stable grains
- [x] Map-player-match relationships are queryable without parsing strings
- [x] Storage upserts are duplicate-safe and refresh trusted fields
- [x] Tests pass
- [ ] dbt can start with clean staging models: `stg_matches`, `stg_maps`, and
      `stg_players`

---

## Phase 4: dbt Transformation Layer

Goal:
Add dbt only after ingestion/state semantics and active stage boundaries are stable.

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

These items remain important, but they are not ahead of lifecycle semantics and controller cleanup.

### API Expansion

- [ ] Add endpoints for matches and teams
- [ ] Add pagination/filtering patterns
- [ ] Evaluate querying transformed dbt models for read paths

### Demo Pipeline

- [ ] Validate the long-term lifecycle semantics of `demo_ingestion_state`
- [ ] Implement downloader/parser pipeline with cleanup strategy
- [ ] Persist structured demo outputs and error metadata
- [ ] Revisit demo orchestration after the active match/map stages are cleaner
