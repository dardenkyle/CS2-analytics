import ast
import re
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


def _migration_tree() -> ast.Module:
    return ast.parse(_migration_sql())


def _is_op_call(node: ast.Call, name: str) -> bool:
    return (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == name
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "op"
    )


def _string_constant(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _create_table_calls() -> dict[str, ast.Call]:
    table_calls: dict[str, ast.Call] = {}
    for node in ast.walk(_migration_tree()):
        if not isinstance(node, ast.Call) or not _is_op_call(node, "create_table"):
            continue
        table_name = _string_constant(node.args[0])
        if table_name is not None:
            table_calls[table_name] = node
    return table_calls


def _column_calls(table_call: ast.Call) -> dict[str, ast.Call]:
    columns: dict[str, ast.Call] = {}
    for arg in table_call.args[1:]:
        if (
            isinstance(arg, ast.Call)
            and isinstance(arg.func, ast.Attribute)
            and arg.func.attr == "Column"
        ):
            column_name = _string_constant(arg.args[0])
            if column_name is not None:
                columns[column_name] = arg
    return columns


def _has_bool_keyword(call: ast.Call, name: str, expected: bool) -> bool:
    for keyword in call.keywords:
        if keyword.arg == name and isinstance(keyword.value, ast.Constant):
            return keyword.value.value is expected
    return False


def _index_names() -> set[str]:
    names: set[str] = set()
    for node in ast.walk(_migration_tree()):
        if isinstance(node, ast.Call) and _is_op_call(node, "create_index"):
            index_name = _string_constant(node.args[0])
            if index_name is not None:
                names.add(index_name)
        elif isinstance(node, ast.Call) and _is_op_call(node, "execute"):
            sql = _string_constant(node.args[0])
            if sql is not None:
                names.update(re.findall(r"CREATE INDEX ([a-z0-9_]+)", sql))
    return names


def test_alembic_is_project_dependency() -> None:
    pyproject = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))

    dependencies = pyproject["project"]["dependencies"]

    assert any(
        re.match(r"^alembic(\s|$|[<>=!~\[])", dependency.strip().lower())
        for dependency in dependencies
    )


def test_alembic_env_does_not_render_plaintext_password_url() -> None:
    env_sql = ENV_PATH.read_text(encoding="utf-8")

    assert "hide_password=False" not in env_sql
    assert "create_engine(" in env_sql
    assert "render_as_string(hide_password=True)" in env_sql


def test_initial_migration_defines_application_tables_and_indexes() -> None:
    table_calls = _create_table_calls()

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
        assert table_name in table_calls

    index_names = _index_names()

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
        assert index_name in index_names


def test_initial_migration_preserves_ingestion_lifecycle_fields() -> None:
    table_calls = _create_table_calls()
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
        column_names = set(_column_calls(table_calls[table_name]))
        for column_name in required_columns:
            assert column_name in column_names
        assert "inserted_at" not in column_names
        assert "last_inserted_at" not in column_names


def test_initial_migration_preserves_explicit_source_id_primary_keys() -> None:
    table_calls = _create_table_calls()

    for table_name, column_name in (
        ("teams", "team_id"),
        ("player_info", "player_id"),
        ("matches", "match_id"),
        ("maps", "map_id"),
        ("match_ingestion_state", "match_id"),
        ("map_ingestion_state", "map_id"),
    ):
        columns = _column_calls(table_calls[table_name])
        assert _has_bool_keyword(columns[column_name], "primary_key", True)
        assert _has_bool_keyword(columns[column_name], "autoincrement", False)
