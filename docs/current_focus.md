# Current Focus

## Goal

Keep the ingestion pipeline reliable while preserving clear stage boundaries.

## Key Decisions

- Scrapers fetch content only
- Parsers extract structured data only
- Controllers orchestrate queue transitions and persistence handoff
- Queues stay PostgreSQL-backed
- Demo-related work remains deferred until ingestion hardening is stable

## Recently Completed

- Queue-status and responsibility cleanup for the active match/map flow
- Match/player persistence remains centralized in storage modules

## Current Work

- Stabilizing retry/backoff and session-recovery paths
- Deciding failure handling when retries are exhausted
- Improving observability around retry exhaustion and run-level outcomes
- Adding targeted tests for controller retry and recovery behavior

## Rules

- Do not tightly couple match -> map -> demo in one synchronous flow
- Each stage should remain independently runnable
