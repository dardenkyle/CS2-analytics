# Backlog

This document tracks the recommended implementation order for the next architecture cleanup phases.

---

## Current Position

The active codebase already has useful stage boundaries and controller retry hardening, but the next work should not jump directly to dbt or Airflow.

Current priorities:

- clarify match/map ingestion and discovery state semantics
- decide whether the current `*_scrape_queue` names still fit their actual purpose
- add distinct lifecycle and audit fields where they provide real value
- move per-item stage workflow out of `MatchController` and `MapController`

---

## Phase 1: Schema and Lifecycle Review

Goal:
Define the intended meaning of the current match and map discovery tables before changing code structure around them.

### Planned work

- [ ] Review the actual role of `match_scrape_queue` and `map_scrape_queue`
- [ ] Decide whether those tables are still simple work queues or are now lifecycle/state tables
- [ ] Document the intended status model and field semantics
- [ ] Identify redundant versus meaningful timestamps
- [ ] Define naming guidance for current-state versus future-state terminology
- [ ] Keep `cs2_analytics/storage/schema.sql` as the source of truth during the review

---

## Phase 2: Match and Map State Table Updates

Goal:
Update the current discovery tables so they clearly support ingestion/lifecycle tracking.

### Planned work

- [ ] Add or revise distinct lifecycle fields such as `status`, `first_seen_at`, `last_seen_at`, `last_attempted_at`, `last_processed_at`, `last_failed_at`, `retry_count`, `failure_count`, `last_error_message`, `run_id`, `worker_id`, `inserted_at`, and `last_updated_at`
- [ ] Keep only fields with distinct meanings and avoid redundant timestamps
- [ ] Decide whether `match_scrape_queue` and `map_scrape_queue` should keep their current names or move toward names like `match_ingestion_state` and `map_ingestion_state`
- [ ] Preserve idempotency and duplicate-discovery protection
- [ ] Document success, retryable failure, terminal failure, and rediscovery semantics
- [ ] Reserve multi-worker fields and lock semantics for cases where they are actually needed

---

## Phase 3: Match and Map Stage Service Refactor

Goal:
Thin the active controllers by separating batch concerns from per-item stage workflow.

### Planned work

- [ ] Introduce `MatchStageService`
- [ ] Introduce `MapStageService`
- [ ] Move per-item fetch -> parse -> persist -> state-transition logic into stage services
- [ ] Keep controller ownership of batch coordination, retry policy, scraper reset/rotation, and summary logging
- [ ] Keep scrapers fetch-only, parsers parse-only, and persistence centralized
- [ ] Add or update tests around per-item stage outcomes and controller summaries

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

- [ ] Validate the long-term role of `demo_scrape_queue`
- [ ] Implement downloader/parser pipeline with cleanup strategy
- [ ] Persist structured demo outputs and error metadata
- [ ] Revisit demo orchestration after the active match/map stages are cleaner
