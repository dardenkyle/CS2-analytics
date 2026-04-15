# Current Focus

## Goal

Keep the ingestion pipeline reliable while preserving clear stage boundaries.

## Key Decisions

- Scrapers fetch content only
- Parsers extract structured data only
- Controllers orchestrate queue transitions and persistence handoff
- Results-stage retry exhaustion fails the run; match/map item exhaustion marks failed and continues
- Queues stay PostgreSQL-backed
- Demo-related work remains deferred until ingestion hardening is stable

## Recently Completed

- Queue-status and responsibility cleanup for the active match/map flow
- Match/player persistence remains centralized in storage modules
- Shared controller retry/session-recovery behavior centralized in controller-scoped helpers
- Retry-exhaustion policy defined for results vs match/map stages
- Run-level retry/failure visibility added to controller summaries and retry-exhaustion logs

## Current Work

- Adding targeted tests for controller retry and recovery behavior

## Rules

- Do not tightly couple match -> map -> demo in one synchronous flow
- Each stage should remain independently runnable
