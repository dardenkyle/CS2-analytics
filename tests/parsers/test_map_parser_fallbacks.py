"""Fixture tests for map parser fallback and secondary-stat branches.

The map stats page is rendered from small building blocks (info box,
stats tables, player rows) so each test varies exactly the markup that
drives the branch under test.
"""

from typing import Any, cast
from unittest import mock

import pytest
from bs4 import BeautifulSoup

from cs2_analytics.exceptions import MapParseError
from cs2_analytics.models.player import Player
from cs2_analytics.parsers import map_parser as map_parser_module
from cs2_analytics.parsers.map_parser import MapParser

MAP_ID = 222
MAP_URL = f"https://www.hltv.org/stats/matches/mapstatsid/{MAP_ID}/team-a-vs-team-b"
UNIX_2024_01_01 = "1704067200000"

DEFAULT_INFO_BOX = """
<div class="match-info-box">
  <div class="date">2025-08-05 14:30</div>
  <div class="small-text">Map</div>
  Inferno
  <a href="/team/1/team-a">Team A</a>
  <div>13</div>
  <a href="/team/2/team-b">Team B</a>
  <div>9</div>
  <div>Breakdown</div>
</div>
"""

DEFAULT_HEADERS = (
    "<th>Op. K-D</th><th>MKs</th><th>KAST</th><th>1vsX</th><th>K (hs)</th>"
    "<th>A (f)</th><th>D (t)</th><th>ADR</th><th>Swing</th><th>Rating 3.0</th>"
)


def _player_row(
    *,
    player_id: int = 1234,
    name: str = "TestPlayer",
    opkd: str = "5 : 2",
    mks: str = "3",
    kast: str = "70.0%",
    clutches: str = "1",
    kills: str = "20 (12)",
    assists: str = "6 (2)",
    deaths: str = "15 (3)",
    adr: str = "95.2",
    swing: str = "+3.00%",
    rating: str = "1.24",
) -> str:
    return f"""
    <tr>
      <td class="st-player"><a href="/player/{player_id}/x">{name}</a></td>
      <td class="st-opkd">{opkd}</td>
      <td class="st-mks">{mks}</td>
      <td class="st-kast">{kast}</td>
      <td class="st-clutches">{clutches}</td>
      <td class="st-kills">{kills}</td>
      <td class="st-assists">{assists}</td>
      <td class="st-deaths">{deaths}</td>
      <td class="st-adr">{adr}</td>
      <td class="st-roundSwing">{swing}</td>
      <td class="st-rating">{rating}</td>
    </tr>
    """


def _stats_table(
    *,
    team: str = "Team A",
    rows: str | None = None,
    headers: str = DEFAULT_HEADERS,
    table_class: str = "stats-table totalstats",
    with_tbody: bool = True,
) -> str:
    body_rows = rows if rows is not None else _player_row()
    tbody = f"<tbody>{body_rows}</tbody>" if with_tbody else ""
    return (
        f'<table class="{table_class}">'
        f'<thead><tr><th class="st-teamname">{team}</th>{headers}</tr></thead>'
        f"{tbody}</table>"
    )


def _two_team_tables() -> str:
    return _stats_table(team="Team A") + _stats_table(
        team="Team B", rows=_player_row(player_id=5678, name="OtherPlayer")
    )


def _map_soup(
    *, info_box: str = DEFAULT_INFO_BOX, tables: str = "", extra: str = ""
) -> BeautifulSoup:
    html = f"<html><body>{info_box}{tables}{extra}</body></html>"
    return BeautifulSoup(html, "html.parser")


def _parse_players(soup: BeautifulSoup) -> list[Player]:
    return MapParser().parse_map(soup, map_url=MAP_URL, map_id=MAP_ID)


def _parse_details(
    soup: BeautifulSoup,
    *,
    map_id: int = MAP_ID,
    match_id: int | None = 1001,
    map_order: int | None = 1,
) -> Any:
    return MapParser().parse_map_details(
        soup,
        map_url=MAP_URL,
        map_id=map_id,
        match_id=match_id,
        map_order=map_order,
    )


