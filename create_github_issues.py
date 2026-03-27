"""
Script to create GitHub issues for CS2 Analytics production deployment roadmap.
Requires: pip install PyGithub python-dotenv
"""

import os
from github import Github
from github.GithubException import GithubException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# GitHub configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = "dardenkyle/CS2-analytics"

# Define all labels needed
LABELS = {
    "infrastructure": {
        "color": "0052cc",
        "description": "Infrastructure and deployment related",
    },
    "priority: critical": {
        "color": "b60205",
        "description": "Critical priority - blocking production",
    },
    "priority: high": {
        "color": "d93f0b",
        "description": "High priority - important for production",
    },
    "priority: medium": {
        "color": "fbca04",
        "description": "Medium priority - nice to have",
    },
    "priority: low": {
        "color": "0e8a16",
        "description": "Low priority - future enhancement",
    },
    "docker": {"color": "1d76db", "description": "Docker and containerization"},
    "local-dev": {"color": "c5def5", "description": "Local development environment"},
    "backend": {"color": "5319e7", "description": "Backend code and services"},
    "config": {"color": "bfd4f2", "description": "Configuration management"},
    "security": {"color": "ee0701", "description": "Security and authentication"},
    "api": {"color": "7057ff", "description": "API endpoints and routes"},
    "observability": {
        "color": "006b75",
        "description": "Monitoring, logging, and tracing",
    },
    "aws": {"color": "ff9900", "description": "AWS services and deployment"},
    "secrets": {"color": "d73a4a", "description": "Secrets and credentials management"},
    "logging": {"color": "1d76db", "description": "Logging and log management"},
    "rate-limiting": {"color": "f9d0c4", "description": "Rate limiting and throttling"},
    "database": {"color": "0e8a16", "description": "Database operations and schema"},
    "migrations": {"color": "c2e0c6", "description": "Database migrations"},
    "reliability": {
        "color": "fbca04",
        "description": "System reliability and resilience",
    },
    "concurrency": {
        "color": "d876e3",
        "description": "Concurrency and parallel processing",
    },
    "pipeline": {"color": "5319e7", "description": "Data pipeline and processing"},
    "data-quality": {
        "color": "0075ca",
        "description": "Data validation and quality checks",
    },
    "testing": {"color": "d4c5f9", "description": "Testing and quality assurance"},
    "web-scraping": {"color": "c5def5", "description": "Web scraping related"},
    "async": {
        "color": "bfdadc",
        "description": "Async/await and asynchronous processing",
    },
    "refactor": {"color": "ededed", "description": "Code refactoring"},
    "queue": {"color": "1d76db", "description": "Queue systems and messaging"},
    "quality": {"color": "0075ca", "description": "Code quality"},
    "monitoring": {"color": "006b75", "description": "Monitoring and metrics"},
    "alerting": {"color": "d93f0b", "description": "Alerting and notifications"},
    "tracing": {"color": "0e8a16", "description": "Distributed tracing"},
    "ci-cd": {"color": "84b6eb", "description": "CI/CD pipelines and automation"},
    "automation": {"color": "5319e7", "description": "Automation and tooling"},
    "github-actions": {"color": "2088ff", "description": "GitHub Actions workflows"},
    "deployment": {"color": "ff9900", "description": "Deployment processes"},
    "iac": {"color": "0052cc", "description": "Infrastructure as Code"},
    "terraform": {"color": "5c4ee5", "description": "Terraform IaC"},
    "architecture": {"color": "1d76db", "description": "System architecture"},
    "scalability": {"color": "0e8a16", "description": "Scalability and performance"},
    "high-availability": {"color": "d93f0b", "description": "High availability"},
    "versioning": {"color": "bfd4f2", "description": "API versioning"},
    "documentation": {"color": "0075ca", "description": "Documentation"},
    "auth": {"color": "ee0701", "description": "Authentication and authorization"},
    "operations": {"color": "fbca04", "description": "Operations and runbooks"},
    "backup": {"color": "d93f0b", "description": "Backup and recovery"},
    "disaster-recovery": {"color": "b60205", "description": "Disaster recovery"},
    "cost-optimization": {"color": "0e8a16", "description": "Cost optimization"},
    "performance": {"color": "84b6eb", "description": "Performance optimization"},
}

