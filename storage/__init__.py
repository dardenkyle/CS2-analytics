"""Storage module for handling database connections and data storage."""

# ✅ Avoid circular imports by using lazy imports
try:
    from storage.db_connection import connect_db, release_db_connection, close_db_pool  # ✅ Ensure these exist in `db_connection.py`
    from storage.data_storage import DataManager  # ✅ Ensure this exists in `data_storage.py`
    __all__ = ["connect_db", "release_db_connection", "close_db_pool", "DataManager"]
except ImportError as e:
    print(f"❌ Error importing storage module: {e}")
    DataManager = None
