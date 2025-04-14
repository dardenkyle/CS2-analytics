"""Parsing module for processing demo files and player analytics."""

try:
    from .demo_parser import DemoParser
    from .match_parser import MatchParser
    from .map_parser import MapParser

    __all__ = ["MatchParser", "MapParser", "DemoParser"]
except ImportError as e:
    print(f"❌ Error importing parsing module: {e}")
    DemoParser = None
