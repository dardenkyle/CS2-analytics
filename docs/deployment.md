# Deployment Baseline

Phase 3.75 keeps deployment focused on packaging the existing Python runtime.
The container runs the same entrypoints used locally:

- API: `python run_api.py`
- migrations: `python manage_db.py --init`
- pipeline: `python main.py`

dbt, Airflow, long-running schedulers, and demo expansion remain out of scope.

## Local Docker Startup

Build the application image:

```sh
docker build -t cs2-analytics:local .
```

Start PostgreSQL and the API:

```sh
docker compose up --build app
```

The API binds to `0.0.0.0` in the container and is published on
`http://localhost:8000` by default. Check the health response or FastAPI docs:

```sh
curl http://localhost:8000/health
curl http://localhost:8000/docs
```

## Migrations

Apply Alembic migrations against the compose PostgreSQL service:

```sh
docker compose --profile tools run --rm migrate
```

This runs:

```sh
python manage_db.py --init
```

The command is non-destructive and applies
`alembic -c cs2_analytics/alembic.ini upgrade head` through the project setup
entrypoint.

## Pipeline Run

Run the current ingestion pipeline in the container:

```sh
docker compose --profile tools run --rm pipeline
```

The pipeline still follows the existing application flow:

```text
results discovery -> match processing -> map processing
```

Demo download and parsing remain deferred.

## Deployment Smoke Test

Run the deterministic deployment smoke path after PostgreSQL, migrations, and
the API are available:

```sh
docker compose up -d db
docker compose --profile tools run --rm migrate
docker compose up -d app
docker compose --profile tools run --rm smoke
```

The smoke script validates that migrations created the expected source tables,
cleans up any stale fixed-ID smoke rows, seeds a tiny fixed-ID match/map/player
dataset through the existing storage upsert functions, checks `GET /health`,
checks `GET /api/top_players?min_maps=1&limit=100` for the seeded smoke player,
and removes the fixed-ID smoke rows before exiting.

This path is intentionally deterministic and does not call HLTV. Live scraping
can be checked manually with the pipeline command above, but deployment smoke
tests should not fail because the upstream website is unavailable or has
changed markup. Run it against local, smoke, staging, or otherwise disposable
deployment-validation databases rather than a production analytics database.

## Environment

Compose provides container-safe defaults for local development. Override these
through your shell environment or a local `.env` file when needed.

| Variable | Default | Notes |
| --- | --- | --- |
| `ENVIRONMENT` | `development` | Use `production` only with all required variables set explicitly. |
| `DEBUG_MODE` | `false` | Keeps Uvicorn reload disabled in the container. |
| `API_PORT` | `8000` | Published host port and in-container API port. |
| `API_CORS_ORIGINS` | localhost development origins | Comma-separated FastAPI CORS allowlist. |
| `DB_NAME` | `cs2_db` | PostgreSQL database created by the compose image. |
| `DB_USER` | `postgres` | PostgreSQL user. |
| `DB_PASS` | `change_me` | PostgreSQL password for local compose only. |
| `POSTGRES_HOST_PORT` | `5432` | Host port mapped to the PostgreSQL container. |
| `SMOKE_API_BASE_URL` | `http://app:8000` | API base URL used by the compose smoke service. |
| `SMOKE_API_TIMEOUT_SECONDS` | `10` | HTTP timeout used by the smoke script. |

The application container always uses `DB_HOST=db` and `DB_PORT=5432` when
running through compose.

## Runtime Data

The image excludes local credentials, caches, logs, generated parsed data, and
downloaded demos through `.dockerignore`.

Compose mounts generated runtime directories from the working tree:

- `./logs:/app/logs`
- `./demos:/app/demos`
- `./parsed_data:/app/parsed_data`

These directories are pre-created in the repository with placeholder files so
fresh Linux clones mount user-owned host paths instead of Docker-created
root-owned directories. Generated files inside those directories remain ignored
by Git. These mounts keep local runtime artifacts out of the image while
preserving the current application paths.
