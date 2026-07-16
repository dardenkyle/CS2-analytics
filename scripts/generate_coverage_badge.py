"""Generate a shields.io endpoint JSON badge from measured coverage.

Reads the .coverage data file produced by `pytest --cov` and writes the
small JSON document that shields.io's endpoint badge consumes. CI runs
this after the test step and publishes the output to the `badges`
branch, which the README coverage badge points at.
"""

import io
import json
import sys
from pathlib import Path

from coverage import Coverage

COLOR_THRESHOLDS = (
    (90.0, "brightgreen"),
    (80.0, "green"),
    (70.0, "yellowgreen"),
    (60.0, "yellow"),
    (50.0, "orange"),
)
DEFAULT_OUTPUT_PATH = "coverage-badge.json"


def badge_color(percent: float) -> str:
    """Map a coverage percentage to a shields.io color name."""
    for floor, color in COLOR_THRESHOLDS:
        if percent >= floor:
            return color
    return "red"


def build_badge(percent: float) -> dict[str, object]:
    """Build the shields.io endpoint schema document for a percentage."""
    return {
        "schemaVersion": 1,
        "label": "coverage",
        "message": f"{percent:.1f}%",
        "color": badge_color(percent),
    }


def measured_total_percent() -> float:
    """Load the .coverage data file and return the total percentage."""
    cov = Coverage()
    cov.load()
    return cov.report(file=io.StringIO())


def main() -> None:
    output_arg = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUTPUT_PATH
    output_path = Path(output_arg)
    percent = measured_total_percent()
    output_path.write_text(
        json.dumps(build_badge(percent)) + "\n", encoding="utf-8"
    )
    print(f"Wrote {output_path} at {percent:.1f}% coverage")


if __name__ == "__main__":
    main()
