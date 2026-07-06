# Counter-Strike 2 Pro Match Analytics Tool

[![CI](https://github.com/dardenkyle/CS2-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/dardenkyle/CS2-analytics/actions/workflows/ci.yml)
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

The current ingestion architecture uses PostgreSQL-backed ingestion-state tables, thin controllers for batch orchestration, and stage services for per-item match/map/demo workflow boundaries.

## Features

### Data Ingestion

- Results discovery refreshes match ingestion-state rows.
- Match processing collects match metadata and discovers downstream map/demo links.
- Map processing collects player performance metrics such as kills, deaths, assists, ADR, KAST, opening duels, multi-kills, clutches, and round swing.
- Ingestion hardening uses retry/backoff, browser session recovery, and lifecycle tracking for resilient scraping runs.

### Deferred / Later-Phase Work

- Demo processing: demo download and parsing remain deferred, though `DemoStageService` preserves the stage boundary.
- Deployment baseline: containerized runtime, environment-driven configuration,
  migrations, CI, and smoke tests come before dbt.
- dbt transformation layer: dbt follows the deployment baseline and stays
  downstream of ingestion.
- Airflow orchestration: Airflow comes after dbt and clean stage boundaries.

## Tech Stack

- Python 3.12
- SeleniumBase and BeautifulSoup for web scraping
- PostgreSQL for structured data storage, with Alembic-managed migrations
- Pandas and NumPy for analytics/data processing
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
|   |-- services/
|   |-- storage/
|   `-- utils/
|-- docs/
|-- logs/
|-- scripts/
|-- tests/
|-- demos/
|-- parsed_data/
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
uv sync --extra dev
```

This creates a `.venv` virtual environment and installs all runtime and
development dependencies from the committed `uv.lock` lockfile. Once
dev dependencies move to `[dependency-groups]` (issue #69), this
becomes `uv sync`.

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

Note: Demo processing is still deferred and intentionally remains outside the active ingestion pipeline.

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
ingestion-state tables (`pending`, `processing`, `processed`, `failed`,
`skipped`) rather than a disposable work queue. Rows are keyed by source ID,
so rediscovery refreshes existing rows instead of duplicating work, and a
rerun after a crash resumes from state instead of starting over. The
`skipped` versus `failed` distinction is deliberate: `skipped` records an
intentional decision not to process (for example a forfeited match with no
stats), while `failed` means processing was attempted and exhausted its
retries. Collapsing the two would make failure metrics lie. The tradeoff is
more lifecycle discipline than a queue requires — every outcome must be
recorded explicitly — in exchange for an ingestion run that is resumable,
idempotent, and observable.

### One source, no pluggable-source abstraction

The pipeline ingests from a single upstream site, and there is deliberately
no generic "source adapter" interface. An abstraction over one
implementation would be speculative complexity: it could not be validated
against a second source and would slow down changes to the only source that
exists. The existing layer boundaries already isolate site-specific logic —
scrapers and parsers are the only layers that know about the upstream
markup — so supporting a second source later means adding a scraper and a
parser, not restructuring the pipeline. The accepted cost is that
site-specific assumptions live in those two layers rather than behind a
formal interface.

### Demo parsing deferred behind a preserved boundary

Demo files introduce a different workload class: large binary downloads,
temporary-file lifecycle, long parses, and event-level extraction. Rather
than bolt that onto the match/map surface, demo processing is deferred
until the analytics layer (dbt) exists and downstream demo needs are
concrete. The boundary is kept, not deleted: `DemoStageService` and the
demo ingestion-state table preserve the stage shape, so demo expansion
plugs into the same controller/stage-service pattern later. The tradeoff
is no event-level stats yet, in exchange for keeping the active pipeline
small enough to harden and deploy.

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
