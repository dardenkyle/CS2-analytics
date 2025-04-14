import os
import json
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)

class DemoParser:
    """Parses CS2 demo files and extracts player insights."""

    def __init__(self, demo_dir: str = "demos/"):
        """
        Initializes the demo parser.

        Args:
            demo_dir (str): Directory containing demo files.
        """
        self.demo_dir = demo_dir
        self.parsed_data_dir = "parsed_data/"
        os.makedirs(self.parsed_data_dir, exist_ok=True)

    def parse_demos(self):
        """Parses all demo files in the demo directory."""
        demo_files = [f for f in os.listdir(self.demo_dir) if f.endswith(".dem")]

        if not demo_files:
            logger.warning("⚠️ No demo files found for parsing.")
            return

        logger.info(f"🔄 Parsing {len(demo_files)} demo files...")

        for demo_file in demo_files:
            demo_path = os.path.join(self.demo_dir, demo_file)
            try:
                parsed_data = self._parse_demo_file(demo_path)
                self._save_parsed_data(demo_file, parsed_data)
                logger.info(f"✅ Successfully parsed {demo_file}.")
            except Exception as e:
                logger.error(f"❌ Error parsing {demo_file}: {e}")

    def _parse_demo_file(self, demo_path: str) -> dict:
        """
        Extracts player and match insights from a demo file.

        Args:
            demo_path (str): Path to the demo file.

        Returns:
            dict: Parsed data containing player statistics, match events, and map insights.
        """
        logger.info(f"📂 Extracting data from: {demo_path}")

        # Placeholder for actual parsing logic (e.g., using `demoinfocs`, `csgo-demo-parser`, etc.)
        parsed_data = {
            "demo_file": os.path.basename(demo_path),
            "map": "de_mirage",  # Extracted map name
            "match_id": "123456",  # Extracted match ID
            "players": {
                "s1mple": {
                    "kills": 25,
                    "deaths": 10,
                    "headshots": 15,
                    "grenade_uses": 5,
                    "mvps": 2,
                    "rating": 1.45,
                },
                "ZywOo": {
                    "kills": 22,
                    "deaths": 12,
                    "headshots": 12,
                    "grenade_uses": 6,
                    "mvps": 1,
                    "rating": 1.32,
                },
            },
            "team_stats": {
                "Team A": {"rounds_won": 16, "rounds_lost": 12},
                "Team B": {"rounds_won": 12, "rounds_lost": 16},
            },
        }

        logger.info(f"📊 Extracted match data: {parsed_data['map']} - Match ID: {parsed_data['match_id']}")
        return parsed_data

    def _save_parsed_data(self, demo_file: str, parsed_data: dict):
        """
        Saves parsed demo data as a JSON file for later analysis.

        Args:
            demo_file (str): Name of the original demo file.
            parsed_data (dict): Extracted player statistics and match insights.
        """
        output_file = os.path.join(self.parsed_data_dir, demo_file.replace(".dem", ".json"))
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(parsed_data, f, indent=4)
        logger.info(f"💾 Saved parsed data: {output_file}")

    def download_demos(self, match_list: list):
        """
        Simulates downloading demo files based on match list.

        Args:
            match_list (list): List of matches with demo URLs (simulated).
        """
        if not match_list:
            logger.warning("⚠️ No matches provided for demo download.")
            return

        logger.info("📥 Downloading demo files...")
        for match in match_list:
            demo_file = f"{match['match_id']}.dem"
            demo_path = os.path.join(self.demo_dir, demo_file)

            # Simulate demo download (In reality, use `requests` or `selenium`)
            with open(demo_path, "w") as f:
                f.write("Simulated demo content.")  # Placeholder content

            logger.info(f"✅ Downloaded: {demo_file}")

