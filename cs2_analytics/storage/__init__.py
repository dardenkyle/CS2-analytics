"""
The `storage` package provides database connection helpers and persistence modules.

The shared database instance is loaded lazily to avoid opening a PostgreSQL
connection when importing setup-only modules such as
`cs2_analytics.storage.initialize_db`.
"""

__all__ = [
    "get_db",
]


def __getattr__(name: str):
    if name == "get_db":
        from .db_instance import get_db

        return get_db
    if name == "db":
        from .db_instance import get_db

        return get_db()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
