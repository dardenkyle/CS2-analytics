"""Database setup commands for schema creation and explicit wipes."""

import argparse
import os

import psycopg2
from psycopg2 import sql

from cs2_analytics.config.config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER
from cs2_analytics.exceptions import DatabaseOperationError
from cs2_analytics.storage.database import Database
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)

TABLES_TO_WIPE = (
    "demo_files",
    "demo_ingestion_state",
    "map_ingestion_state",
    "match_ingestion_state",
    "player_metrics",
    "player_transfers",
    "player_aliases",
    "player_team_history",
    "players",
    "maps",
    "matches",
    "teams",
    "player_info",
    "scrape_runs",
)


def _connection_kwargs(dbname: str) -> dict[str, str]:
    return {
        "dbname": dbname,
        "user": DB_USER,
        "password": DB_PASS,
        "host": DB_HOST,
        "port": DB_PORT,
    }


def create_database_if_missing(maintenance_db: str = "postgres") -> None:
    """Create the configured database when it does not already exist."""
    try:
        with psycopg2.connect(**_connection_kwargs(maintenance_db)) as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s;",
                    (DB_NAME,),
                )
                if cur.fetchone():
                    logger.info("Database %s already exists.", DB_NAME)
                    return

                cur.execute(
                    sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME))
                )
                logger.info("Database %s created.", DB_NAME)
    except Exception as e:
        raise DatabaseOperationError("Failed to create database.") from e


def wipe_database() -> None:
    """Drop application tables from the configured database."""
    drop_sql = "\n".join(
        f"DROP TABLE IF EXISTS {table_name} CASCADE;" for table_name in TABLES_TO_WIPE
    )

    try:
        with psycopg2.connect(**_connection_kwargs(DB_NAME)) as conn:
            with conn.cursor() as cur:
                cur.execute(drop_sql)
        logger.info("Database tables wiped successfully.")
    except Exception as e:
        raise DatabaseOperationError("Failed to wipe database tables.") from e


def confirm_wipe() -> bool:
    """Ask for interactive confirmation before wiping application tables."""
    answer = input(
        f"This will drop CS2 Analytics tables in database '{DB_NAME}'. "
        "Are you sure? [y/n]: "
    )
    return answer.strip().lower() == "y"


def initialize_database(create_db: bool = False) -> None:
    """Create schema tables and indexes in the configured database."""
    if create_db:
        create_database_if_missing()

    try:
        with psycopg2.connect(**_connection_kwargs(DB_NAME)) as conn:
            logger.info("Connected to PostgreSQL database for schema initialization.")
            with conn.cursor() as cur:
                schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")

                with open(schema_path, encoding="utf-8") as schema_file:
                    schema_sql = schema_file.read()
                    cur.execute(schema_sql)

        logger.info("Database tables created or verified.")

        db = Database()
        try:
            db.create_indexes()
        finally:
            db.close_db_pool()

        logger.info("Database schema initialized successfully.")

    except Exception as e:
        raise DatabaseOperationError("Failed to initialize database schema.") from e


def main(argv: list[str] | None = None) -> None:
    """Run database setup commands from the command line."""
    parser = argparse.ArgumentParser(description="Initialize CS2 Analytics storage.")
    command_group = parser.add_mutually_exclusive_group()
    command_group.add_argument(
        "--init",
        action="store_true",
        help="Create or verify schema tables and indexes in the configured database.",
    )
    command_group.add_argument(
        "--create-database",
        action="store_true",
        help="Create the configured database before initializing schema tables.",
    )
    command_group.add_argument(
        "--wipe",
        action="store_true",
        help="Drop application tables from the configured database and exit.",
    )
    args = parser.parse_args(argv)

    if args.wipe:
        if not confirm_wipe():
            logger.info("Database wipe cancelled.")
            return
        wipe_database()
        return

    initialize_database(create_db=args.create_database)


if __name__ == "__main__":
    main()
