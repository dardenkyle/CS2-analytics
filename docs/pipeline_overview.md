# Pipeline Overview

This document describes the current ingestion flow and ownership by stage.

## Results Stage

- scrape results pages
- enqueue match URLs into `match_scrape_queue` with initial status `queued`

## Match Stage

- fetch queued match jobs
- scrape match pages
- parse match metadata
- persist match records
- enqueue map and demo follow-up jobs
- mark processed match queue rows as `parsed` (or `failed` on terminal error)

## Map Stage

- fetch queued map jobs
- scrape map pages
- parse map data
- persist player stat rows derived from map pages
- mark processed map queue rows as `parsed` (or `failed` on terminal error)

## Demo Pipeline

Status: deferred.

Planned flow:

- fetch queued demo jobs
- download demo file
- parse demo
- persist structured demo outputs
- delete demo file