# Define all issues
ISSUES = [
    {
        "title": "Create Multi-Stage Dockerfile for Application",
        "body": """## Why It's Needed
Application currently runs locally without containerization. AWS Fargate/ECS deployment requires Docker containers. SeleniumBase with Chrome needs special container configuration.

## Acceptance Criteria
- [ ] Multi-stage Dockerfile (builder + slim runtime)
- [ ] Chrome/Chromium installed for headless SeleniumBase
- [ ] Non-root user configured for security
- [ ] Final image size <800MB
- [ ] Environment variables properly injected at runtime
- [ ] Health check endpoint implemented (`/health`)
- [ ] Successfully builds and runs locally with `docker build` and `docker run`
- [ ] Scraping functionality works inside container

## Implementation Notes
```dockerfile
# Stage 1: Builder
FROM python:3.13-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Stage 2: Runtime
FROM python:3.13-slim
RUN apt-get update && apt-get install -y \\
    chromium chromium-driver curl \\
    && rm -rf /var/lib/apt/lists/*
    
COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/*

RUN useradd -m -u 1000 appuser
USER appuser
WORKDIR /app
COPY --chown=appuser:appuser . .

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s \\
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "main.py"]
```

## Dependencies
None

## Phase
Phase 1: Infrastructure Foundation (Week 1-2)
""",
        "labels": ["infrastructure", "priority: critical", "docker"],
        "milestone": 1,
    },
    {
        "title": "Create Docker Compose for Local Development Stack",
        "body": """## Why It's Needed
Currently requires manual PostgreSQL setup. Docker Compose provides consistent local development environment matching production architecture.

## Acceptance Criteria
- [ ] `docker-compose.yml` with services: `app`, `postgres`, `api`
- [ ] PostgreSQL 15+ with persistent volume
- [ ] Automatic database schema initialization on first run
- [ ] Environment variables configured via `.env` file
- [ ] Health checks for all services
- [ ] Port mappings: PostgreSQL (5433), API (8000), Streamlit (8501)
- [ ] Network configuration for inter-service communication
- [ ] Documentation in README for `docker-compose up`

## Implementation Notes
```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASS}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./cs2_analytics/storage/schema.sql:/docker-entrypoint-initdb.d/schema.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      
  app:
    build: .
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DB_HOST: postgres
      DB_PORT: 5432
```

## Dependencies
Issue #1

## Phase
Phase 1: Infrastructure Foundation (Week 1-2)
""",
        "labels": ["infrastructure", "priority: critical", "docker", "local-dev"],
        "milestone": 1,
    },
    {
        "title": "Implement Pydantic-Based Configuration Management",
        "body": """## Why It's Needed
Current config uses plain `os.getenv()` without validation. No type safety, no validation, secrets exposed in code. Need environment-specific configs (dev/staging/prod).

## Acceptance Criteria
- [ ] Replace `config.py` with Pydantic `BaseSettings` model
- [ ] Type validation for all config variables
- [ ] Environment-specific config classes (`DevConfig`, `ProdConfig`)
- [ ] Required fields enforced (fail fast on missing critical config)
- [ ] Secrets loaded from environment only (never committed)
- [ ] Config validation on application startup
- [ ] `.env.example` template file created
- [ ] Remove hardcoded defaults for sensitive data

## Implementation Notes
```python
from pydantic import BaseSettings, PostgresDsn, validator
from typing import Literal

class Settings(BaseSettings):
    # Database
    database_url: PostgresDsn
    db_pool_size: int = 10
    db_max_overflow: int = 20
    
    # Scraping
    hltv_base_url: str = "https://www.hltv.org"
    max_retries: int = 3
    request_timeout: int = 30
    
    # Environment
    environment: Literal["development", "staging", "production"]
    debug: bool = False
    
    # Secrets
    api_secret_key: str
    
    @validator("database_url", pre=True)
    def assemble_db_connection(cls, v, values):
        if isinstance(v, str):
            return v
        return PostgresDsn.build(...)
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

## Dependencies
None

## Phase
Phase 1: Infrastructure Foundation (Week 1-2)
""",
        "labels": ["backend", "priority: critical", "config", "security"],
        "milestone": 1,
    },
    {
        "title": "Add Health Check and Readiness Endpoints to FastAPI",
        "body": """## Why It's Needed
AWS load balancers and orchestrators (ECS/Fargate) require health checks. Current API has no health endpoints. Need to verify database connectivity and application state.

## Acceptance Criteria
- [ ] `GET /health` endpoint returns 200 when app is running
- [ ] `GET /health/ready` checks database connectivity
- [ ] Returns appropriate status codes (200, 503) based on health
- [ ] JSON response with component status (db, scraper availability)
- [ ] Responds within 2 seconds
- [ ] Does not log every health check (noise reduction)
- [ ] Documented in API docs (`/docs`)

## Implementation Notes
```python
from datetime import datetime
from fastapi import HTTPException

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/health/ready", tags=["Health"])
def readiness_check():
    try:
        # Test database connection
        with db.get_cursor() as cur:
            cur.execute("SELECT 1")
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail="Database unavailable")
```

## Dependencies
None

## Phase
Phase 1: Infrastructure Foundation (Week 1-2)
""",
        "labels": ["api", "priority: critical", "observability"],
        "milestone": 1,
    },
    {
        "title": "Implement Secrets Management with AWS Secrets Manager",
        "body": """## Why It's Needed
Database credentials and API keys currently in `.env` file. Production needs centralized secrets management with rotation capabilities.

## Acceptance Criteria
- [ ] AWS Secrets Manager integration implemented
- [ ] Boto3 client for secrets retrieval
- [ ] Secrets cached locally with TTL (5 minutes)
- [ ] Fallback to environment variables for local development
- [ ] Database password retrieved from Secrets Manager
- [ ] API secret key stored in Secrets Manager
- [ ] IAM role policy documented for ECS task
- [ ] Secrets rotation procedure documented

## Dependencies
Issue #3 (Pydantic Configuration)

## Phase
Phase 2: Security & Configuration (Week 2)
""",
        "labels": ["security", "priority: critical", "aws", "secrets"],
        "milestone": 2,
    },
    {
        "title": "Add Request ID Middleware and Structured Logging",
        "body": """## Why It's Needed
Current logging lacks request tracing. Production debugging requires correlation between logs across services. Need structured logs for CloudWatch Insights.

## Acceptance Criteria
- [ ] FastAPI middleware generates unique `X-Request-ID` for each request
- [ ] Request ID propagated through entire request lifecycle
- [ ] All log statements include request ID
- [ ] Structured JSON logging for production
- [ ] Human-readable logs for development
- [ ] Performance metrics logged (request duration)
- [ ] Error logs include full stack traces
- [ ] Log sampling for high-volume endpoints (health checks)

## Implementation Notes
```python
import structlog
from fastapi import Request
import uuid

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    structlog.contextvars.bind_contextvars(request_id=request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

## Dependencies
None

## Phase
Phase 2: Security & Configuration (Week 2)
""",
        "labels": ["observability", "priority: high", "logging", "backend"],
        "milestone": 2,
    },
    {
        "title": "Implement Rate Limiting and DDoS Protection",
        "body": """## Why It's Needed
Public API has no rate limiting. Vulnerable to abuse and DDoS. Need to protect backend and HLTV scraping (avoid IP bans).

## Acceptance Criteria
- [ ] SlowAPI or similar rate limiting middleware installed
- [ ] Per-IP rate limits: 100 requests/minute for API
- [ ] Per-endpoint limits for expensive operations
- [ ] Rate limit headers in responses (`X-RateLimit-*`)
- [ ] 429 status code returned when limit exceeded
- [ ] Redis backend for distributed rate limiting (multi-instance)
- [ ] Configurable limits per environment
- [ ] Whitelist for internal services/health checks

## Dependencies
None

## Phase
Phase 2: Security & Configuration (Week 2)
""",
        "labels": ["security", "priority: high", "api", "rate-limiting"],
        "milestone": 2,
    },
    {
        "title": "Add CORS, Security Headers, and API Hardening",
        "body": """## Why It's Needed
Current CORS allows all origins (`*`). Missing security headers expose vulnerabilities. Need production-grade API security.

## Acceptance Criteria
- [ ] CORS restricted to specific frontend domains
- [ ] Security headers middleware: `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`
- [ ] HTTPS-only cookies in production
- [ ] CSP (Content Security Policy) header configured
- [ ] Remove server version headers
- [ ] Input validation on all endpoints
- [ ] SQL injection protection verified
- [ ] API versioning implemented (`/api/v1`)

## Dependencies
None

## Phase
Phase 2: Security & Configuration (Week 2)
""",
        "labels": ["security", "priority: high", "api"],
        "milestone": 2,
    },
    {
        "title": "Implement Alembic Database Migrations",
        "body": """## Why It's Needed
Currently using raw SQL schema file. No migration tracking, version control, or rollback capability. Production needs controlled schema evolution.

## Acceptance Criteria
- [ ] Alembic initialized in project
- [ ] Initial migration created from current `schema.sql`
- [ ] Migration scripts for adding/modifying tables
- [ ] Rollback migrations tested
- [ ] Migration CI/CD integration (run before deployment)
- [ ] Migration documentation in README
- [ ] Version tracking in `alembic_version` table
- [ ] Separate migration configs for dev/prod

## Implementation Notes
```bash
alembic init alembic
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

## Dependencies
None

## Phase
Phase 3: Database & Data Quality (Week 3)
""",
        "labels": ["database", "priority: high", "migrations", "backend"],
        "milestone": 3,
    },
    {
        "title": "Add Database Connection Retry Logic and Circuit Breaker",
        "body": """## Why It's Needed
Current connection pool has no retry logic. Database restarts cause application crashes. Need resilient connection handling.

## Acceptance Criteria
- [ ] Exponential backoff retry on connection failures (3 attempts)
- [ ] Circuit breaker pattern for repeated failures
- [ ] Connection validation before query execution
- [ ] Automatic reconnection on stale connections
- [ ] Graceful degradation when database unavailable
- [ ] Health check reflects database state
- [ ] Logging of connection failures
- [ ] Configurable retry parameters

## Dependencies
None

## Phase
Phase 3: Database & Data Quality (Week 3)
""",
        "labels": ["database", "priority: high", "reliability", "backend"],
        "milestone": 3,
    },
    {
        "title": "Implement Queue Table Locking to Prevent Concurrency Issues",
        "body": """## Why It's Needed
Current `fetch()` in `BaseScrapeQueue` doesn't lock rows. Multiple workers can process same item. Need `SELECT FOR UPDATE SKIP LOCKED` for distributed processing.

## Acceptance Criteria
- [ ] Replace `SELECT` with `SELECT FOR UPDATE SKIP LOCKED`
- [ ] Row-level locking prevents duplicate processing
- [ ] Transaction wraps fetch + mark operations
- [ ] Lock timeout configured (avoid deadlocks)
- [ ] Testing with concurrent workers (2+ instances)
- [ ] Monitoring for lock contention
- [ ] Documentation of locking strategy

## Implementation Notes
```python
def fetch(self, limit: int = 25) -> list[tuple[str, str]]:
    query = f\"\"\"
    SELECT {self.id_field}, {self.url_field}
    FROM {self.table_name}
    WHERE status = 'queued'
    ORDER BY priority DESC, last_inserted_at ASC
    LIMIT %s
    FOR UPDATE SKIP LOCKED;
    \"\"\"
    # Must be within transaction context
```

## Dependencies
None

## Phase
Phase 3: Database & Data Quality (Week 3)
""",
        "labels": ["database", "priority: high", "concurrency", "pipeline"],
        "milestone": 3,
    },
    {
        "title": "Add Data Validation and Quality Checks",
        "body": """## Why It's Needed
No validation of scraped data before storage. Bad data causes downstream failures. Need Great Expectations or custom validators.

## Acceptance Criteria
- [ ] Pydantic models validate all scraped data before storage
- [ ] Required fields enforced (not null constraints)
- [ ] Data type validation (dates, integers, floats)
- [ ] Range checks (scores >= 0, ratings 0-2, etc.)
- [ ] URL format validation
- [ ] Duplicate detection before insert
- [ ] Failed validation logged with details
- [ ] Data quality metrics dashboard (future)

## Dependencies
None

## Phase
Phase 3: Database & Data Quality (Week 3)
""",
        "labels": ["data-quality", "priority: high", "backend", "testing"],
        "milestone": 3,
    },
    {
        "title": "Implement Exponential Backoff and Retry Logic for Scrapers",
        "body": """## Why It's Needed
No retry logic for failed HTTP requests. Temporary HLTV downtime causes permanent failures. Risk of IP bans from aggressive scraping.

## Acceptance Criteria
- [ ] `tenacity` library integrated
- [ ] Exponential backoff: 2^n seconds (max 60s)
- [ ] Max retries: 3 for transient errors (50x, timeouts)
- [ ] No retries for 4xx client errors
- [ ] Retry count logged
- [ ] Jitter added to prevent thundering herd
- [ ] Circuit breaker after repeated 429s (rate limit)
- [ ] Configurable retry strategy per scraper type

## Implementation Notes
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type((RequestException, Timeout)),
    before_sleep=lambda retry_state: logger.warning(f"Retry {retry_state.attempt_number}")
)
def fetch_with_retry(url: str) -> BeautifulSoup:
    ...
```

## Dependencies
None

## Phase
Phase 4: Pipeline Reliability (Week 3-4)
""",
        "labels": ["pipeline", "priority: high", "reliability", "web-scraping"],
        "milestone": 4,
    },
    {
        "title": "Add Request Timeout and Resource Limits to Scrapers",
        "body": """## Why It's Needed
No timeouts configured. Hung requests block pipeline indefinitely. Need resource limits for container stability.

## Acceptance Criteria
- [ ] HTTP request timeout: 30 seconds
- [ ] Page load timeout: 45 seconds for SeleniumBase
- [ ] Memory limits in Docker (2GB container limit)
- [ ] Max concurrent browser instances: 3
- [ ] Browser resource cleanup after each scrape
- [ ] Timeout exceptions logged and handled gracefully
- [ ] Failed scrapes marked with timeout reason

## Dependencies
Issue #13 (Exponential Backoff)

## Phase
Phase 4: Pipeline Reliability (Week 3-4)
""",
        "labels": ["pipeline", "priority: high", "reliability", "web-scraping"],
        "milestone": 4,
    },
    {
        "title": "Refactor Controllers to Support Async Processing",
        "body": """## Why It's Needed
Current controllers are synchronous (process one item at a time). Batch processing is slow. Need async/await for parallel execution.

## Acceptance Criteria
- [ ] Controllers refactored to use `async def`
- [ ] `asyncio.gather()` for parallel scraping (batch)
- [ ] Semaphore limits concurrent operations (max 5)
- [ ] Database operations use async driver (`asyncpg`)
- [ ] Error handling preserves individual item failures
- [ ] Performance improvement: 3-5x faster batch processing
- [ ] Backward compatibility with sync code maintained

## Dependencies
None

## Phase
Phase 4: Pipeline Reliability (Week 3-4)
""",
        "labels": ["pipeline", "priority: medium", "async", "backend", "refactor"],
        "milestone": 4,
    },
    {
        "title": "Implement Dead Letter Queue for Failed Scrapes",
        "body": """## Why It's Needed
Failed items marked as `failed` but never retried. No visibility into failure patterns. Need DLQ for manual review and retry.

## Acceptance Criteria
- [ ] Items moved to DLQ after max retry attempts (3)
- [ ] DLQ table: `failed_scrapes` with error details
- [ ] Admin endpoint to view/retry DLQ items
- [ ] Failed items include full error context
- [ ] Monitoring alerts on DLQ size thresholds
- [ ] Manual retry mechanism via API
- [ ] DLQ cleanup policy (30 days retention)

## Dependencies
Issue #13 (Exponential Backoff)

## Phase
Phase 4: Pipeline Reliability (Week 3-4)
""",
        "labels": ["pipeline", "priority: medium", "queue", "reliability"],
        "milestone": 4,
    },
    {
        "title": "Build Comprehensive Pytest Test Suite",
        "body": """## Why It's Needed
Only 2 test files exist with minimal coverage. No CI/CD tests. Production deployment needs >80% code coverage.

## Acceptance Criteria
- [ ] Pytest configured with `pytest.ini`
- [ ] Unit tests for all parsers (mock HTML responses)
- [ ] Integration tests for controllers (test database)
- [ ] API endpoint tests with TestClient
- [ ] Database tests with fixtures and rollback
- [ ] Mock SeleniumBase to avoid browser dependencies
- [ ] Coverage report generated (`pytest-cov`)
- [ ] Minimum 80% code coverage enforced

## Dependencies
None

## Phase
Phase 5: Testing & Quality Assurance (Week 4)
""",
        "labels": ["testing", "priority: medium", "quality"],
        "milestone": 5,
    },
    {
        "title": "Add Contract Testing for HLTV Scraping",
        "body": """## Why It's Needed
HLTV HTML structure changes break parsers silently. Need contract tests to detect upstream changes immediately.

## Acceptance Criteria
- [ ] Snapshot tests for HLTV page structures
- [ ] Weekly scheduled tests against live HLTV
- [ ] Alerts when page structure changes detected
- [ ] Test fixtures with real HTML samples (versioned)
- [ ] Parser regression tests with historical data
- [ ] CI/CD runs contract tests on PRs

## Dependencies
Issue #17 (Pytest Test Suite)

## Phase
Phase 5: Testing & Quality Assurance (Week 4)
""",
        "labels": ["testing", "priority: medium", "web-scraping", "monitoring"],
        "milestone": 5,
    },
    {
        "title": "Implement Load Testing for API Endpoints",
        "body": """## Why It's Needed
Unknown API performance under load. Need to verify scalability before public launch.

## Acceptance Criteria
- [ ] Locust or k6 load testing scripts
- [ ] Test scenarios: 100 concurrent users, 1000 req/min
- [ ] P95 latency < 500ms for read endpoints
- [ ] Database connection pool sizing verified
- [ ] Load test runs in CI/CD before deployment
- [ ] Performance baselines documented

## Dependencies
Issue #17 (Pytest Test Suite)

## Phase
Phase 5: Testing & Quality Assurance (Week 4)
""",
        "labels": ["testing", "priority: low", "performance", "api"],
        "milestone": 5,
    },
    {
        "title": "Integrate CloudWatch Logs and Metrics",
        "body": """## Why It's Needed
No centralized logging for production. Need CloudWatch integration for AWS deployment. Debugging production issues requires logs.

## Acceptance Criteria
- [ ] CloudWatch Logs agent configured in ECS task
- [ ] Application logs stream to CloudWatch Logs
- [ ] Log groups per service (api, pipeline, scraper)
- [ ] CloudWatch Insights queries for common patterns
- [ ] Log retention policy (30 days)
- [ ] Cost optimization (log filtering, sampling)
- [ ] IAM policies for log writing

## Dependencies
Issue #6 (Structured Logging)

## Phase
Phase 6: Observability & Monitoring (Week 5)
""",
        "labels": ["observability", "priority: medium", "aws", "monitoring"],
        "milestone": 6,
    },
    {
        "title": "Add Custom Metrics and Alarms",
        "body": """## Why It's Needed
No visibility into pipeline health. Need proactive alerts for failures, slow scraping, database issues.

## Acceptance Criteria
- [ ] Custom CloudWatch metrics: scrape success rate, queue depth, processing time
- [ ] CloudWatch alarms for critical thresholds
- [ ] SNS topic for alarm notifications (email/Slack)
- [ ] Alarm: Queue depth > 1000 items
- [ ] Alarm: Error rate > 5% over 5 minutes
- [ ] Alarm: Database connection failures
- [ ] Dashboard with key metrics (Grafana or CloudWatch)

## Dependencies
Issue #20 (CloudWatch Integration)

## Phase
Phase 6: Observability & Monitoring (Week 5)
""",
        "labels": ["observability", "priority: medium", "monitoring", "alerting"],
        "milestone": 6,
    },
    {
        "title": "Implement Distributed Tracing with X-Ray",
        "body": """## Why It's Needed
Complex pipeline requires end-to-end tracing. Need to identify bottlenecks and trace failures across services.

## Acceptance Criteria
- [ ] AWS X-Ray SDK integrated
- [ ] Traces for API requests, scraping, database operations
- [ ] Subsegments for each controller operation
- [ ] Error traces captured automatically
- [ ] Service map visualization in X-Ray console
- [ ] Performance profiling with trace analysis

## Dependencies
Issue #20 (CloudWatch Integration)

## Phase
Phase 6: Observability & Monitoring (Week 5)
""",
        "labels": ["observability", "priority: low", "tracing", "aws"],
        "milestone": 6,
    },
    {
        "title": "Create GitHub Actions CI/CD Pipeline",
        "body": """## Why It's Needed
No automated testing or deployment. Manual deployments error-prone. Need CI/CD for code quality and rapid iteration.

## Acceptance Criteria
- [ ] `.github/workflows/ci.yml` for pull request checks
- [ ] Run linting (black, flake8, mypy)
- [ ] Run full test suite on PRs
- [ ] Code coverage reporting (codecov.io)
- [ ] Docker image build and security scan
- [ ] Branch protection rules require passing CI
- [ ] Automated PR comments with test results

## Implementation Notes
```yaml
name: CI
on: [pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: pip install -r requirements.txt -r requirements-dev.txt
      - name: Run tests
        run: pytest --cov=cs2_analytics tests/
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Dependencies
Issue #17 (Pytest Test Suite)

## Phase
Phase 7: CI/CD & Deployment Automation (Week 5-6)
""",
        "labels": ["ci-cd", "priority: high", "automation", "github-actions"],
        "milestone": 7,
    },
    {
        "title": "Create GitHub Actions CD Pipeline for AWS ECS",
        "body": """## Why It's Needed
No automated deployment to AWS. Need continuous deployment for staging and production environments.

## Acceptance Criteria
- [ ] `.github/workflows/deploy.yml` triggers on main branch push
- [ ] Build Docker image and push to ECR
- [ ] Update ECS task definition with new image
- [ ] Deploy to staging environment automatically
- [ ] Manual approval gate for production deployment
- [ ] Rollback capability on deployment failure
- [ ] Slack notifications on deployment status

## Dependencies
- Issue #23 (CI Pipeline)
- Issue #25 (Terraform IaC)

## Phase
Phase 7: CI/CD & Deployment Automation (Week 5-6)
""",
        "labels": ["ci-cd", "priority: high", "deployment", "aws", "github-actions"],
        "milestone": 7,
    },
    {
        "title": "Create Terraform Infrastructure as Code",
        "body": """## Why It's Needed
Manual AWS resource creation is error-prone and not repeatable. Need IaC for consistent environments and disaster recovery.

## Acceptance Criteria
- [ ] Terraform modules for: VPC, ECS cluster, RDS PostgreSQL, ALB, ECR
- [ ] Separate Terraform workspaces for dev/staging/prod
- [ ] Remote state in S3 with DynamoDB locking
- [ ] IAM roles and policies defined
- [ ] Secrets Manager resources created
- [ ] CloudWatch log groups and alarms
- [ ] `terraform plan` runs in CI before apply
- [ ] Documentation for infrastructure deployment

## Implementation Structure
```
terraform/
├── modules/
│   ├── ecs/
│   ├── rds/
│   ├── networking/
│   └── monitoring/
├── environments/
│   ├── dev/
│   ├── staging/
│   └── production/
└── backend.tf
```

## Dependencies
None

## Phase
Phase 7: CI/CD & Deployment Automation (Week 5-6)
""",
        "labels": ["infrastructure", "priority: high", "iac", "terraform", "aws"],
        "milestone": 7,
    },
    {
        "title": "Migrate PostgreSQL Queue to AWS SQS",
        "body": """## Why It's Needed
PostgreSQL tables as queues don't scale well. SQS provides native queue features (DLQ, visibility timeout, message retention).

## Acceptance Criteria
- [ ] Create SQS queues: `match-scrape-queue`, `map-scrape-queue`, `demo-scrape-queue`
- [ ] Refactor `BaseScrapeQueue` to use boto3 SQS client
- [ ] Message format: JSON with metadata
- [ ] DLQ configured for failed messages (max 3 retries)
- [ ] Visibility timeout: 5 minutes
- [ ] Message retention: 7 days
- [ ] Graceful migration from database queues (dual write period)
- [ ] Performance comparison (throughput, latency)

## Dependencies
- Issue #3 (Pydantic Configuration)
- Issue #25 (Terraform IaC)

## Phase
Phase 8: AWS Architecture & Scalability (Week 6-7)
""",
        "labels": ["architecture", "priority: medium", "aws", "queue", "scalability"],
        "milestone": 8,
    },
    {
        "title": "Design Multi-AZ RDS PostgreSQL with Read Replicas",
        "body": """## Why It's Needed
Single database instance is single point of failure. Production needs HA, automatic failover, and read scaling.

## Acceptance Criteria
- [ ] RDS PostgreSQL 15 with Multi-AZ deployment
- [ ] Automated backups (7-day retention, point-in-time recovery)
- [ ] Read replica for analytics queries
- [ ] Connection pooling with PgBouncer
- [ ] SSL/TLS enforced for connections
- [ ] Parameter groups optimized for workload
- [ ] CloudWatch monitoring for database metrics
- [ ] Failover testing documented

## Dependencies
Issue #25 (Terraform IaC)

## Phase
Phase 8: AWS Architecture & Scalability (Week 6-7)
""",
        "labels": [
            "database",
            "priority: medium",
            "aws",
            "high-availability",
            "scalability",
        ],
        "milestone": 8,
    },
    {
        "title": "Implement API Versioning and Deprecation Strategy",
        "body": """## Why It's Needed
Current API has no versioning. Future changes will break frontend. Need versioned API with deprecation policy.

## Acceptance Criteria
- [ ] API routes prefixed with version: `/api/v1/`
- [ ] Version negotiation via Accept header
- [ ] Deprecation warnings in response headers
- [ ] Deprecated versions supported for 6 months
- [ ] Version documentation in OpenAPI spec
- [ ] Changelog maintained

## Dependencies
None

## Phase
Phase 9: API Enhancement & Documentation (Week 7-8)
""",
        "labels": ["api", "priority: low", "versioning", "documentation"],
        "milestone": 9,
    },
    {
        "title": "Add Comprehensive API Documentation and Examples",
        "body": """## Why It's Needed
Minimal API documentation. Frontend developers need clear examples, error codes, and authentication docs.

## Acceptance Criteria
- [ ] OpenAPI 3.0 spec fully documented
- [ ] Example requests/responses for each endpoint
- [ ] Error response catalog (4xx, 5xx codes)
- [ ] Authentication flow documented
- [ ] Rate limiting behavior explained
- [ ] Postman collection provided
- [ ] Interactive docs at `/docs` enhanced

## Dependencies
None

## Phase
Phase 9: API Enhancement & Documentation (Week 7-8)
""",
        "labels": ["documentation", "priority: medium", "api"],
        "milestone": 9,
    },
    {
        "title": "Implement API Authentication and Authorization",
        "body": """## Why It's Needed
Public API has no authentication. Need API keys for usage tracking, rate limiting per user, and potential monetization.

## Acceptance Criteria
- [ ] API key authentication implemented
- [ ] JWT tokens for user sessions
- [ ] OAuth2 password flow for frontend login
- [ ] Role-based access control (admin, user)
- [ ] API key management endpoints
- [ ] Rate limits per API key
- [ ] Usage analytics per API key

## Dependencies
Issue #7 (Rate Limiting)

## Phase
Phase 9: API Enhancement & Documentation (Week 7-8)
""",
        "labels": ["security", "priority: medium", "api", "auth"],
        "milestone": 9,
    },
    {
        "title": "Create Runbook for Common Operational Issues",
        "body": """## Why It's Needed
No operational documentation. On-call engineers need troubleshooting guides for common issues.

## Acceptance Criteria
- [ ] Runbook for: database connection failures, scraper IP bans, queue backlog, high memory usage
- [ ] Step-by-step resolution procedures
- [ ] Escalation paths documented
- [ ] Common log patterns with solutions
- [ ] Rollback procedures
- [ ] Contact information for external dependencies

## Dependencies
None

## Phase
Phase 10: Monitoring & Operations (Ongoing)
""",
        "labels": ["documentation", "priority: low", "operations"],
        "milestone": 10,
    },
    {
        "title": "Implement Automated Backup and Disaster Recovery",
        "body": """## Why It's Needed
No documented backup or DR strategy. Data loss prevention and business continuity requirements.

## Acceptance Criteria
- [ ] Automated RDS snapshots (daily, 30-day retention)
- [ ] Cross-region backup replication
- [ ] Disaster recovery plan documented
- [ ] Recovery time objective (RTO): 4 hours
- [ ] Recovery point objective (RPO): 1 hour
- [ ] DR drill schedule (quarterly)
- [ ] Backup restoration tested successfully

## Dependencies
Issue #27 (Multi-AZ RDS)

## Phase
Phase 10: Monitoring & Operations (Ongoing)
""",
        "labels": ["operations", "priority: medium", "backup", "disaster-recovery"],
        "milestone": 10,
    },
    {
        "title": "Set Up Cost Monitoring and Budget Alerts",
        "body": """## Why It's Needed
No visibility into AWS costs. Need budget alerts to prevent unexpected bills.

## Acceptance Criteria
- [ ] AWS Cost Explorer tags for resources
- [ ] Monthly budget alert ($100, $250, $500 thresholds)
- [ ] Cost allocation by service (ECS, RDS, SQS, ECR)
- [ ] Savings plan recommendations reviewed
- [ ] Unused resources identified and terminated
- [ ] Cost dashboard created

## Dependencies
Issue #25 (Terraform IaC)

## Phase
Phase 10: Monitoring & Operations (Ongoing)
""",
        "labels": ["operations", "priority: low", "aws", "cost-optimization"],
        "milestone": 10,
    },
]

