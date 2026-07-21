# Counter-Strike 2 Pro Match Analytics Tool

[![CI](https://github.com/dardenkyle/CS2-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/dardenkyle/CS2-analytics/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/dardenkyle/CS2-analytics/badges/coverage.json)](https://github.com/dardenkyle/CS2-analytics/actions/workflows/ci.yml)
[![Frontend CI](https://github.com/dardenkyle/CS2-analytics/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/dardenkyle/CS2-analytics/actions/workflows/frontend-ci.yml)
[![Deploy Frontend](https://github.com/dardenkyle/CS2-analytics/actions/workflows/deploy-frontend.yml/badge.svg)](https://github.com/dardenkyle/CS2-analytics/actions/workflows/deploy-frontend.yml)

**Live demo:** [dardenkyle.github.io/CS2-analytics](https://dardenkyle.github.io/CS2-analytics/) —
a public dashboard showing top players served live from the production
database. The API behind it is also public:
[cs2-analytics.onrender.com/docs](https://cs2-analytics.onrender.com/docs).
(The API runs on a free tier and can take up to ~30 seconds to wake after
idle periods.)

## Project Overview

This project is a Counter-Strike 2 analytics tool focused on collecting professional match, map, and player data and turning it into reliable, queryable analytics data.

The system is deployed end to end: a Python ingestion pipeline writes to
PostgreSQL, a FastAPI service on Render serves player statistics, and a React
SPA on GitHub Pages presents them publicly.

The current ingestion architecture uses PostgreSQL-backed ingestion-state tables, thin controllers for batch orchestration, and stage services for per-item match/map workflow boundaries.

## Features

### Data Ingestion

- Results discovery refreshes match ingestion-state rows.
- Match processing collects match metadata and discovers downstream map/demo links.
- Map processing collects player performance metrics such as kills, deaths, assists, ADR, KAST, opening duels, multi-kills, clutches, and round swing.
- Ingestion hardening uses retry/backoff, browser session recovery, and lifecycle tracking for resilient scraping runs.

### Deferred / Later-Phase Work

- Demo processing: deferred; the demo subsystem lives on the
  `feature/demo-parsing` branch, while demo link discovery and
  `demo_ingestion_state` tracking remain on `main`.
- Deployment baseline: containerized runtime, environment-driven configuration,
  migrations, CI, and smoke tests come before dbt.
- dbt transformation layer: dbt follows the deployment baseline and stays
  downstream of ingestion.
- Airflow orchestration: Airflow comes after dbt and clean stage boundaries.

## Tech Stack

- Python 3.12
- SeleniumBase and BeautifulSoup for web scraping
- PostgreSQL for structured data storage, with Alembic-managed migrations
- dbt for the downstream analytics transformation layer (Phase 4, in
  progress)
- FastAPI for the public read API (deployed on Render)
- React, TypeScript, and Vite for the public frontend (deployed on GitHub
  Pages)
- Docker and Docker Compose for the container runtime
- GitHub Actions for CI (backend and frontend gates) and deployment
- uv with a committed lockfile for reproducible Python installs

## Project Structure

```text
CS2-Analytics/
|-- main.py
|-- run_api.py
|-- README.md
|-- pyproject.toml
|-- api/
|   |-- main.py
|   |-- routes/
|   |-- schemas/
|   `-- services/
|-- cs2_analytics/
|   |-- config/
|   |-- controllers/
|   |-- ingestion_state/
|   |-- models/
|   |-- parsers/
|   |-- pipeline/
|   |-- scrapers/
|   |-- stage_services/
|   |-- storage/
|   `-- utils/
|-- dbt/
|   |-- dbt_project.yml
|   |-- profiles.yml
|   `-- models/
|-- docs/
|-- logs/
|-- scripts/
|-- tests/
`-- frontend/
```

## Installation & Setup

### 1. Clone the Repository

```sh
git clone https://github.com/dardenkyle/CS2-analytics.git
cd CS2-Analytics
```

### 2. Install uv

If you do not have uv installed, pick one of:

```sh
# via pip
pip install uv

# via the official installer (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# via the official installer (Windows)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 3. Install Dependencies

```sh
uv sync
```

This creates a `.venv` virtual environment and installs all runtime and
development dependencies from the committed `uv.lock` lockfile. Dev and
test tooling lives in `[dependency-groups]`, which `uv sync` installs by
default.

Activate the virtual environment before running subsequent `python`
commands:

```sh
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 4. Configure Environment Variables

Copy `.env.example` to `.env` for local development and adjust the values for
your PostgreSQL instance.

Required runtime variables:

| Variable | Purpose | Local example |
| --- | --- | --- |
| `ENVIRONMENT` | Runtime environment name. Use `production` for deployed runtime validation. | `development` |
| `DEBUG_MODE` | Enables debug logging and API reload behavior. Must be `false` in production. | `true` |
| `API_HOST` | Host address used by `python run_api.py`. | `127.0.0.1` |
| `API_PORT` | Port used by `python run_api.py`. | `8000` |
| `API_CORS_ORIGINS` | Comma-separated browser origins allowed by the API. Wildcard CORS is rejected in production. | `http://localhost:8501` |
| `DB_NAME` | PostgreSQL database name. | `cs2_db` |
| `DB_USER` | PostgreSQL user. | `postgres` |
| `DB_PASS` | PostgreSQL password. | `change_me` |
| `DB_HOST` | PostgreSQL host. | `localhost` |
| `DB_PORT` | PostgreSQL port. | `5432` |

Optional variables:

| Variable | Purpose | Default |
| --- | --- | --- |
| `SOURCE_URL` | Overrides the results discovery URL used by the results scraper. | Built-in results source |

Production mode fails fast when required runtime variables are missing, when
`DEBUG_MODE=true`, or when `API_CORS_ORIGINS` includes `*`.

### 5. Set Up Database

Ensure PostgreSQL is installed and configure database credentials through your
local environment or `.env`.

Run the non-destructive migration path:

```sh
python manage_db.py --init
```

Running `python manage_db.py` with no flags also applies migrations. Deployed
environments should run the equivalent Alembic command during release startup:

```sh
alembic -c cs2_analytics/alembic.ini upgrade head
```

Day-to-day migration operations are also exposed through the CLI. Each
command first prints the target database (name, host, and port) so it is
obvious whether the environment points at a local or production database:

```sh
cs2a db current                  # show the database's current revision
cs2a db upgrade                  # apply migrations up to head; confirms first
cs2a db downgrade <revision>     # revert to a revision; confirms first
```

These wrap the same `alembic -c cs2_analytics/alembic.ini ...` commands with
the same environment-driven connection settings.

For an existing database that was already initialized from the current
`schema.sql`, first confirm the live schema matches the initial Alembic
migration, then mark it as migration-managed without recreating tables:

```sh
alembic -c cs2_analytics/alembic.ini stamp head
```

For first-time local setup when the configured PostgreSQL database does not
exist yet, create it and then apply migrations:

```sh
python manage_db.py --create-database
```

To explicitly wipe application tables:

```sh
python manage_db.py --wipe
```

The wipe command asks for `y` confirmation before dropping tables. Alembic owns
the application/source schema; future dbt models will remain downstream and
will not manage ingestion tables.

### 6. Run With Docker Compose

The Phase 3.75 deployment baseline includes a local container runtime for
PostgreSQL, migrations, the API, and pipeline runs.

Build the application image and start PostgreSQL plus the API:

```sh
docker compose up --build app
```

Apply database migrations in the compose environment:

```sh
docker compose --profile tools run --rm migrate
```

Run the ingestion pipeline in the compose environment:

```sh
docker compose --profile tools run --rm pipeline
```

The API is available at `http://localhost:8000` by default. See
`docs/deployment.md` for Docker build, environment variable, runtime data, and
container command details.

Run the deterministic deployment smoke path after PostgreSQL, migrations, and
the API are available:

```sh
docker compose up -d db
docker compose --profile tools run --rm migrate
docker compose up -d app
docker compose --profile tools run --rm smoke
```

The smoke path seeds a tiny fixed-ID dataset, checks `/health`, verifies the API
can query PostgreSQL through the top players read path, and removes the smoke
rows before exiting. It should run against a local or deployment-validation
database, not a production analytics database, and does not depend on live
website scraping.

### 7. Run the Pipeline

```sh
python main.py
```

Or use the `cs2a` CLI installed with the package for individual stages:

```sh
cs2a ingest discover            # scrape results pages, queue new matches
cs2a ingest discover --mode backfill
cs2a process --batch 50         # process pending matches, then maps
cs2a status                     # ingestion-state row counts by status
```

### 8. Run the API

```sh
python run_api.py
```

Then open the host and port configured by `API_HOST` and `API_PORT`, such as
`http://127.0.0.1:8000/docs`.

### 9. Run Tests

```sh
python -m pytest
```

### 10. Run dbt (analytics transformations)

dbt is installed with the dev dependencies (`uv sync`). Its default target is a
**local** Postgres, so `dbt run` never touches a deployed database by accident.
dbt uses its own `DBT_DB_*` variables (with local defaults, see `.env.example`)
and does not read `.env` itself. Start a local Postgres, load the schema, then
run dbt:

```sh
docker compose --env-file .env.example up -d db
env DB_HOST=localhost DB_USER=postgres DB_PASS=change_me DB_NAME=cs2_db \
  uv run alembic -c cs2_analytics/alembic.ini upgrade head
uv run dbt debug --project-dir dbt --profiles-dir dbt
uv run dbt run --project-dir dbt --profiles-dir dbt
```

To run against a deployed database on purpose, export its `DB_*` values and
name the `prod` target explicitly:

```sh
set -a; source .env; set +a
uv run dbt run --project-dir dbt --profiles-dir dbt --target prod
```

dbt owns analytics transformations only; the ingestion schema stays owned by
Alembic migrations. Sources are declared for the `matches`, `maps`, and
`players` tables. The staging layer (`stg_matches`, `stg_maps`, `stg_players`)
is thin views over those sources. See `docs/dbt_models.md` for the planned
model layers.

Note: Demo processing is still deferred and intentionally remains outside the active ingestion pipeline; its implementation lives on the `feature/demo-parsing` branch.

## Architecture Notes

Current stage boundaries:

- Controllers coordinate batches, retry policy, scraper reset/rotation, and summaries.
- Stage services own per-item fetch, parse, persist, and lifecycle outcome work.
- Scrapers fetch remote content only.
- Parsers convert fetched content into structured outputs only.
- Storage modules centralize relational writes.
- Ingestion-state tables track lifecycle for discovered matches, maps, and demos.

Current active flow:

```text
results discovery
-> match_ingestion_state refresh
-> MatchController batch
-> MatchStageService per-item workflow
-> map/demo ingestion-state refresh
-> MapController batch
-> MapStageService per-item workflow
-> relational storage
```

## Design Decisions & Tradeoffs

Short reasoning behind the choices that shaped the system. Full ADR-style
records live in `docs/architecture/decision_log.md`.

### Layered pipeline boundaries

Controllers, stage services, scrapers, parsers, and storage are separate
layers with one job each: controllers own batch coordination and retry
policy, stage services own a single item's fetch-parse-persist workflow,
scrapers only fetch, parsers only parse, and storage centralizes writes.
The tradeoff is more indirection than a small project strictly needs — but
each layer is testable without the others (parsers run against saved HTML,
no browser), scraping failures stay contained to the layer that talks to
the network, and later stages (dbt, new sources) attach without rewrites.
This split came from experience, not upfront design: controllers originally
absorbed per-item work until the mixed responsibilities made retry behavior
hard to reason about.

### Ingestion state over work queues

Discovered matches, maps, and demos live in PostgreSQL-backed
ingestion-state tables (`discovered`, `processing`, `processed`, `failed`,
`skipped`, `dead`, `partial`) rather than a disposable work queue. Rows are
keyed by source ID, so rediscovery refreshes existing rows instead of
duplicating work, and a rerun after a crash resumes from state instead of
starting over. The `skipped` versus `failed` distinction is deliberate:
`skipped` records an intentional decision not to process (for example a
forfeited match with no stats), while `failed` means a processing attempt
went wrong, and `dead` marks rows whose retries are exhausted so claim
queries can exclude them without counting failures. `partial` is reserved
for matches processed while some of their maps never reached a terminal
state. Collapsing these would make failure metrics lie. The tradeoff is
more lifecycle discipline than a queue requires — every outcome must be
recorded explicitly — in exchange for an ingestion run that is resumable,
idempotent, and observable.

### Stable grains and idempotent writes before analytics

The parsed source tables were locked to explicit grains before any
analytics work: `matches` is one row per match, `maps` one row per played
map, `players` one row per player per map. Storage writes are upserts that
refresh trusted fields, so re-running ingestion over the same matches never
duplicates rows. This was done ahead of the planned dbt layer because
transformation models are only as trustworthy as their sources — building
dbt on tables that could drift or duplicate would push data-quality
firefighting downstream where it is hardest to debug. The tradeoff is
slower feature delivery up front: schema and write-path discipline landed
before any user-visible analytics did.

### Simple, managed deployment first

The first cloud deployment uses deliberately simple, proven parts: Render
for the API and PostgreSQL, GitHub Pages for the frontend, and a manual
GitHub Actions workflow as the scraper runner — no Kubernetes, no Airflow, no
custom domain. Render builds the repository's own Dockerfile, so production
runs the same container image and the same entrypoints used locally through
Docker Compose (`python run_api.py` for the API, `python main.py` for the
pipeline) — one runtime to debug instead of a separate cloud configuration.
Production validation is read-only by policy: health checks and DB-backed
reads, with write-based smoke tests restricted to disposable databases. The tradeoff is fewer operational
capabilities (no scheduling, manual migrations) in exchange for a
deployment simple enough to reason about while the data layer is still
evolving.

### Demo parsing deferred behind a preserved boundary

Demo files introduce a different workload class: large binary downloads,
temporary-file lifecycle, long parses, and event-level extraction. Rather
than bolt that onto the match/map surface, demo processing is deferred
until the analytics layer (dbt) exists and downstream demo needs are
concrete. The boundary is kept, not deleted: demo links are still
discovered during match processing and tracked in the demo
ingestion-state table, while the non-working downloader/parser
implementation lives on the `feature/demo-parsing` branch until
acquisition is unblocked. Demo expansion plugs back into the same
controller/stage-service pattern later. The tradeoff is no event-level
stats yet, in exchange for keeping the active pipeline small enough to
harden and deploy.

## Data Insights & Usage (planned)

- Current API surface includes a player-oriented read path for top players by
  average rating, shown live on the public demo page.
- View per-match player performance.
- Compare teams' win rates on specific maps.
- Identify key players in matchups.
- Add transformed analytics models through dbt.
- Expand API read paths over trusted transformed tables.

## Developer Notes

See `docs/` for architecture and roadmap details.

Current architecture direction:

- Phases 2, 3, 3.5, 3.6, and 3.75 are complete.
- Frontend Phase A shipped the public GitHub Pages demo backed by the live
  API (see `docs/frontend_backlog.md`).
- Phase 3.9 (environment and tooling hardening) is in progress.
- Phase 4 (dbt transformation layer) follows Phase 3.9. Entry criteria include
  v1.0 hardening items for ingestion layer correctness and atomic writes.
- Demo pipeline implementation remains deferred.
- Airflow comes after dbt and clean transformation boundaries.

## License

This project is licensed under the MIT License.

## Contact & Support

- GitHub Issues: [CS2-analytics Issues](https://github.com/dardenkyle/CS2-analytics/issues)
- Email: [dardenkyle@example.com](mailto:dardenkyle@example.com)
