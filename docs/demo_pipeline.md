# Demo Pipeline

## Status

Not yet implemented.

The demo pipeline is intentionally deferred until:

- match/map ingestion hardening is stable
- queue handling behavior is reliable
- orchestration strategy is chosen
- dbt-era transformation needs are clearer

## Purpose

Process `.dem` files into structured, queryable outputs.

Unlike match/map HTML scraping, demo processing includes:

- binary download and file lifecycle handling
- heavier compute during parse
- event-level extraction

## High-Level Flow

```text
match stage
  -> discover demo_url
  -> enqueue demo job

demo stage (planned)
  -> fetch queued demo job
  -> download demo file (temporary)
  -> parse demo file
  -> persist structured results
  -> delete demo file on success
```
