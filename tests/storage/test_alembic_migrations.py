from pathlib import Path

import tomllib

MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "cs2_analytics"
    / "alembic"
    / "versions"
    / "20260521_0001_initial_application_schema.py"
)
ENV_PATH = Path(__file__).parents[2] / "cs2_analytics" / "alembic" / "env.py"
PYPROJECT_PATH = Path(__file__).parents[2] / "pyproject.toml"


def _migration_sql() -> str:
    return MIGRATION_PATH.read_text(encoding="utf-8")


def _table_block(migration_sql: str, table_name: str) -> str:
    start_marker = f'op.create_table(\n        "{table_name}",'
    start_index = migration_sql.index(start_marker)
    next_table_index = migration_sql.find("    op.create_table(", start_index + 1)
    index_start = migration_sql.find("    op.create_index(", start_index + 1)
    candidates = [value for value in (next_table_index, index_start) if value != -1]
    end_index = min(candidates) if candidates else len(migration_sql)
    return migration_sql[start_index:end_index]


def test_alembic_is_project_dependency() -> None:
    pyproject = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))

    assert "alembic" in pyproject["project"]["dependencies"]


def test_alembic_env_does_not_render_plaintext_password_url() -> None:
    env_sql = ENV_PATH.read_text(encoding="utf-8")

    assert "hide_password=False" not in env_sql
    assert "create_engine(" in env_sql
    assert "render_as_string(hide_password=True)" in env_sql


def test_initial_migration_defines_application_tables_and_indexes() -> None:
    migration_sql = _migration_sql()

    for table_name in (
        "teams",
        "player_info",
        "matches",
        "maps",
        "players",
        "player_team_history",
        "player_aliases",
        "player_transfers",
        "match_ingestion_state",
        "map_ingestion_state",
        "demo_ingestion_state",
        "demo_files",
        "scrape_runs",
        "player_metrics",
    ):
        assert f'"{table_name}"' in migration_sql

    for index_name in (
        "idx_matches_date",
        "idx_maps_match_id",
        "idx_players_map_id",
        "idx_players_player_id",
        "idx_players_team_name",
        "idx_player_stats",
        "idx_player_info_team_id",
        "idx_player_transfers_player_id",
        "idx_player_team_history_player_id",
        "idx_match_ingestion_state_pending",
        "idx_map_ingestion_state_pending",
        "idx_demo_ingestion_state_pending",
    ):
        assert index_name in migration_sql


def test_initial_migration_preserves_ingestion_lifecycle_fields() -> None:
    migration_sql = _migration_sql()
    required_columns = (
        "status",
        "first_seen_at",
        "last_seen_at",
        "last_attempted_at",
        "last_processed_at",
        "last_failed_at",
        "failure_count",
        "last_error_message",
        "source",
        "priority",
        "last_updated_at",
    )

    for table_name in (
        "match_ingestion_state",
        "map_ingestion_state",
        "demo_ingestion_state",
    ):
        table_sql = _table_block(migration_sql, table_name)
        for column_name in required_columns:
            assert column_name in table_sql
        assert "inserted_at" not in table_sql
        assert "last_inserted_at" not in table_sql


def test_initial_migration_preserves_explicit_source_id_primary_keys() -> None:
    migration_sql = _migration_sql()

    for table_name, column_name in (
        ("teams", "team_id"),
        ("player_info", "player_id"),
        ("matches", "match_id"),
        ("maps", "map_id"),
        ("match_ingestion_state", "match_id"),
        ("map_ingestion_state", "map_id"),
    ):
        table_sql = _table_block(migration_sql, table_name)
        assert f'"{column_name}", sa.Integer(), primary_key=True' in table_sql
        assert "autoincrement=False" in table_sql