# Define milestones
MILESTONES = {
    1: {
        "title": "Phase 1: Infrastructure Foundation",
        "description": "Core infrastructure setup with Docker, config management, and health checks",
        "due_on": "2025-12-14",
    },
    2: {
        "title": "Phase 2: Security & Configuration",
        "description": "Security hardening with secrets management, logging, and API protection",
        "due_on": "2025-12-21",
    },
    3: {
        "title": "Phase 3: Database & Data Quality",
        "description": "Database reliability with migrations, retries, and validation",
        "due_on": "2025-12-28",
    },
    4: {
        "title": "Phase 4: Pipeline Reliability",
        "description": "Scraper reliability with retries, timeouts, and async processing",
        "due_on": "2026-01-04",
    },
    5: {
        "title": "Phase 5: Testing & Quality Assurance",
        "description": "Comprehensive test suite and quality checks",
        "due_on": "2026-01-11",
    },
    6: {
        "title": "Phase 6: Observability & Monitoring",
        "description": "CloudWatch integration and monitoring infrastructure",
        "due_on": "2026-01-18",
    },
    7: {
        "title": "Phase 7: CI/CD & Deployment Automation",
        "description": "GitHub Actions pipelines and Terraform IaC",
        "due_on": "2026-01-25",
    },
    8: {
        "title": "Phase 8: AWS Architecture & Scalability",
        "description": "SQS migration and Multi-AZ RDS setup",
        "due_on": "2026-02-01",
    },
    9: {
        "title": "Phase 9: API Enhancement & Documentation",
        "description": "API versioning, documentation, and authentication",
        "due_on": "2026-02-08",
    },
    10: {
        "title": "Phase 10: Monitoring & Operations",
        "description": "Operational runbooks and ongoing maintenance",
        "due_on": "2026-02-15",
    },
}


