# Architecture

## Overview

This project is a backend and data-engineering pipeline for collecting and analyzing CS2 match data.

## Current flow

Results scraping -> match queue -> match scraping/parsing -> map queue -> map scraping/parsing -> storage/API consumption

Demo processing is intentionally staged for later and remains decoupled.

## Principles

- Separation of concerns
- Queue-based handoff between stages
- Restartable and retry-aware processing
- Domain writes owned by storage modules
- Controllers own orchestration logic
