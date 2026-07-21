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

## Frontend GitHub Pages Deployment

The public React SPA deploys to GitHub Pages through
`.github/workflows/deploy-frontend.yml`. Pushes to `main` that touch
`frontend/**` (or the workflow file) build the SPA with Node 24 (`npm ci`,
`npm run build`) and publish `frontend/dist` to the `github-pages`
environment. The workflow can also be run manually from the Actions tab.

Deployment details:

- The app is served as a project page at
  `https://dardenkyle.github.io/CS2-analytics/`, so Vite's `base` is set to
  `/CS2-analytics/` in `frontend/vite.config.ts`.
- The build copies `index.html` to `404.html` so deep links and refreshes
  serve the SPA instead of the GitHub Pages 404 page.
- The deployed app calls the Render API using the base URL configured in
  `frontend/src/config.ts` (see `frontend/README.md` for the
  `VITE_API_BASE_URL` override).
- One-time repository setup: Settings -> Pages -> Build and deployment ->
  Source must be set to "GitHub Actions".

Frontend deploys are independent of the Render API service: publishing the
SPA never changes backend runtime, schema, or data.

## First Cloud Deployment Status

The first Render API deployment is available at:

```text
https://cs2-analytics.onrender.com
```

Validated production checks:

- `GET https://cs2-analytics.onrender.com/health` returns
  `{"status":"ok","service":"cs2-analytics-api"}`.
- `GET https://cs2-analytics.onrender.com/` returns the same compatibility
  health payload.
- Alembic migrations have been applied to the Render PostgreSQL database.
- `GET https://cs2-analytics.onrender.com/api/top_players?min_maps=1&limit=10`
  returns DB-backed player rows from Render PostgreSQL.
- Local live ingestion has written real player data to Render PostgreSQL.
- The Docker worker image builds locally and can start Selenium/Chromium inside
  the container after the image grants the non-root app user ownership of
  SeleniumBase's driver scratch directory.
- Local Docker live pipeline execution completed in the worker image and
  reached the map stage against Render PostgreSQL. The map stage selected 50
  pending maps, but some fetched HTML lacked the expected `match-info-box`
  content. Issue #57 hardened map fetch validation so incomplete, blocked, or
  challenged map stats HTML is classified as a retryable scraper/session
  failure with diagnostics before parser handling. This confirms the deployment
  worker path while keeping recurring worker runs paused until broader live
  ingestion behavior and operations are intentionally resumed.
