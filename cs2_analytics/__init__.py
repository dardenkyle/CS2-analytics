"""
CS2 Analytics Package

This package provides scraping, parsing, storage, and analytics functionality
for Counter-Strike 2 match data collected from HLTV. It is organized into
modular components to support automation, analysis, and API integration.

Submodules:
- config: Environment and settings management
- scrapers: Web scraping using SeleniumBase
- parsers: HTML and demo file parsing into structured formats
- controllers: Pipeline orchestration and queue handling
- queues: Task tracking for scraping stages
- services: Business logic and analytical processing
- storage: Database access layer
- pipeline: Main orchestration logic
- utils: Logging, batching, and other shared utilities
- models: Optional data models (e.g., Pydantic)
"""
