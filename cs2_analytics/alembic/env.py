"""Alembic runtime configuration for CS2 Analytics."""

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import URL

from cs2_analytics.config.config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER

config = context.config

target_metadata = None


def _database_url() -> str:
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
    )
    return url.render_as_string(hide_password=False)


def run_migrations_offline() -> None:
    """Run migrations without opening a DBAPI connection."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a live database connection."""
    config.set_main_option("sqlalchemy.url", _database_url())
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
