"""Tests for the coverage badge generator script (issue #128)."""

import json
import sys

import pytest

import scripts.generate_coverage_badge as badge_module
from scripts.generate_coverage_badge import badge_color, build_badge


@pytest.mark.parametrize(
    ("percent", "expected_color"),
    [
        (95.0, "brightgreen"),
        (90.0, "brightgreen"),
        (80.4, "green"),
        (80.0, "green"),
        (79.9, "yellowgreen"),
        (70.0, "yellowgreen"),
        (65.0, "yellow"),
        (55.0, "orange"),
        (49.9, "red"),
        (0.0, "red"),
    ],
)
def test_badge_color_thresholds(percent: float, expected_color: str) -> None:
    assert badge_color(percent) == expected_color


def test_build_badge_uses_shields_endpoint_schema() -> None:
    badge = build_badge(80.36)

    assert badge == {
        "schemaVersion": 1,
        "label": "coverage",
        "message": "80.4%",
        "color": "green",
    }


def test_main_writes_endpoint_json_to_given_path(tmp_path, monkeypatch) -> None:
    output_path = tmp_path / "coverage.json"
    monkeypatch.setattr(badge_module, "measured_total_percent", lambda: 81.25)
    monkeypatch.setattr(sys, "argv", ["generate_coverage_badge.py", str(output_path)])

    badge_module.main()

    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["schemaVersion"] == 1
    assert written["message"] == "81.2%"
    assert written["color"] == "green"
