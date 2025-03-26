"""Parsing module for processing demo files and player analytics."""

try:
    from .demo_parser import DemoParser
    from .player_analytics import PlayerAnalytics
    from .match_parser import MatchParser
    from .map_parser import MapParser

    __all__ = ["MatchParser", "MapParser", "DemoParser", "PlayerAnalytics"]
except ImportError as e:
    print(f"❌ Error importing parsing module: {e}")
    DemoParser = None
    PlayerAnalytics = None
