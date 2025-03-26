"""
This file marks the tests/ directory as a package.
"""

# Ensure `tests` can import from the main project directory
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
