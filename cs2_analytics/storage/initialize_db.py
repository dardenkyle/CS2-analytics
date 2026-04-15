"""This script initializes the database schema by executing the schema.sql file."""

import os

import psycopg2

from cs2_analytics.config.config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER
from cs2_analytics.exceptions import DatabaseOperationError
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)


def initialize_database():
    """Executes the schema.sql file to create/update the database schema."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT
        )
        cur = conn.cursor()

        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")

        with open(schema_path, encoding="utf-8") as schema_file:
            schema_sql = schema_file.read()
            cur.execute(schema_sql)

        conn.commit()
        cur.close()
        conn.close()
        logger.info("✅ Database initialized successfully.")

    except Exception as e:
        raise DatabaseOperationError("Failed to initialize database schema.") from e


if __name__ == "__main__":
    initialize_database()

