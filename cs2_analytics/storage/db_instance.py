"""Lazy shared database access for persistence modules."""

from cs2_analytics.storage.database import Database

_db: Database | None = None


def get_db() -> Database:
    """Return the shared database instance, creating it on first use."""
    global _db

    if _db is None:
        _db = Database()

    return _db
