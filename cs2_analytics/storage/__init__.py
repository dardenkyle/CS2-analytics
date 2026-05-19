"""
The `storage` package provides database connection helpers and persistence modules.

The shared `db` instance is loaded lazily to avoid opening a PostgreSQL connection
when importing setup-only modules such as `cs2_analytics.storage.initialize_db`.
"""

__all__ = [
    "db",
]


def __getattr__(name: str):
    if name == "db":
        from .db_instance import db

        return db
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
