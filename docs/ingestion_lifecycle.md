# Ingestion Lifecycle Review

Status: Phase 1 decisions implemented in Phase 2

This document captures the lifecycle semantics now implemented in the
`*_ingestion_state` tables. The implementation source of truth remains
`cs2_analytics/storage/schema.sql`.

## Decisions So Far

The current match and map ingestion-state tables are more than temporary
work queues. They are durable records for discovered entities and their
processing lifecycle.

Agreed direction:

- `match_ingestion_state` is the lifecycle table for discovered matches
- `map_ingestion_state` is the lifecycle table for discovered maps
- `demo_ingestion_state` keeps demo discovery aligned with the same lifecycle
  naming, even though the demo pipeline lifecycle is still deferred

Queue behavior is a filtered view of ingestion state: rows that are ready for
work are selected by status.

## Table Names and Keys

Implemented ingestion state table names:

- `match_ingestion_state`
- `map_ingestion_state`
- `demo_ingestion_state`

Each table uses the source entity ID as its primary key:

- `match_ingestion_state.match_id`
- `map_ingestion_state.map_id`
- `demo_ingestion_state.demo_id`

These primary keys preserve duplicate-discovery protection. When the same
entity is discovered again, the ingestion row should be refreshed instead of
duplicated.

The tables use table-specific URL fields for readability:

- `match_url`
- `map_url`
- `demo_url`

## Status Values

The same status model is used across match, map, and demo ingestion state:

- `pending`: discovered and ready to be processed
- `processing`: actively being worked on
- `processed`: fetched, parsed, and persisted successfully
- `failed`: terminal failure under the current retry policy
- `skipped`: intentionally not processed

`pending` replaces queue-oriented language like `queued`.
`processed` replaces parser-specific language like `parsed`, because a
successful stage includes fetch, parse, and persistence.

## Shared Fields

Each ingestion state table includes:

- table-specific ID field: `match_id`, `map_id`, or `demo_id`
- table-specific URL field: `match_url`, `map_url`, or `demo_url`
- `status`
- `first_seen_at`
- `last_seen_at`
- `last_attempted_at`
- `last_processed_at`
- `last_failed_at`
- `failure_count`
- `last_error_message`
- `source`
- `priority`
- `last_updated_at`

Do not include `inserted_at` on these tables. `first_seen_at` is the row's
creation/discovery timestamp, and `last_updated_at` captures later meaningful
row changes.

## Field Meanings

- `match_id` / `map_id` / `demo_id`
  Stable source identifier and primary key.
- `match_url` / `map_url` / `demo_url`
  Source URL used by the relevant stage.
- `status`
  Current ingestion lifecycle state.
- `first_seen_at`
  First time discovery saw the entity.
- `last_seen_at`
  Most recent time discovery saw the entity.
- `last_attempted_at`
  Most recent time processing was attempted.
- `last_processed_at`
  Most recent successful processing completion.
- `last_failed_at`
  Most recent failed processing completion.
- `failure_count`
  Count of failed processing attempts over the row lifetime.
- `last_error_message`
  Most recent failure or skipped reason.
- `source`
  Discovery source, such as `results_scraper` or `match_parser`.
- `priority`
  Ordering hint for pending work.
- `last_updated_at`
  Most recent meaningful update to the ingestion state row.

## Implemented Behavior

- the schema now creates only `match_ingestion_state`, `map_ingestion_state`,
  and `demo_ingestion_state`
- Python managers live under `cs2_analytics/ingestion_state/`.
- controllers mark rows as `processing` when a batch attempt begins
- stage services mark normal per-item outcomes as `processed`, `failed`, or
  `skipped` using the shared lifecycle helpers
- controllers mark terminal exception failures when retry policy is exhausted
- rediscovery refreshes `last_seen_at`, keeps source IDs as primary keys, and
  preserves `first_seen_at`
