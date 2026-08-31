"""Integration tests for the storage layer against a disposable database.

These tests write real rows through the storage modules, which commit on
their own connections, so no rollback can undo them. They therefore run
only when explicitly opted in (CS2_ALLOW_DB_TESTS) and only against a
local database host, and they delete their fixed-ID rows before and after
each test. CI opts in against its service container; a local run with the
application .env skips.
"""

import os
import sys
import unittest
from datetime import UTC, datetime

import pytest

from cs2_analytics.models.map import Map
from cs2_analytics.models.match import Match
from cs2_analytics.models.player import Player
from cs2_analytics.storage.database import Database
from cs2_analytics.storage.map_storage import store_maps
from cs2_analytics.storage.match_storage import store_matches
from cs2_analytics.storage.player_storage import store_players

OPT_IN_ENV = "CS2_ALLOW_DB_TESTS"
LOCAL_DB_HOSTS = ("localhost", "127.0.0.1", "db")
TEST_MATCH_IDS = (999998, 999999)
TEST_MAP_ID = 999999
TEST_PLAYER_ID = 888888


def db_tests_enabled() -> bool:
    """True only when opted in and DB_HOST is a local database."""
    opted_in = os.getenv(OPT_IN_ENV, "").strip().lower() in {"1", "true", "yes"}
    return opted_in and os.getenv("DB_HOST", "") in LOCAL_DB_HOSTS


pytestmark = pytest.mark.skipif(
    not db_tests_enabled(),
    reason=(
        f"DB-backed storage tests run only with {OPT_IN_ENV} set and DB_HOST "
        f"in {LOCAL_DB_HOSTS}; they write and delete real rows."
    ),
)


def delete_test_rows(cur) -> None:
    """Remove the fixed-ID rows these tests write, children first."""
    cur.execute(
        "DELETE FROM players WHERE map_id = %s OR player_id = %s;",
        (TEST_MAP_ID, TEST_PLAYER_ID),
    )
    cur.execute(
        "DELETE FROM maps WHERE map_id = %s OR match_id = ANY(%s);",
        (TEST_MAP_ID, list(TEST_MATCH_IDS)),
    )
    cur.execute("DELETE FROM matches WHERE match_id = ANY(%s);", (list(TEST_MATCH_IDS),))


class TestDatabase(unittest.TestCase):
    """Integration tests for storage writes against a disposable database."""

    @classmethod
    def setUpClass(cls):
        """Runs once before all tests to initialize the database connection."""
        print("\n🚀 Setting up database connection for tests...")
        sys.stdout.flush()
        cls.db = Database()
        cls.conn = cls.db.get_connection()
        cls.conn.autocommit = True
        cls.cur = cls.conn.cursor()

    @classmethod
    def tearDownClass(cls):
        """Remove test rows and release the connection."""
        delete_test_rows(cls.cur)
        cls.cur.close()
        cls.db.release_connection(cls.conn)

    def setUp(self):
        """Runs before each test. Removes leftover test rows so reruns are repeat-safe."""
        print("\n🔄 Removing previous test data (if any)...")
        sys.stdout.flush()
        delete_test_rows(self.cur)

    def tearDown(self):
        """Remove the rows this test wrote."""
        delete_test_rows(self.cur)

    def test_store_match(self):
        """Tests inserting a match and retrieving it."""
        print("\n🟢 Running test_store_match...")
        sys.stdout.flush()

        now = datetime.now(UTC)

        test_match = Match(
            match_id=999999,
            match_url="https://www.hltv.org/matches/999999/test-match",
            map_links=[(999999, "https://www.hltv.org/matches/999999/test-map")],
            demo_links=[],
            team1="Test Team A",
            team2="Test Team B",
            score1=16,
            score2=10,
            winner="Test Team A",
            event="Test Event",
            match_type="BO1",
            forfeit=False,
            date="2025-03-15",
            inserted_at=now,
            last_scraped_at=now,
            last_updated_at=now,
            data_complete=True,
        )

        print("🟡 Inserting test match into database...")
        sys.stdout.flush()
        store_matches([test_match])

        print("🔍 Fetching match from database...")
        sys.stdout.flush()
        self.cur.execute(
            "SELECT match_id, team1, team2, score1, score2 FROM matches WHERE match_id = 999999;"
        )
        result = self.cur.fetchone()

        print(f"✅ Retrieved match: {result}")
        sys.stdout.flush()

        self.assertIsNotNone(result)
        self.assertEqual(result[0], 999999)
        self.assertEqual(result[1], "Test Team A")
        self.assertEqual(result[2], "Test Team B")
        self.assertEqual(result[3], 16)
        self.assertEqual(result[4], 10)

    def test_store_player(self):
        """Tests inserting a player and retrieving it."""
        print("\n🟢 Running test_store_player...")
        sys.stdout.flush()

        now = datetime.now(UTC)

        test_match = Match(
            match_id=999998,
            match_url="https://www.hltv.org/matches/999998/test-player-match",
            map_links=[(999999, "https://www.hltv.org/matches/999998/test-map")],
            demo_links=[],
            team1="Test Team A",
            team2="Test Team B",
            score1=16,
            score2=10,
            winner="Test Team A",
            event="Test Event",
            match_type="BO1",
            forfeit=False,
            date="2025-03-15",
            inserted_at=now,
            last_scraped_at=now,
            last_updated_at=now,
            data_complete=True,
        )
        test_map = Map(
            map_id=999999,
            match_id=999998,
            map_url="https://www.hltv.org/stats/matches/mapstatsid/999999/test-map",
            map_name="de_dust2",
            map_order=1,
            team1_score=16,
            team2_score=10,
            map_winner="Test Team A",
            date="2025-03-15",
            inserted_at=now,
            last_scraped_at=now,
            last_updated_at=now,
            data_complete=True,
        )
        test_player = Player(
            map_id=999999,
            player_id=888888,
            player_name="Test Player",
            player_url="https://www.hltv.org/player/888888/test-player",
            map_name="de_dust2",
            team_name="Test Team A",
            kills=20,
            headshots=12,
            assists=5,
            flash_assists=3,
            deaths=8,
            traded_deaths=2,
            opening_kills=3,
            opening_deaths=1,
            multi_kills=4,
            clutches_won=1,
            kast=0.75,
            kd_diff=12,
            adr=85.0,
            fk_diff=2,
            round_swing=0.0512,
            rating=1.32,
            inserted_at=now,
            last_scraped_at=now,
            last_updated_at=now,
            data_complete=True,
        )

        print(f"🔄 Created Player object: {test_player}")
        sys.stdout.flush()
        print(f"🟡 Player object as dictionary: {test_player.to_dict()}")
        sys.stdout.flush()

        print("🟡 Inserting parent match, map, and test player into database...")
        sys.stdout.flush()
        store_matches([test_match])
        store_maps([test_map])
        store_players([test_player])

        print("🔍 Fetching player from database...")
        sys.stdout.flush()
        self.cur.execute(
            "SELECT player_id, player_name, team_name, kills, deaths FROM players WHERE player_id = 888888;"
        )
        result = self.cur.fetchone()

        print(f"✅ Retrieved player: {result}")
        sys.stdout.flush()

        self.assertIsNotNone(result, "❌ Player was not found in database!")
        self.assertEqual(result[0], 888888)
        self.assertEqual(result[1], "Test Player")
        self.assertEqual(result[2], "Test Team A")
        self.assertEqual(result[3], 20)
        self.assertEqual(result[4], 8)

if __name__ == "__main__":
    print("\n🔵 Running database tests...\n")
    sys.stdout.flush()
    unittest.main()