def create_labels(repo):
    """Create all necessary labels in the repository."""
    print("\n🏷️  Creating labels...")
    existing_labels = {label.name: label for label in repo.get_labels()}

    for label_name, label_config in LABELS.items():
        if label_name in existing_labels:
            # Update existing label
            try:
                label = existing_labels[label_name]
                label.edit(
                    name=label_name,
                    color=label_config["color"],
                    description=label_config["description"],
                )
                print(f"  ✅ Updated label: {label_name}")
            except GithubException as e:
                print(f"  ⚠️  Failed to update label {label_name}: {e}")
        else:
            # Create new label
            try:
                repo.create_label(
                    name=label_name,
                    color=label_config["color"],
                    description=label_config["description"],
                )
                print(f"  ✅ Created label: {label_name}")
            except GithubException as e:
                print(f"  ⚠️  Failed to create label {label_name}: {e}")


def create_milestones(repo):
    """Create all milestones in the repository."""
    print("\n🎯 Creating milestones...")
    existing_milestones = {
        milestone.title: milestone for milestone in repo.get_milestones(state="all")
    }

    milestone_map = {}
    for milestone_num, milestone_config in MILESTONES.items():
        title = milestone_config["title"]
        if title in existing_milestones:
            milestone = existing_milestones[title]
            print(f"  ✅ Milestone already exists: {title}")
        else:
            try:
                milestone = repo.create_milestone(
                    title=title,
                    description=milestone_config["description"],
                    due_on=milestone_config.get("due_on"),
                )
                print(f"  ✅ Created milestone: {title}")
            except GithubException as e:
                print(f"  ⚠️  Failed to create milestone {title}: {e}")
                milestone = None

        milestone_map[milestone_num] = milestone

    return milestone_map