def test_parse_map_wraps_unexpected_errors_as_parse_error() -> None:
    with pytest.raises(
        MapParseError, match="Failed to parse map stats page"
    ) as exc_info:
        MapParser().parse_map(None, map_url=MAP_URL, map_id=MAP_ID)

    assert isinstance(exc_info.value.__cause__, AttributeError)


def test_parse_map_details_wraps_unexpected_errors_as_parse_error() -> None:
    with pytest.raises(
        MapParseError, match="Failed to parse map stats page"
    ) as exc_info:
        MapParser().parse_map_details(
            None, map_url=MAP_URL, map_id=MAP_ID, match_id=1001, map_order=1
        )

    assert isinstance(exc_info.value.__cause__, AttributeError)


def test_parse_map_details_requires_parent_match_id() -> None:
    soup = _map_soup(tables=_two_team_tables())

    with pytest.raises(
        MapParseError, match="Missing parent match id for map persistence."
    ):
        _parse_details(soup, match_id=None)


def test_parse_map_raises_when_page_has_no_stats_tables() -> None:
    with pytest.raises(
        MapParseError, match="No player stats tables found on map page."
    ):
        _parse_players(_map_soup())


def test_parse_map_falls_back_to_plain_stats_tables_and_skips_hidden() -> None:
    tables = _stats_table(
        table_class="stats-table hidden",
        rows=_player_row(player_id=1, name="HiddenPlayer"),
    ) + _stats_table(table_class="stats-table")

    players = _parse_players(_map_soup(tables=tables))

    assert [player.player_name for player in players] == ["TestPlayer"]


def test_parse_map_skips_table_without_tbody_and_warns() -> None:
    tables = _stats_table(team="Team B", with_tbody=False) + _stats_table()

    with mock.patch.object(map_parser_module.logger, "warning") as warning_mock:
        players = _parse_players(_map_soup(tables=tables))

    assert [player.player_name for player in players] == ["TestPlayer"]
    warning_mock.assert_called_once_with(
        "Skipping table without tbody in %s", MAP_URL
    )


def test_parse_map_skips_rows_without_cells() -> None:
    tables = _stats_table(rows="<tr></tr>" + _player_row())

    players = _parse_players(_map_soup(tables=tables))

    assert [player.player_name for player in players] == ["TestPlayer"]


def test_map_name_requires_small_text_label() -> None:
    soup = _map_soup(info_box='<div class="match-info-box">Inferno</div>')

    with pytest.raises(
        MapParseError, match="Failed to extract map name from map stats page."
    ):
        _parse_players(soup)


def test_map_name_requires_text_after_label() -> None:
    soup = _map_soup(
        info_box='<div class="match-info-box"><div class="small-text">Map</div></div>'
    )

    with pytest.raises(
        MapParseError, match="Failed to extract map name from map stats page."
    ):
        _parse_players(soup)


def test_map_date_prefers_data_unix_attribute() -> None:
    info_box = DEFAULT_INFO_BOX.replace(
        '<div class="date">2025-08-05 14:30</div>',
        f'<div class="date" data-unix="{UNIX_2024_01_01}"></div>',
    )

    parsed = _parse_details(_map_soup(info_box=info_box, tables=_two_team_tables()))

    assert parsed.map.date == "2024-01-01 00:00:00"


def test_map_date_rejects_unparseable_data_unix() -> None:
    info_box = DEFAULT_INFO_BOX.replace(
        '<div class="date">2025-08-05 14:30</div>',
        '<div class="date" data-unix="not-a-number"></div>',
    )

    with pytest.raises(
        MapParseError, match="Failed to extract map date from map stats page."
    ) as exc_info:
        _parse_details(_map_soup(info_box=info_box, tables=_two_team_tables()))

    assert isinstance(exc_info.value.__cause__, ValueError)


