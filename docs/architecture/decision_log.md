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

## ADR-0008: Use Render And GitHub Actions For First Cloud Deployment

Status:
Accepted

Date:
2026-05-26

Context:
The project needs a first cloud deployment target before dbt work begins. The
deployment should stay low-cost and operationally simple, preserve the current
API and pipeline entrypoints, and avoid introducing Airflow or broader
ingestion architecture changes.

Decision:
Use GitHub Pages for the frontend, Render for the API web service, Render
PostgreSQL for the application database, and GitHub Actions as the manual
pipeline/scraper runner. Store API runtime secrets in Render environment
variables and pipeline/deployment secrets in GitHub Actions secrets. Run
migrations manually from a controlled local environment for the first deploy,
with a GitHub Actions migration workflow deferred until the release path is
stable.

Consequences:
- No custom frontend domain is planned for the first deploy.
- The Render API CORS allowlist must include the GitHub Pages origin.
- Scheduled scraper runs remain deferred until match and map batch behavior is
  validated.
- Write-based deterministic smoke checks must use a separate minimal smoke or
  staging database, not the production analytics database.
- Production validation must be read-only: Alembic current revision, API
  `/health`, and a DB-backed API read.
- Rollback relies on a recovery point or exported logical backup before manual
  migrations, forward-fix migrations when possible, Render API deploy rollback
  when schema compatibility allows, and database restore for unrecoverable
  migration mistakes.
- Pipeline failures are treated as ingestion recovery through lifecycle state
  inspection and manual retry, not as schema rollback events.

## ADR-0009: Use A React SPA For The Public Frontend

Status:
Accepted

Date:
2026-07-05

Context:
Phase A needed a public, employer-facing demo of the deployed system.
`frontend/` held only a localhost Streamlit debug viewer, and the deployment
target was already GitHub Pages (ADR-0008), which serves static assets only.

Decision:
Retire the Streamlit debug app and build the public frontend as a React,
TypeScript, and Vite SPA in `frontend/`. Keep the app router-free until a
second view needs routing. Configure the API base URL as a code default in
`frontend/src/config.ts` with a `VITE_API_BASE_URL` build-time override; no
`.env` file is committed because the URL is public and ships in the bundle
either way.

Consequences:
- The SPA builds statically and deploys to GitHub Pages from `main`, with
  Vite `base` set to the project-page path for builds and preview only.
- Frontend deploys cannot affect backend runtime, schema, or data.
- Loading, empty, and error states are explicit, including cold-start
  messaging for the free-tier API wake-up delay.
- Local development against the production API requires the localhost
  origins in the Render `API_CORS_ORIGINS` allowlist.

## ADR-0010: Gate Each Stack With Its Own Path-Filtered Workflow

Status:
Accepted

Date:
2026-07-06

Context:
The CI gate covered only Python. Frontend changes merged with no automated
verification, and GitHub Actions path filtering works at the workflow level,
so a frontend job inside `ci.yml` could not skip cleanly for backend-only
changes.

Decision:
Give the frontend its own workflow (`frontend-ci.yml`) that runs `npm ci`,
`npm run build`, and `npm run lint` only when `frontend/**` changes, and a
separate Pages deployment workflow (`deploy-frontend.yml`) for pushes to
`main`. Pin all third-party actions to commit SHAs, following the existing
`ci.yml` convention.

Consequences:
- Backend-only pull requests never pay Node setup time, and frontend pull
  requests are machine-verified before merge.
- Non-matching pull requests do not trigger the workflow at all, so making
  the frontend check required would need path-aware handling.
- New workflows cannot be manually dispatched until their file exists on the
  default branch; first runs happen on merge.

## ADR-0011: Consolidate Lint And Format Tooling On Ruff

Status:
Accepted

Date:
2026-07-06

Context:
black and isort sat in dev dependencies while ruff already owned linting
with the `I` import rules selected, and CI invoked only ruff. Three tools
shared two jobs, and the isort-covered files were provably never enforced.

Decision:
Remove black and isort. `ruff format` is the sole formatter and `ruff check`
with the `I` rules is the sole import sorter. Apply the one-time
`ruff format` and safe-fix migration in a dedicated, mechanical commit.

