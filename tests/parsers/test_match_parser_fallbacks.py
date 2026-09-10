"""Fixture tests for match parser fallback and error branches.

Each test renders a minimal match page with one field varied so the
branch under test is the only thing that differs from the happy path.
"""

from typing import Any, cast

import pytest
from bs4 import BeautifulSoup

from cs2_analytics.exceptions import MatchParseError
from cs2_analytics.parsers.match_parser import MatchParser

MATCH_URL = "https://www.hltv.org/matches/123456/test-match"


def _match_soup(
    *,
    team1: str = "Team One",
    team2: str = "Team Two",
    match_type: str = "Best of 3",
    map_name: str = "Inferno",
    results_href: str = "/stats/matches/mapstatsid/2/test-map",
    extra: str = "",
) -> BeautifulSoup:
    html = f"""
    <html>
      <body>
        <div class="teamName">{team1}</div>
        <div class="teamName">{team2}</div>
        <div class="team1-gradient">
          <a href="/team/1/team-one">{team1}</a>
          <div>16</div>
        </div>
        <div class="team2-gradient">
          <a href="/team/2/team-two">{team2}</a>
          <div>10</div>
        </div>
        <div class="event text-ellipsis">Test Event</div>
        <div class="padding preformatted-text">{match_type}</div>
        <div class="mapname">{map_name}</div>
        <div class="date" data-unix="1704067200000"></div>
        <a class="results-stats" href="{results_href}"></a>
        {extra}
      </body>
    </html>
    """
    return BeautifulSoup(html, "html.parser")


class _BrokenSoup:
    """Stands in for a soup whose tree walking blows up mid-extraction."""

    def find(self, *args: Any, **kwargs: Any) -> None:
        raise AttributeError("broken markup")

    def find_all(self, *args: Any, **kwargs: Any) -> None:
        raise AttributeError("broken markup")


def test_parse_match_wraps_unexpected_errors_as_parse_error() -> None:
    parser = MatchParser()

    with pytest.raises(
        MatchParseError, match="Failed to parse match page"
    ) as exc_info:
        parser.parse_match(None, MATCH_URL)

    assert isinstance(exc_info.value.__cause__, AttributeError)


def test_parse_match_rejects_blank_team_names() -> None:
    parser = MatchParser()

    with pytest.raises(MatchParseError, match="Missing team names on match page."):
        parser.parse_match(_match_soup(team1="", team2="Team Two"), MATCH_URL)


def test_parse_match_extracts_demo_link_from_stream_box() -> None:
    parser = MatchParser()
    soup = _match_soup(
        extra='<a class="stream-box" data-demo-link="/download/demo/98765"></a>'
    )

    _, _, demo_links = parser.parse_match(soup, MATCH_URL)

    assert demo_links == [("98765", "https://www.hltv.org/download/demo/98765")]


def test_demo_link_extraction_wraps_broken_markup() -> None:
    parser = cast(Any, MatchParser())

    with pytest.raises(
        MatchParseError, match="Invalid demo link markup on match page."
    ) as exc_info:
        parser._extract_demo_links(_BrokenSoup())

    assert isinstance(exc_info.value.__cause__, AttributeError)


def test_map_link_extraction_wraps_broken_markup() -> None:
    parser = cast(Any, MatchParser())

    with pytest.raises(
        MatchParseError, match="Invalid map link markup on match page."
    ) as exc_info:
        parser._extract_map_stats_links(_BrokenSoup())

    assert isinstance(exc_info.value.__cause__, AttributeError)


def test_extract_id_returns_url_when_it_has_no_digits() -> None:
    parser = cast(Any, MatchParser())

    assert parser._extract_id("https://www.hltv.org/download/demo/pending") == (
        "https://www.hltv.org/download/demo/pending"
    )


def test_parse_match_rejects_map_link_without_numeric_id() -> None:
    parser = MatchParser()
    soup = _match_soup(results_href="/stats/matches/mapstatsid/pending/test-map")

    with pytest.raises(
        MatchParseError, match="Failed to extract numeric id from URL."
    ):
        parser.parse_match(soup, MATCH_URL)


def test_parse_match_rejects_blank_match_type() -> None:
    parser = MatchParser()

    with pytest.raises(
        MatchParseError, match="Failed to extract match type from match page."
    ):
        parser.parse_match(_match_soup(match_type=""), MATCH_URL)


@pytest.mark.parametrize(
    ("match_type_text", "expected"),
    [
        ("Best of 5", "bo5"),
        ("Best of 1", "bo1"),
        ("Best of 3", "bo3"),
    ],
)
def test_parse_match_normalizes_best_of_variants(
    match_type_text: str, expected: str
) -> None:
    parser = MatchParser()

    match, _, _ = parser.parse_match(_match_soup(match_type=match_type_text), MATCH_URL)

    assert match.match_type == expected


def test_parse_match_rejects_unknown_best_of_text() -> None:
    parser = MatchParser()

    with pytest.raises(
        MatchParseError, match="Failed to extract match type from match page."
    ):
        parser.parse_match(_match_soup(match_type="Best of 7"), MATCH_URL)


def test_parse_match_rejects_blank_map_name_for_forfeit_status() -> None:
    parser = MatchParser()

    with pytest.raises(
        MatchParseError, match="Failed to extract forfeit status from match page."
    ):
        parser.parse_match(_match_soup(map_name=""), MATCH_URL)
