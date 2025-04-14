import unittest
import sys
from storage.database import Database
from storage.storage_models import Match, Player


class TestDatabase(unittest.TestCase):
    """Unit tests for verifying database operations with rollback."""

    @classmethod
    def setUpClass(cls):
        """Runs once before all tests to initialize the database connection."""
        print("\n🚀 Setting up database connection for tests...")
        sys.stdout.flush()
        cls.db = Database()
        cls.conn = cls.db.get_connection()
        cls.cur = cls.conn.cursor()
        cls.conn.autocommit = False  # ✅ Disable autocommit to allow rollbacks

    def setUp(self):
        """Runs before each test. Rolls back any leftover changes from previous tests."""
        print("\n🔄 Rolling back previous test data (if any)...")
        sys.stdout.flush()
        self.conn.rollback()  # ✅ Ensures each test starts fresh

    def test_store_match(self):
        """Tests inserting a match and retrieving it."""
        print("\n🟢 Running test_store_match...")
        sys.stdout.flush()

        test_match = Match(
            match_id=999999,
            match_url="https://www.hltv.org/matches/999999/test-match",
            map_stats_links=["https://www.hltv.org/matches/999999/test-map"],
            team1="Test Team A",
            team2="Test Team B",
            score1=16,
            score2=10,
            event="Test Event",
            match_type="BO1",
            forfeit=False,
            date="2025-03-15",
            data_complete=True,
        )

        print("🟡 Inserting test match into database...")
        sys.stdout.flush()
        self.db.store_matches([test_match.to_dict()])

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

        test_player = Player(
            game_id=999999,
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
            kast=0.75,
            kd_diff=12,
            adr=85.0,
            fk_diff=2,
            rating=1.32,
            data_complete=True,
        )

        print(f"🔄 Created Player object: {test_player}")
        sys.stdout.flush()
        print(f"🟡 Player object as dictionary: {test_player.to_dict()}")
        sys.stdout.flush()

        print("🟡 Inserting test player into database...")
        sys.stdout.flush()
        self.db.store_players([test_player])

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

    def tearDown(self):
        """Runs after each test. Rolls back any changes made during the test."""
        print("\n🛠️ Rolling back test transaction...")
        sys.stdout.flush()
        self.conn.rollback()  # ✅ Ensures test data is NOT permanently stored

    @classmethod
    def tearDownClass(cls):
        """Runs once after all tests to clean up."""
        print("\n❌ Closing test database connection...")
        sys.stdout.flush()
        cls.cur.close()
        cls.db.release_connection(cls.conn)


if __name__ == "__main__":
    print("\n🔵 Running database tests...\n")
    sys.stdout.flush()
    unittest.main()
