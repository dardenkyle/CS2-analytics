# CLAUDE.md

Guidance for coding agents working in this repository.

## Read First

- Start with `README.md`, `docs/architecture/overview.md`,
  `docs/architecture/current_state.md`, `docs/conventions.md`,
  `docs/workflow.md`, and `docs/backlog.md`.
- Treat Alembic migrations in `cs2_analytics/alembic/versions/` as the
  executable application/source schema source of truth. Keep
  `cs2_analytics/storage/schema.sql` aligned as the readable schema reference
  during the migration ownership transition.
- Prefer the existing architecture over new abstractions.
- Keep changes aligned with the current roadmap: Phases 3, 3.5, 3.6, and 3.75
  are complete. Phase 3.9 is environment and tooling hardening. Phase 4 entry
  criteria include the v1.0 hardening items (#71–#74). dbt comes after Phase
  3.9, demo expansion is deferred, and Airflow comes after dbt.

## Python Coding Standards

- Use Python 3.14+ syntax.
- Use built-in generic type hints such as `list[str]`, `dict[str, int]`, and `str | None`.
- Avoid importing from `typing` unless necessary.
- Add module-level docstrings to new Python modules when they clarify purpose.
- Add docstrings to public classes/functions when behavior, inputs, side effects, or domain meaning are not obvious.
- Use type hints consistently.
- Use structured logging instead of `print`; prefer JSON for log files and human-readable output for console logs.
- Avoid broad exception handling except at explicit retry, boundary, or terminal logging points.
- Prefer specific exceptions and domain-specific custom exceptions.
- Use OOP when it improves structure, clarity, or extensibility.
- Keep modules small, focused, and testable.
- Preserve separation of concerns.
- Avoid unnecessary imports, hardcoded values, and unrelated rewrites.
- Prefer production-grade, maintainable solutions over shortcuts.

## Project Shape

- This is a Python 3.14+ Counter-Strike 2 analytics project.
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

## Agent Change Policy

Agents may make small, scoped changes without additional approval when the work
matches an issue, branch, or explicit request and stays within the documented
architecture.

Agents may normally update:

- docs, templates, labels, and issue metadata
- focused tests for the behavior being changed
- parser, scraper, controller, stage-service, storage, API, or config code that
  is directly in scope for the requested task
- backlog status when a branch completes or roadmap status changes

Agents must ask before:

- changing database schema, migrations, or lifecycle field semantics
- changing ingestion stage order or controller/stage-service boundaries
- adding dbt, Airflow, demo expansion, CT/T splits, eco-adjusted stats, or
  unrelated analytics scope
- changing deployment targets, production runtime assumptions, or credentials
- running destructive commands, destructive schema resets, or broad formatters
- refactoring outside the requested scope

Human review is required before merge for schema changes, deployment/runtime
changes, architecture-boundary changes, dependency changes, CI changes, and any
PR marked medium or high risk.

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
- Do not run auto-formatters across the whole repo unless the task is specifically formatting-related.

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

- Install development dependencies with `uv sync --extra dev`. This
  creates `.venv`. Activate it if not automatically activated
  (`source .venv/bin/activate`), or prefix commands with `uv run`.
- Use `python -m cs2_analytics.storage.initialize_db` or
  `alembic -c cs2_analytics/alembic.ini upgrade head` to initialize or upgrade
  the local database schema when needed.
- Keep local credentials and environment-specific settings out of commits.
- Avoid committing generated caches, coverage output, logs, parsed data, or
  downloaded demos.

## Documentation Expectations

- Update `docs/backlog.md` when roadmap status changes.
- At the end of each branch, update `docs/backlog.md` when the branch completes
  roadmap work, changes phase status, changes checklist status, or alters
  planned branch sequencing. If no backlog update is needed, explain why in the
  PR documentation check.
- Update `docs/architecture/overview.md`,
  `docs/architecture/current_state.md`, `docs/architecture/decision_log.md`, or
  `docs/conventions.md` when architectural boundaries or project decisions
  change.
- Update `docs/workflow.md` when agent, branch, PR, review, or documentation
  workflow rules change.
- Keep README changes user-facing and concise.
- Prefer linking to existing docs over repeating long explanations.
- Every PR must include a documentation check explaining whether docs were
  updated or why they were not needed.

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
