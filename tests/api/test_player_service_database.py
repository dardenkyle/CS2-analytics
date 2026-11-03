"""Database-backed test of the top-players read against a real PostgreSQL.

The service's SQL runs against a seeded `analytics.agg_player_ratings` in the
local test database. The table is replaced inside one transaction that is
rolled back afterwards; PostgreSQL DDL is transactional, so a dbt-built table
of the same name is restored untouched.
"""

from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from api.services import player_service
from api.services.player_service import PlayerService

# (player_id, player_name, maps_played, rated_maps, avg_rating). 102 and 103
# both round to 1.23; ordering on the rounded value would put 102 first on
# maps played, so 103 leading proves the unrounded average decides. 111 has
# 60 maps but only 3 rated, so the floor on rated maps excludes it.
SEEDED_PLAYERS = [
    (101, "Single Map Outlier", 1, 1, "2.0"),
    (102, "Rounds Same Lower Raw More Maps", 90, 90, "1.2310"),
    (103, "Rounds Same Higher Raw", 60, 60, "1.2340"),
    (104, "Tied Average Most Maps", 80, 80, "1.2000"),
    (107, "Tied Average And Maps High Id", 55, 55, "1.2000"),
    (105, "Tied Average And Maps Low Id", 55, 55, "1.2000"),
    (106, "Tied Average And Maps Mid Id", 55, 55, "1.2000"),
    (108, "All Ratings Null", 70, 0, None),
    (109, "Just Below Floor", 49, 49, "1.9"),
    (110, "Exactly At Floor", 50, 50, "1.1"),
    (111, "Mostly Unrated", 60, 3, "1.9"),
]


class _TransactionDatabase:
    """Yields cursors on one connection without committing between them."""

    def __init__(self, connection) -> None:
        self.connection = connection

    @contextmanager
    def get_cursor(self) -> Iterator[object]:
        cursor = self.connection.cursor()
        try:
            yield cursor
        finally:
            cursor.close()


@pytest.fixture
def seeded_ratings(test_database, monkeypatch) -> Iterator[None]:
    connection = test_database.get_connection()
    try:
        with connection.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS analytics;")
            cur.execute("DROP TABLE IF EXISTS analytics.agg_player_ratings;")
            cur.execute(
                "CREATE TABLE analytics.agg_player_ratings ("
                "player_id BIGINT, player_name TEXT, maps_played BIGINT,"
                " rated_maps BIGINT, avg_rating NUMERIC);"
            )
            cur.executemany(
                "INSERT INTO analytics.agg_player_ratings VALUES (%s, %s, %s, %s, %s);",
                SEEDED_PLAYERS,
            )
        monkeypatch.setattr(
            player_service,
            "Database",
            lambda: _TransactionDatabase(connection),
        )
        yield
    finally:
        connection.rollback()
        test_database.release_connection(connection)


def test_floor_ordering_and_tie_breaks_against_postgres(seeded_ratings) -> None:
    players = PlayerService().fetch_top_players(min_maps=50, limit=10)

    assert [player.player_id for player in players] == [
        103,
        102,
        104,
        105,
        106,
        107,
        110,
    ]
    assert [player.avg_rating for player in players[:2]] == [1.23, 1.23]


def test_limit_applies_after_ordering(seeded_ratings) -> None:
    players = PlayerService().fetch_top_players(min_maps=1, limit=3)

    assert [player.player_id for player in players] == [101, 111, 109]
