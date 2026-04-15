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

### Remaining hardening priorities

- [ ] Decide failure policy when retries are exhausted (continue stage vs fail run)
- [x] Standardize scraper/parser/storage error handling so controllers own retry and terminal queue outcomes
- [ ] Improve observability around retry exhaustion and run-level outcomes
- [ ] Add targeted tests for controller retry and recovery behavior
- [ ] Clean up scraper/parser helper methods to clarify responsibilities, naming, and public vs private method boundaries
- [ ] Centralize shared controller retry/session-recovery logic to reduce duplication across stages
- [ ] Evaluate queue schema upgrades (`processing`, locks, `available_at`) when multi-worker support is needed

---

## Next Phase: Data Transformation (dbt)

Goal:
Introduce transformation models after ingestion behavior is stable.

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
