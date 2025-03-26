"""This script initializes the database schema by executing the schema.sql file."""

import os
import psycopg2
from config.config import DB_NAME, DB_USER, DB_PASS, DB_HOST, DB_PORT
from utils.log_manager import get_logger

logger = get_logger(__name__)


def initialize_database():
    """Executes the schema.sql file to create/update the database schema."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT
        )
        cur = conn.cursor()

        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")

        with open(schema_path, "r", encoding="utf-8") as schema_file:
            schema_sql = schema_file.read()
            cur.execute(schema_sql)

        conn.commit()
        cur.close()
        conn.close()
        logger.info("✅ Database initialized successfully.")

    except Exception as e:
        logger.error("Error initializing database: %s", e)


if __name__ == "__main__":
    initialize_database()
