"""
CS2 Analytics Package

This package provides scraping, parsing, storage, and analytics functionality
for Counter-Strike 2 match data collected from a public results source. It is
organized into modular components to support automation, analysis, and API
integration.

Submodules:
- config: Environment and settings management
- scrapers: Web scraping using SeleniumBase
- parsers: HTML parsing into structured formats
- controllers: Pipeline orchestration and ingestion-stage coordination
- ingestion_state: Lifecycle tracking for discovered matches, maps, and demos
- stage_services: Per-item ingestion workflow services
- storage: Database access layer
- pipeline: Main orchestration logic
- utils: Logging, batching, and other shared utilities
- models: Optional data models (e.g., Pydantic)
"""
