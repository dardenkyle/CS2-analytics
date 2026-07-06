"""Parsing module for processing demo files and player analytics."""

try:
    from .demo_parser import DemoParser
    from .map_parser import MapParser
    from .match_parser import MatchParser

    __all__ = ["MatchParser", "MapParser", "DemoParser"]
except ImportError as e:
    print(f"❌ Error importing parsing module: {e}")
    DemoParser = None