def create_issues(repo, milestone_map):
    """Create all issues in the repository."""
    print("\n📝 Creating issues...")

    for idx, issue_data in enumerate(ISSUES, start=1):
        try:
            # Get milestone object
            milestone = milestone_map.get(issue_data.get("milestone"))

            # Create issue
            issue = repo.create_issue(
                title=f"[Production] {issue_data['title']}",
                body=issue_data["body"],
                labels=issue_data["labels"],
                milestone=milestone,
            )

            print(f"  ✅ Created issue #{issue.number}: {issue_data['title']}")

        except GithubException as e:
            print(f"  ❌ Failed to create issue '{issue_data['title']}': {e}")


def main():
    """Main function to create all GitHub issues."""

    # Check for GitHub token
    if not GITHUB_TOKEN:
        print("❌ Error: GITHUB_TOKEN not found in environment variables.")
        print(
            "Please create a GitHub Personal Access Token with 'repo' scope and add it to your .env file:"
        )
        print("GITHUB_TOKEN=your_token_here")
        return

    try:
        # Initialize GitHub client
        print(f"🔐 Authenticating with GitHub...")
        g = Github(GITHUB_TOKEN)

        # Get repository
        print(f"📦 Accessing repository: {REPO_NAME}")
        repo = g.get_repo(REPO_NAME)

        # Create labels
        create_labels(repo)

        # Create milestones
        milestone_map = create_milestones(repo)

        # Create issues
        create_issues(repo, milestone_map)

        print("\n✨ All done! Issues created successfully.")
        print(f"🔗 View issues at: https://github.com/{REPO_NAME}/issues")

    except GithubException as e:
        print(f"\n❌ GitHub API Error: {e}")
        print("Please check your token permissions and repository access.")
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")


if __name__ == "__main__":
    main()
