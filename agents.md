# AGENTS.md

Guidance for coding agents working in this repository.

## Read First

- Start with `README.md`, `docs/architecture.md`, `docs/conventions.md`, and
  `docs/backlog.md`.
- Treat `cs2_analytics/storage/schema.sql` as the schema source of truth.
- Prefer the existing architecture over new abstractions.
- Keep changes aligned with the current roadmap: Phase 3 is complete, dbt is
  next, demo expansion is deferred, and Airflow comes after dbt.

## Project Shape

- This is a Python 3.11+ Counter-Strike 2 analytics project.
- Ingestion currently uses PostgreSQL-backed lifecycle/state tables:
  `match_ingestion_state`, `map_ingestion_state`, and `demo_ingestion_state`.
- The active production flow is results discovery, match processing, map
  processing, then relational storage and API/data consumers.
- Demo support exists as a boundary, but full demo download/parsing remains
  deferred.

## Architectural Boundaries

- Controllers own batch coordination, retry policy, scraper reset/rotation,
  summaries, and retry exhaustion behavior.
- Stage services own per-item fetch, parse, persist, and lifecycle outcomes.
- Scrapers fetch remote content only.
- Parsers convert fetched content into structured outputs only.
- Storage modules centralize relational database writes.
- Pipelines coordinate stage order and should stay thin.
- Do not tightly couple match, map, and demo into one synchronous flow.
- Do not move ingestion responsibilities into dbt.
- Do not let orchestration concerns drive schema semantics prematurely.

## Change Discipline

- Prefer small, reviewable diffs.
- Do not delete large blocks of code and add back nearly identical code plus one
  small change.
- Do not reformat, reorder, or rewrite unrelated code just to add a small
  behavior change.
- Do not mix refactors with feature work unless explicitly requested.
- Do not change unrelated files to satisfy personal style preferences.
- Preserve existing structure unless the task explicitly calls for a refactor.
- Keep docs-only branches docs-only.
- If a change appears to require a large rewrite, explain why before making it.

## Testing And Verification

- For code changes, run `python -m pytest`.
- For focused changes, prefer targeted tests first, then the full suite when the
  change affects shared behavior.
- For docs-only changes, tests are not required unless the docs describe or
  change executable behavior.
- Smoke test `python main.py` only when the local scraper and database
  environment is available.
- Run API work with `python run_api.py` when API behavior needs manual checking.

## Local Development Notes

- Install development dependencies with `pip install -e ".[dev]"`.
- Use `python -m cs2_analytics.storage.initialize_db` to initialize the local
  database schema when needed.
- Keep local credentials and environment-specific settings out of commits.
- Avoid committing generated caches, coverage output, logs, parsed data, or
  downloaded demos.

## Documentation Expectations

- Update `docs/backlog.md` when roadmap status changes.
- Update `docs/architecture.md` or `docs/conventions.md` when architectural
  boundaries change.
- Keep README changes user-facing and concise.
- Prefer linking to existing docs over repeating long explanations.