Consequences:
- One tool defines formatting and import order for humans, CI, and agents.
- Remaining non-auto-fixable lint findings are deliberate future cleanup,
  not enforced by the CI gate.
- The committed lockfile shrinks (black, isort, and transitive pytokens
  removed).

## ADR-0012: Enforce Fetch-Only Scrapers With A Boundary Test

Status:
Accepted

Date:
2026-07-06

Context:
ADR-0002 declared scrapers fetch-only, but the results scraper still
constructed `MatchIngestionState` and wrote discovery rows directly — debt
documented in the conventions and overview docs. The contract lived only in
prose, so nothing failed when code drifted from it.

Decision:
Split results discovery like the other stages: `ResultsScraper` yields
per-page batches of discovered matches, `ResultsStageService` owns the
ingestion-state refreshes, and `ResultsController` coordinates the two. Add
a boundary test that walks every scraper module's imports and fails if any
scraper imports storage or ingestion-state modules.

Consequences:
- No scraper module performs database or lifecycle writes; the discovery
  write path preserves the existing source string, chunking, and per-page
  timing.
- The fetch/persist contract is enforced by the test suite instead of
  assumed from documentation.
- Scrapers are unit-testable without a database, and results discovery
  gained its first real tests.

## ADR-0013: Make Data Writes And State Transitions Atomic Via Explicit Cursor Threading

Status:
Accepted

Date:
2026-07-07

Context:
Storage writes and the ingestion-state mark-complete transition ran as
separate transactions (#74). A failure between them left persisted data rows
with a stale lifecycle status. Two designs were considered: an explicit
transaction cursor passed through storage and state functions, or an ambient
transaction joined implicitly through a context variable inside
`get_cursor()`.

Decision:
Use explicit cursor threading. `Database.transaction()` yields a cursor that
spans multiple statements and commits or rolls back as one unit. Storage
functions and ingestion-state mark/queue methods accept an optional `cur`
parameter: when provided they execute on the caller's cursor without
committing; when omitted they keep their existing per-call transaction.
Stage services own the transaction scope, wrapping the per-item data write,
follow-up discovery refreshes, and the processed mark in one block. The
ambient alternative was rejected because participation would be invisible at
call sites, future writes inside a wrapped block would join the transaction
silently, and wiring could not be unit-tested without a database.

Consequences:
- A failure between the data write and the state mark rolls both back; no
  half-committed rows.
- Network fetch and parsing stay outside the transaction, so slow upstream
  responses never hold a pool connection.
- `mark_as_failed` intentionally stays a separate transaction so failures
  are recorded even when the data transaction rolls back.
- Storage functions and state methods called without a cursor behave exactly
  as before, so callers outside stage services are unaffected.
- Transaction wiring is unit-testable by asserting all writes received the
  same cursor object.

## ADR-0014: Move The Non-Working Demo Subsystem Off Main

Status:
Accepted

Date:
Phase 3.9

Context:
Non-working demo code sat on `main`: a demo scraper marked not working, a
demo parser producing placeholder output, an unreachable demo controller and
stage service (the pipeline demo step was commented out), and demo storage
with no live caller. Demo acquisition is currently blocked, so the code added
noise and maintenance surface without value (#81). ADR-0005 already committed
to deferring demo expansion.

Decision:
Move the demo scraper, parser, controller, stage service, storage module, and
their tests to the `feature/demo-parsing` branch, preserving full history.
Keep the working discovery side on `main`: match processing still discovers
demo links and records them in `demo_ingestion_state`, and the
`demo_ingestion_state` and `demo_files` tables stay in the schema unchanged.

Consequences:
- `main` has no unreachable or placeholder demo code paths.
- Demo discovery keeps accumulating `demo_ingestion_state` rows, so demo
  processing can resume from recorded state when acquisition is unblocked.
- Demo implementation work continues from `feature/demo-parsing`, which plugs
  back into the same controller/stage-service pattern.
- The demo stage boundary is now preserved by the ingestion-state tables and
  discovery flow rather than a placeholder `DemoStageService`, superseding
  that consequence of ADR-0005.
