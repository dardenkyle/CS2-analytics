import psycopg2
import psycopg2.pool
from config.config import DB_NAME, DB_USER, DB_PASS, DB_HOST, DB_PORT
from log_manager.logger_config import setup_logger

logger = setup_logger(__name__)

# ✅ Connection Pooling for Performance
try:
    db_pool = psycopg2.pool.SimpleConnectionPool(
        minconn=1,
        maxconn=10,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT
    )
    logger.info("✅ PostgreSQL connection pool initialized successfully.")
except Exception as e:
    logger.error(f"❌ Failed to initialize database connection pool: {e}")
    db_pool = None

def connect_db():
    """Retrieves a database connection from the pool."""
    if db_pool is None:
        logger.error("❌ Database connection pool is not available.")
        return None
    try:
        conn = db_pool.getconn()
        logger.info("✅ Successfully retrieved a database connection.")
        return conn
    except Exception as e:
        logger.error(f"❌ Database connection error: {e}")
        return None

def release_db_connection(conn):
    """Releases a database connection back to the pool."""
    if db_pool and conn:
        db_pool.putconn(conn)
        logger.info("🔄 Database connection released back to the pool.")

def close_db_pool():
    """Closes all connections in the database pool."""
    if db_pool:
        db_pool.closeall()
        logger.info("❌ Database connection pool closed.")
