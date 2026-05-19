from pathlib import Path

SCHEMA_PATH = Path(__file__).parents[2] / "cs2_analytics" / "storage" / "schema.sql"


RELATIONSHIP_READINESS_QUERY = """
SELECT
    p.map_id,
    p.player_id,
    p.player_name,
    m.match_id,
    m.map_order,
    m.map_name,
    mt.team1,
    mt.team2,
    mt.winner
FROM players AS p
JOIN maps AS m
    ON p.map_id = m.map_id
JOIN matches AS mt
    ON m.match_id = mt.match_id;
"""


def _table_definition(schema_sql: str, table_name: str) -> str:
    start_marker = f"CREATE TABLE IF NOT EXISTS {table_name} ("
    start_index = schema_sql.index(start_marker)
    end_index = schema_sql.index("\n);", start_index)
    return schema_sql[start_index:end_index]


def test_schema_defines_normalized_player_map_match_relationships() -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    matches_table = _table_definition(schema_sql, "matches")
    maps_table = _table_definition(schema_sql, "maps")
    players_table = _table_definition(schema_sql, "players")

    assert "match_id INT PRIMARY KEY" in matches_table
    assert "map_id INT PRIMARY KEY" in maps_table
    assert "match_id INT NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE" in (
        maps_table
    )
    assert "map_id INT NOT NULL REFERENCES maps(map_id) ON DELETE CASCADE" in (
        players_table
    )
    assert "PRIMARY KEY (map_id, player_id)" in players_table


def test_maps_table_does_not_own_player_relationships() -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    maps_table = _table_definition(schema_sql, "maps")

    assert "player_id" not in maps_table
    assert "REFERENCES players" not in maps_table


def test_relationship_readiness_query_does_not_parse_trace_link_fields() -> None:
    assert "JOIN maps AS m" in RELATIONSHIP_READINESS_QUERY
    assert "ON p.map_id = m.map_id" in RELATIONSHIP_READINESS_QUERY
    assert "JOIN matches AS mt" in RELATIONSHIP_READINESS_QUERY
    assert "ON m.match_id = mt.match_id" in RELATIONSHIP_READINESS_QUERY
    assert "map_links" not in RELATIONSHIP_READINESS_QUERY
    assert "demo_links" not in RELATIONSHIP_READINESS_QUERY