def test_map_date_accepts_date_without_time() -> None:
    info_box = DEFAULT_INFO_BOX.replace("2025-08-05 14:30", "2025-08-05")

    parsed = _parse_details(_map_soup(info_box=info_box, tables=_two_team_tables()))

    assert parsed.map.date == "2025-08-05"


def test_map_date_missing_raises() -> None:
    info_box = DEFAULT_INFO_BOX.replace(
        '<div class="date">2025-08-05 14:30</div>', ""
    )

    with pytest.raises(
        MapParseError, match="Failed to extract map date from map stats page."
    ):
        _parse_details(_map_soup(info_box=info_box, tables=_two_team_tables()))


def test_team_scores_require_info_box() -> None:
    parser = cast(Any, MapParser())

    with pytest.raises(
        MapParseError, match="Failed to extract map scores from map stats page."
    ):
        parser._extract_map_team_scores(_map_soup(info_box=""))


def test_team_scores_require_two_distinct_teams() -> None:
    with pytest.raises(
        MapParseError, match="Failed to extract map teams from map stats page."
    ):
        _parse_details(_map_soup(tables=_stats_table(team="Team A")))


def test_team_scores_require_team_name_in_info_box() -> None:
    info_box = DEFAULT_INFO_BOX.replace("Team B</a>", "Someone Else</a>")

    with pytest.raises(
        MapParseError, match="Failed to extract map scores from map stats page."
    ) as exc_info:
        _parse_details(_map_soup(info_box=info_box, tables=_two_team_tables()))

    assert isinstance(exc_info.value.__cause__, ValueError)


def test_team_scores_stop_scanning_at_breakdown_marker() -> None:
    info_box = """
    <div class="match-info-box">
      <div class="small-text">Map</div>
      Inferno
      <a href="/team/1/team-a">Team A</a>
      <div>Breakdown</div>
      <div>13</div>
      <a href="/team/2/team-b">Team B</a>
      <div>9</div>
    </div>
    """

    with pytest.raises(
        MapParseError, match="Failed to extract map scores from map stats page."
    ):
        _parse_details(_map_soup(info_box=info_box, tables=_two_team_tables()))


def test_map_order_is_inferred_from_map_stats_links() -> None:
    links = (
        '<a href="/stats/matches/mapstatsid/111/map-one">1</a>'
        '<a href="/stats/matches/mapstatsid/222/map-two">2</a>'
        '<a href="/stats/matches/mapstatsid/222/map-two">2 again</a>'
        '<a href="/stats/matches/mapstatsid/">no id</a>'
    )

    parsed = _parse_details(
        _map_soup(tables=_two_team_tables(), extra=links), map_order=None
    )

    assert parsed.map.map_order == 2


def test_map_order_falls_back_to_map_id_in_url() -> None:
    links = (
        '<a href="/stats/matches/mapstatsid/111/map-one">1</a>'
        '<a href="/stats/matches/mapstatsid/222/map-two">2</a>'
    )

    parsed = _parse_details(
        _map_soup(tables=_two_team_tables(), extra=links),
        map_id=0,
        map_order=None,
    )

    assert parsed.map.map_order == 2


def test_map_order_missing_raises() -> None:
    with pytest.raises(
        MapParseError, match="Failed to extract map order from map stats page."
    ):
        _parse_details(_map_soup(tables=_two_team_tables()), map_order=None)


def test_column_map_skips_blank_headers_and_defaults_missing_columns() -> None:
    headers = DEFAULT_HEADERS.replace("<th>Swing</th>", "<th></th>")

    players = _parse_players(_map_soup(tables=_stats_table(headers=headers)))

    assert len(players) == 1
    assert players[0].round_swing == 0.03


