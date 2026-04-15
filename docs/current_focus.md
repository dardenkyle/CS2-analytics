# Current Focus

## Goal

Transition from ingestion hardening into dbt while preserving clear stage boundaries.

## Key Decisions

- Scrapers fetch content only
- Parsers extract structured data only
- Controllers orchestrate queue transitions and persistence handoff
- Results-stage retry exhaustion fails the run; match/map item exhaustion marks failed and continues
- Queues stay PostgreSQL-backed
- Demo-related work remains deferred until ingestion hardening is stable
- The next major phase is dbt, after one small parser/scraper readability cleanup

## Recently Completed

- Queue-status and responsibility cleanup for the active match/map flow
- Match/player persistence remains centralized in storage modules
- Shared controller retry/session-recovery behavior centralized in controller-scoped helpers
- Retry-exhaustion policy defined for results vs match/map stages
- Run-level retry/failure visibility added to controller summaries and retry-exhaustion logs
- Targeted controller and retry-helper tests added for retry, recovery, and run summaries
- Field-specific parser extraction errors added for required match/map fields with direct parser coverage

## Current Work

- Do one last parser/scraper class-structure cleanup branch focused on readability only
- Initialize the dbt project once that cleanup lands
- Start with staging models for matches, maps, and players

## Rules

- Do not tightly couple match -> map -> demo in one synchronous flow
- Each stage should remain independently runnable
