"""Pipeline module for orchestrating the CS2 analytics workflow."""
try:
    from .cs2_pipeline import CS2AnalyticsPipeline
    __all__ = ["CS2AnalyticsPipeline"]
except ImportError as e:
    print(f"❌ Error importing pipeline module: {e}")
    CS2AnalyticsPipeline = None