def test_sparse_row_falls_back_to_empty_text_for_out_of_range_columns() -> None:
    row = """
    <tr>
      <td class="st-player"><a href="/player/1234/x">TestPlayer</a></td>
      <td>filler</td>
      <td class="st-kills">20 (12)</td>
      <td class="st-assists">6 (2)</td>
      <td class="st-deaths">15 (3)</td>
      <td class="st-kast">70.0%</td>
      <td class="st-adr">95.2</td>
      <td class="st-rating">1.24</td>
    </tr>
    """

    with mock.patch.object(map_parser_module.logger, "warning"):
        players = _parse_players(_map_soup(tables=_stats_table(rows=row)))

    assert len(players) == 1
    assert players[0].round_swing == 0.0


def test_metric_text_uses_hidden_cell_when_no_visible_cell_exists() -> None:
    row = _player_row().replace(
        '<td class="st-opkd">5 : 2</td>',
        '<td class="st-opkd eco-adjusted-data hidden">9 : 4</td>',
    )

    players = _parse_players(_map_soup(tables=_stats_table(rows=row)))

    assert (players[0].opening_kills, players[0].opening_deaths) == (9, 4)


def test_metric_text_prefer_hidden_picks_hidden_then_visible() -> None:
    parser = cast(Any, MapParser())
    both = BeautifulSoup(
        '<tr><td class="st-opkd">5 : 2</td>'
        '<td class="st-opkd eco-adjusted-data hidden">9 : 4</td></tr>',
        "html.parser",
    ).find_all("td")
    visible_only = BeautifulSoup(
        '<tr><td class="st-opkd">5 : 2</td></tr>', "html.parser"
    ).find_all("td")

    assert parser._extract_metric_text(both, 0, ["st-opkd"], prefer_hidden=True) == (
        "9 : 4"
    )
    assert parser._extract_metric_text(
        visible_only, 0, ["st-opkd"], prefer_hidden=True
    ) == "5 : 2"


def test_pair_metric_without_parenthesized_part_defaults_second_value() -> None:
    players = _parse_players(_map_soup(tables=_stats_table(rows=_player_row(kills="20"))))

    assert (players[0].kills, players[0].headshots) == (20, 0)


def test_secondary_stats_default_to_zero_with_warning_when_unparseable() -> None:
    row = _player_row(opkd="-", mks="-")

    with mock.patch.object(map_parser_module.logger, "warning") as warning_mock:
        players = _parse_players(_map_soup(tables=_stats_table(rows=row)))

    player = players[0]
    assert (player.opening_kills, player.opening_deaths) == (0, 0)
    assert player.multi_kills == 0
    warning_mock.assert_any_call(
        "Could not parse %s from %r; defaulting to 0", "opening duels", "-"
    )
    warning_mock.assert_any_call(
        "Could not parse %s from %r; defaulting to 0", "multi-kills", "-"
    )


@pytest.mark.parametrize("placeholder", ["-", "–", "—"])
def test_adr_dash_placeholder_parses_as_missing_and_keeps_the_row(
    placeholder: str,
) -> None:
    rows = _player_row() + _player_row(
        player_id=5678, name="SubbedOut", adr=placeholder, kills="0 (0)", deaths="3 (0)"
    )

    players = _parse_players(_map_soup(tables=_stats_table(rows=rows)))

    assert [player.player_name for player in players] == ["TestPlayer", "SubbedOut"]
    assert players[0].adr == 95.2
    assert players[1].adr is None
    assert (players[1].kills, players[1].deaths, players[1].rating) == (0, 3, 1.24)


def test_adr_non_numeric_text_other_than_the_placeholder_still_raises() -> None:
    row = _player_row(adr="N/A")

    with pytest.raises(MapParseError, match="Failed to parse ADR value: 'N/A'"):
        _parse_players(_map_soup(tables=_stats_table(rows=row)))


def test_adr_missing_cell_still_raises() -> None:
    row = _player_row().replace('<td class="st-adr">95.2</td>', '<td class="st-adr"></td>')

    with pytest.raises(MapParseError, match="Failed to parse ADR value: ''"):
        _parse_players(_map_soup(tables=_stats_table(rows=row)))
