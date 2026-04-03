# Copilot Context

This is a backend/data engineering pipeline project.

Key rules:

- Scrapers fetch content only; they do not parse or write domain tables
- Parsers extract structured data only; they do not orchestrate pipelines
- Controllers orchestrate pipeline stages
- Queues are stored in PostgreSQL
- Demo files are temporary

Architecture:
results stage -> match stage -> map stage -> demo stage (deferred)

Do not tightly couple stages together.
Prefer queue-based handoff between stages.
