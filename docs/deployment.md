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

## First Cloud Deployment Plan

The first cloud deployment keeps the runtime simple and uses managed services
that match the current container and script entrypoints.

Planned targets:

- Frontend: GitHub Pages.
- API runtime: Render web service.
- Pipeline and scraper runner: GitHub Actions manual workflow.
- Database: Render PostgreSQL.
- Secrets: Render environment variables for the API and database connection;
  GitHub Actions secrets for manual pipeline and deployment workflows.
- Migrations: manual release step from a controlled local environment first;
  a GitHub Actions migration workflow can be added later.

No custom domain is planned for the first deploy. The frontend should use the
default GitHub Pages URL, and the API CORS allowlist should include the GitHub
Pages origin. For a project page such as
`https://dardenkyle.github.io/CS2-analytics`, the browser origin is
`https://dardenkyle.github.io`.

## First Cloud Topology

The first deploy should use separate runtimes for reads and ingestion:

```text
GitHub Pages frontend
-> Render API web service
-> Render PostgreSQL

GitHub Actions manual pipeline workflow
-> build/run the application Docker image
-> execute python main.py inside the container
-> Render PostgreSQL
-> HLTV fetches through the containerized Chromium/Selenium runtime
```

The API and pipeline should continue using the existing entrypoints:

- API: `python run_api.py`
- migrations: `alembic -c cs2_analytics/alembic.ini upgrade head`
- pipeline: `python main.py`

The GitHub Actions pipeline workflow should run the same application image used
by the local container runtime, so scraper dependencies such as Chromium,
ChromiumDriver, SeleniumBase, and Python packages are supplied by the Docker
image rather than by the host runner.

GitHub Actions should be manual-only at first. Scheduled scraper runs are
deferred until the match and map batch behavior is validated, especially the
handoff from a fetched match batch to the number of discovered maps that still
need processing.

## Cloud Environment And Secrets

Render API environment variables:

| Variable | Source |
| --- | --- |
| `ENVIRONMENT=production` | Render environment variable |
| `DEBUG_MODE=false` | Render environment variable |
| `API_HOST=0.0.0.0` | Render environment variable |
| `API_PORT` | Map to Render's web service `PORT` value in the service start command or environment |
| `API_CORS_ORIGINS` | Render environment variable containing the GitHub Pages origin |
| `DB_NAME` | Render PostgreSQL connection setting |
| `DB_USER` | Render PostgreSQL connection setting |
| `DB_PASS` | Render secret |
| `DB_HOST` | Render PostgreSQL connection setting |
| `DB_PORT` | Render PostgreSQL connection setting |

GitHub Actions pipeline secrets:

| Secret | Purpose |
| --- | --- |
| `DB_NAME` | Pipeline database name |
| `DB_USER` | Pipeline database user |
| `DB_PASS` | Pipeline database password |
| `DB_HOST` | Pipeline database host |
| `DB_PORT` | Pipeline database port |

Secret values must stay out of the repository, docs, logs, and committed
configuration files. `.env.example` should keep placeholder values only.

## Migration Order

For the first cloud deploy, migrations are a manual release step:

1. Confirm the target database is the intended Render PostgreSQL instance.
2. Confirm or create a Render PostgreSQL recovery point where the database plan
   supports it, or take an exported logical backup before continuing.
3. Apply migrations from a controlled local environment:

   ```sh
   alembic -c cs2_analytics/alembic.ini upgrade head
   ```

4. Confirm the database revision is current:

   ```sh
   alembic -c cs2_analytics/alembic.ini current
   ```

5. Deploy or restart the Render API service.
6. Run read-only production validation checks.

Write-based deterministic smoke tests should not run against the production
analytics database.

## Validation Policy

Use separate validation paths for smoke/staging and production.

Smoke or staging validation may write fixed-ID synthetic rows, but it must run
against a separate minimal Render PostgreSQL database or another disposable
deployment-validation database. That database does not need to stay running all
the time.

Production validation must be read-only:

1. Confirm Alembic reports the expected current revision.
2. Call the API health endpoint:

   ```sh
   curl https://<render-api-host>/health
   ```

3. Call a DB-backed read endpoint without inserting synthetic rows, such as:

   ```sh
   curl "https://<render-api-host>/api/top_players?min_maps=1&limit=10"
   ```

4. Confirm API logs do not show startup, configuration, database, or CORS
   errors.

## Rollback And Recovery

The first deployment should prefer controlled recovery over automatic downgrade
migrations.

- Before manual migrations, confirm a Render PostgreSQL recovery point or
  exported logical backup exists.
- If the API deploy fails before migrations run, roll back the Render web
  service to the previous deploy.
- If migrations fail partway, stop the deploy, do not run the pipeline, inspect
  database state, then restore the pre-migration backup or apply a forward fix
  migration.
- If migrations succeed but application behavior fails, roll back the API
  runtime when the schema remains backward-compatible. Otherwise, apply a
  forward fix.
- If the pipeline run fails, treat it as ingestion recovery rather than schema
  rollback. Inspect lifecycle state, fix code or configuration, and retry
  manually.

The follow-up implementation branch is `phase3.75-first-cloud-deploy`, tracked
by issue #55.

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
