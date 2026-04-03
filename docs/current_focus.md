# Current Focus

## Goal

Keep the ingestion pipeline reliable while preserving clear stage boundaries.

## Key Decisions

- Scrapers fetch content only
- Parsers extract structured data only
- Controllers orchestrate queue transitions and persistence handoff
- Queues stay PostgreSQL-backed
- Demo-related work remains deferred until ingestion hardening is stable

## Current Work

- Closing review feedback on queue status transitions and cleanup behavior
- Stabilizing retry/backoff and session-recovery paths
- Keeping match/player persistence centralized in storage modules

## Rules

- Do not tightly couple match -> map -> demo in one synchronous flow
- Each stage should remain independently runnable
