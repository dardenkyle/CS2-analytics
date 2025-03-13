"""Storage module for handling database connections and data storage."""

# ✅ Avoid circular imports by using lazy imports
try:
    from storage.database import Database
    from storage.models import Match, Player
    __all__ = ["connect_db", "release_db_connection", "close_db_pool", "DataManager"]
except ImportError as e:
    print(f"❌ Error importing storage module: {e}")
    DataManager = None
