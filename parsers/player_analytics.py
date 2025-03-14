import os
import json
from log_manager.logger_config import setup_logger

logger = setup_logger(__name__)

class PlayerAnalytics:
    """Analyzes player performance based on parsed demo data."""

    def __init__(self, parsed_data_dir: str = "parsed_data/"):
        """
        Initializes the analytics module.

        Args:
            parsed_data_dir (str): Directory containing parsed demo data.
        """
        self.parsed_data_dir = parsed_data_dir
        self.analytics_output_dir = "analytics_results/"
        os.makedirs(self.analytics_output_dir, exist_ok=True)

    def analyze_all_players(self):
        """Processes all parsed demo data and extracts player performance insights."""
        parsed_files = [f for f in os.listdir(self.parsed_data_dir) if f.endswith(".json")]

        if not parsed_files:
            logger.warning("⚠️ No parsed demo data found for analysis.")
            return

        logger.info(f"🔄 Analyzing player performance from {len(parsed_files)} demo files...")

        aggregated_data = {}

        for file in parsed_files:
            file_path = os.path.join(self.parsed_data_dir, file)
            try:
                player_stats = self._analyze_single_game(file_path)
                for player, stats in player_stats.items():
                    if player not in aggregated_data:
                        aggregated_data[player] = []
                    aggregated_data[player].append(stats)

                logger.info(f"✅ Processed player stats from {file}")

            except Exception as e:
                logger.error(f"❌ Error processing {file}: {e}")

        self._save_aggregated_data(aggregated_data)

    def _analyze_single_game(self, file_path: str) -> dict:
        """
        Analyzes player performance from a single demo file.

        Args:
            file_path (str): Path to the parsed JSON file.

        Returns:
            dict: Player performance statistics.
        """
        logger.info(f"📂 Analyzing file: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            demo_data = json.load(f)

        players = demo_data.get("players", {})
        player_analysis = {}

        for player_name, stats in players.items():
            kills = stats.get("kills", 0)
            deaths = stats.get("deaths", 1)  # Prevent division by zero
            assists = stats.get("assists", 0)
            adr = stats.get("adr", 0.0)
            headshots = stats.get("headshots", 0)

            # Calculate K/D ratio, Kill Participation (KP), and Headshot %.
            kd_ratio = round(kills / deaths, 2)
            kp_ratio = round((kills + assists) / max(1, kills + assists + deaths), 2)
            headshot_percentage = round((headshots / max(1, kills)) * 100, 2)

            player_analysis[player_name] = {
                "kills": kills,
                "deaths": deaths,
                "assists": assists,
                "kd_ratio": kd_ratio,
                "adr": adr,
                "kp_ratio": kp_ratio,
                "headshot_percentage": headshot_percentage,
            }

            logger.info(f"📊 {player_name} - K/D: {kd_ratio}, ADR: {adr}, HS%: {headshot_percentage}%")

        return player_analysis

    def _save_aggregated_data(self, aggregated_data: dict):
        """
        Saves aggregated player performance data to a JSON file.

        Args:
            aggregated_data (dict): Aggregated player stats across multiple games.
        """
        output_file = os.path.join(self.analytics_output_dir, "player_analytics.json")

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(aggregated_data, f, indent=4)

        logger.info(f"💾 Saved aggregated player performance data: {output_file}")

