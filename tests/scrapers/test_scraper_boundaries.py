"""Enforces the scraper layering contract: scrapers fetch only.

Scraper modules must not import storage, ingestion-state, or
ingestion-state helper modules. Persistence and lifecycle transitions
belong to stage services.
"""

import ast
from pathlib import Path

import pytest

SCRAPERS_DIR = Path(__file__).resolve().parents[2] / "cs2_analytics" / "scrapers"

FORBIDDEN_IMPORT_PREFIXES = (
    "cs2_analytics.storage",
    "cs2_analytics.ingestion_state",
    "cs2_analytics.utils.ingestion_state_helpers",
)

SCRAPER_MODULES = sorted(SCRAPERS_DIR.glob("*.py"))


def _imported_module_names(source: str) -> list[str]:
    names = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
            names.extend(f"{node.module}.{alias.name}" for alias in node.names)
    return names


@pytest.mark.parametrize("module_path", SCRAPER_MODULES, ids=lambda p: p.name)
def test_scraper_module_has_no_persistence_imports(module_path: Path) -> None:
    imported = _imported_module_names(module_path.read_text())

    violations = [
        name for name in imported if name.startswith(FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == [], (
        f"{module_path.name} imports persistence modules {violations}; "
        "scrapers are fetch-only, and state writes belong to stage services."
    )
