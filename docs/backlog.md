# Backlog

This backlog tracks planned work after current pipeline hardening.

---

## Current Phase: Pipeline Hardening

Goal:
Maintain reliability while preserving clean stage boundaries and queue-driven processing.

### Completed or largely complete

- [x] Controllers orchestrate results/match/map stages
- [x] Scrapers fetch content; parsers extract structured data
- [x] Queue-based handoff between stages
- [x] Retry/backoff and scraper session recovery in controllers
- [x] Map parser hidden-vs-visible metric regression fix + tests
- [x] Storage ownership centralized for match/player writes
- [x] Controller/parser/scraper responsibilities aligned for active match/map flow
- [x] Decide failure policy when retries are exhausted (results fails run; match/map fail item and continue)
- [x] Standardize scraper/parser/storage error handling so controllers own retry and terminal queue outcomes
- [x] Improve observability around retry exhaustion and run-level outcomes
- [x] Add targeted tests for controller retry and recovery behavior
- [x] Clean up scraper/parser helper methods to clarify responsibilities, naming, and public vs private method boundaries
- [x] Centralize shared controller retry/session-recovery logic to reduce duplication across stages
- [x] Add field-specific parser extraction errors for required match/map fields

### Future hardening backlog

- [ ] Evaluate queue schema upgrades (`processing`, locks, `available_at`) when multi-worker support is needed
- [ ] Add parser tests for malformed-but-partial HLTV markup
- [ ] Define required vs optional fields for match/map parsing
- [ ] Add idempotency tests for queue and storage writes
- [ ] Standardize timezone-aware timestamps across parser/storage models
- [ ] Add controller tests for queue/storage failure paths after parse success
- [ ] Add structured run identifiers to controller logs for cross-stage tracing
- [ ] Truncate and normalize stored error messages consistently across controllers
- [ ] Add dead-letter/retry requeue policy for failed items
- [ ] Validate follow-up queue payloads before enqueueing map/demo links
- [ ] Add health-check coverage for scraper reset failure/fallback behavior
- [ ] Add startup checks for required config/env vars before pipeline execution
- [ ] Separate integration tests from unit tests for DB and scraper-dependent paths
- [ ] Add protection against duplicate processing when the same item is queued twice
- [ ] Audit and normalize naive `datetime.now()` usage outside the recent UTC fix
- [ ] Add explicit controller summaries for zero-item runs
- [ ] Document expected failure modes by stage in `docs/current_focus.md` or a dedicated hardening note

---

## Next Phase: Data Transformation (dbt)

Goal:
Introduce transformation models after ingestion behavior is stable.

### Before starting

- [ ] Clean up parser/scraper class structure for readability without changing behavior

### Planned work

- [ ] Initialize dbt project
- [ ] Create staging models (`stg_matches`, `stg_maps`, `stg_players`)
- [ ] Create intermediate models for reusable joins
- [ ] Create marts (`fact_*`, `dim_*`)
- [ ] Add dbt tests (`not_null`, `unique`, `relationships`)
- [ ] Generate lineage/docs

---

## Next Phase: Orchestration

Goal:
Move from manual runs to scheduled, observable workflows.

### Planned work

- [ ] Choose orchestration strategy
- [ ] Define jobs for results, match, and map stages
- [ ] Add run scheduling, retries, and monitoring

---

## Next Phase: API Expansion

Goal:
Expose additional structured data via FastAPI.

### Planned work

- [ ] Add endpoints for matches and teams
- [ ] Add pagination/filtering patterns
- [ ] Evaluate querying transformed dbt models for read paths

---

## Next Phase: Demo Pipeline

Status: blocked until hardening goals are met.

### Planned work

- [ ] Validate `demo_scrape_queue` operating model
- [ ] Implement downloader/parser pipeline with cleanup strategy
- [ ] Persist structured demo outputs and error metadata