- The 2026-07-06 in-container browser validation failures (#91) were caused by
  Debian trixie's initial Chromium 150 package (`150.0.7871.46-1~deb13u1`),
  which SeleniumBase undetected mode could not connect to. The follow-up distro
  point release (`150.0.7871.124-1~deb13u1`) resolved the failure with no
  repository change: validation passes with it on both the then-current and
  current SeleniumBase releases. The worker path stays paused pending #66.
- To keep worker builds reproducible instead of drifting with `pip` resolution,
  the Docker image installs Python dependencies pinned by `uv.lock` (via
  `uv export --frozen`). Upgrading the browser automation stack now happens
  through a reviewed `uv.lock` update rather than silently at build time.
  Chromium and its driver still come from the Debian package archive, which
  only serves current point releases, so the browser itself can still drift;
  `scripts/validate_worker_browser.py` logs the Chromium, ChromeDriver,
  SeleniumBase, and Selenium versions on every run so any future failure is
  immediately attributable to a specific stack.

Local worker validation commands:

```powershell
docker build -t cs2-analytics:manual-worker .
docker run --rm --shm-size=2g --env-file .env.render `
  -e ENVIRONMENT=production `
  -e DEBUG_MODE=false `
  -e API_HOST=0.0.0.0 `
  -e API_PORT=8000 `
  -e API_CORS_ORIGINS=https://dardenkyle.github.io `
  cs2-analytics:manual-worker `
  python scripts/validate_worker_browser.py
```

Run the live pipeline through the same container with:

```powershell
docker run --rm --shm-size=2g --env-file .env.render `
  -e ENVIRONMENT=production `
  -e DEBUG_MODE=false `
  -e API_HOST=0.0.0.0 `
  -e API_PORT=8000 `
  -e API_CORS_ORIGINS=https://dardenkyle.github.io `
  cs2-analytics:manual-worker `
  python main.py
```

Observed local Docker worker result:

```text
MapController summary: selected=50 succeeded=0 failed=50 retries=0
CS2 Analytics Pipeline complete.
```

The manual GitHub Actions workflow is defined in the repository, but it will
only become runnable from GitHub Actions after the workflow file is pushed and
available to GitHub. Deterministic write-based smoke remains restricted to a
separate smoke/staging database and must not be run against the production
Render PostgreSQL analytics database.

For the first cloud branch, creating a separate Render smoke/staging database is
deferred to a follow-up because it would add cost and secret/configuration
maintenance before recurring deployment validation needs it. The deterministic
smoke script remains the accepted write-based validation path, but cloud smoke
execution should wait until a disposable validation database exists. Production
validation remains read-only, and live ingestion validation uses real pipeline
execution rather than synthetic smoke rows.

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

GitHub Actions is manual-only at first. The workflow lives at
`.github/workflows/manual-pipeline-worker.yml`, builds the application Docker
image, validates that Selenium/Chromium can start inside the container, and can
then run `python main.py` against the configured PostgreSQL database. Scheduled
scraper runs are deferred until the match and map batch behavior is validated,
especially the handoff from a fetched match batch to the number of discovered
maps that still need processing.

Run the manual worker from GitHub:

1. Open the repository in GitHub.
2. Go to Actions.
3. Select `Manual Pipeline Worker`.
4. Choose `Run workflow`.
5. Leave `run_pipeline` disabled to validate only the containerized
   Selenium/Chromium runtime. Enable it only when intentionally running live
   ingestion against the configured PostgreSQL database.

The workflow uses a concurrency group so only one manual pipeline worker run
executes at a time.

## Cloud Environment And Secrets

Render API environment variables:

| Variable | Source |
| --- | --- |
| `ENVIRONMENT=production` | Render environment variable |
| `DEBUG_MODE=false` | Render environment variable |
| `API_HOST=0.0.0.0` | Render environment variable |
| `API_PORT` | Must resolve to Render's web service `PORT` value |
| `API_CORS_ORIGINS` | Render environment variable with the comma-separated browser origin allowlist: the GitHub Pages origin, plus local frontend dev origins as needed |
| `DB_NAME` | Render PostgreSQL connection setting |
| `DB_USER` | Render PostgreSQL connection setting |
| `DB_PASS` | Render secret |
| `DB_HOST` | Render PostgreSQL connection setting |
| `DB_PORT` | Render PostgreSQL connection setting |

Render provides the port a web service must bind to through `PORT`. The app
reads `API_PORT`, so the Render start command should map `PORT` explicitly:

```sh
API_PORT=$PORT python run_api.py
```

Keep `API_HOST=0.0.0.0` so the service binds on the container interface Render
can route to.

GitHub Actions pipeline secrets:

| Secret | Purpose |
| --- | --- |
| `DB_NAME` | Pipeline database name |
| `DB_USER` | Pipeline database user |
| `DB_PASS` | Pipeline database password |
| `DB_HOST` | Pipeline database host |
| `DB_PORT` | Pipeline database port |

Use Render's external PostgreSQL host for local migration commands and for the
GitHub Actions manual worker. The short internal hostname is only reachable
from Render services on Render's private network.

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

No write-based deterministic smoke check should run against the first production
Render PostgreSQL database. Until a separate smoke/staging database exists,
record the smoke result as deferred by policy and use read-only production
validation plus limited live ingestion validation for deployment confidence.

Production validation must be read-only:

1. Confirm Alembic reports the expected current revision.
2. Call the API health endpoint:

   ```sh
   curl https://cs2-analytics.onrender.com/health
   ```

3. Call a DB-backed read endpoint without inserting synthetic rows, such as:

   ```sh
   curl "https://cs2-analytics.onrender.com/api/top_players?min_maps=1&limit=10"
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
