# Workflow

This project uses small, issue-driven branches so architecture changes stay
reviewable and aligned with the roadmap.

## Current Roadmap Order

1. Phase 3.6: issue-driven workflow and agent readiness.
2. Phase 3.75: deployment baseline.
3. Phase 4: dbt transformation layer.
4. Phase 5: Airflow orchestration.

Demo expansion remains deferred. dbt must stay downstream of ingestion, and
Airflow comes after dbt.

## Issue To Merge Flow

1. Create or choose a GitHub issue with clear scope, acceptance criteria,
   out-of-scope notes, and verification expectations.
2. Create a branch from the current mainline branch using the branch naming
   convention below.
3. Keep the change focused on the issue. Split broad work into follow-up issues.
4. Open a pull request using the repo template.
5. Before opening or finalizing the pull request, update `docs/backlog.md` when
   the branch completes roadmap work, changes phase status, or alters planned
   branch sequencing.
6. Fill in summary, related issue, scope, out of scope, risk level,
   architecture/roadmap check, documentation check, verification, and review
   notes.
7. Request human review for medium-risk, high-risk, schema, deployment,
   dependency, CI, or architecture-boundary changes.
8. Merge only after CI passes, review concerns are resolved, and verification
   gaps are closed.

## Branch Naming

Use lower-case, hyphen-separated branch names:

`phase<phase>-<short-scope>`

Examples:

- `phase3.6-agent-docs`
- `phase3.75-env-config-hardening`
- `phase3.75-container-runtime`
- `phase4-dbt-staging-models`

Bugfix branches may use:

`fix-<short-scope>`

## Labels

Apply labels that describe phase, area, type, priority, and risk.

Use exactly one phase label when possible:

- `phase: 3.6`
- `phase: 3.75`
- `phase: 3.9`
- `phase: 4`
- `phase: 5`
- `phase: A`
- `phase: B`
- `phase: deferred`

Use one or more area labels when they add useful routing context:

- `area: frontend`
- `area: backend`
- `area: api`
- `area: ingestion`
- `area: data`
- `area: tooling`

Use type labels to describe the main kind of work:

- `type: implementation`
- `type: bug`
- `type: documentation`
- `type: maintenance`
- `type: architecture`
- `type: deployment`

Use one priority label and one risk label:

- `priority: critical`, `priority: high`, `priority: medium`, or `priority: low`
- `risk: high`, `risk: medium`, or `risk: low`

## Risk Levels

Low risk:

- docs-only changes
- templates or label metadata
- narrow tests with no runtime behavior change
- small implementation changes with isolated behavior

Medium risk:

- shared behavior changes
- controller, stage-service, storage, parser, or API changes with contained
  impact
- dependency or CI changes
- config changes that affect local development

High risk:

- schema or migration changes
- deployment/runtime behavior changes
- ingestion lifecycle semantics changes
- broad refactors
- changes that could affect production data, retries, or idempotency

## Agent Change Policy

Agents may make small, scoped changes without additional approval when the work
matches an issue, branch, or explicit request and stays within documented
architecture boundaries.

Agents should ask before changing schema, deployment targets, lifecycle
semantics, stage order, architecture boundaries, dependencies, CI, or anything
outside the requested scope.

Agents must not add dbt, Airflow, demo expansion, CT/T splits, eco-adjusted
stats, or unrelated analytics scope unless explicitly requested.

During Phase 3.75 and later, Alembic owns application/source schema changes.
Keep `cs2_analytics/storage/schema.sql` aligned as a readable reference when
schema migrations change application tables.

## Human Review Policy

Human review is required before merge for:

- schema, migration, or database ownership changes
- deployment/runtime changes
- architecture-boundary changes
- dependency or CI changes
- medium-risk or high-risk PRs
- changes that expand roadmap scope

Low-risk docs and template changes may still be reviewed, but they are intended
to be small and fast to evaluate.

## CI Gate

GitHub Actions CI runs on pull requests and pushes to `main`. The minimum gate
installs development dependencies, runs focused `python -m ruff` `E,F` linting
over runtime code, type checks API and runner entrypoints with
`python -m mypy`, applies Alembic migrations against PostgreSQL, and runs
`python -m pytest`.

A separate frontend gate (`.github/workflows/frontend-ci.yml`) runs only when
a pull request or push to `main` touches `frontend/**`. It installs
dependencies with `npm ci`, then runs `npm run build` (which includes
TypeScript checking) and `npm run lint`. Pull requests that do not touch the
frontend do not trigger this workflow at all, so no frontend check appears on
them. If the frontend check is ever made a required status check, this
path-filtered behavior needs to be revisited, because required checks that
never run block merging.

Broader Ruff rules, formatting checks, full-package MyPy, and frontend unit
tests may be added later once the project is ready to enforce stricter gates.

## Documentation Check

Every PR must select either `Updated` or `Update not needed` in the PR template
and include a reason.

At the end of each branch, update `docs/backlog.md` when the branch completes
roadmap work, changes phase status, changes checklist status, or alters planned
branch sequencing. If no backlog update is needed, explain why in the PR
documentation check.

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

## Verification

Docs-only changes do not require tests unless they describe executable behavior.

For code changes, run targeted tests first when appropriate, then
`python -m pytest` for shared behavior.

For schema, storage, controller, or stage-service behavior, include focused
tests that prove idempotency, lifecycle behavior, or join/readiness assumptions
as appropriate.
