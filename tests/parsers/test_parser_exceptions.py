import pytest
from bs4 import BeautifulSoup

from cs2_analytics.exceptions import MapParseError, MatchParseError
from cs2_analytics.parsers.map_parser import MapParser
from cs2_analytics.parsers.match_parser import MatchParser


def _build_match_soup(html_override: str | None = None) -> BeautifulSoup:
    if html_override is not None:
        return BeautifulSoup(html_override, "html.parser")

    return BeautifulSoup(
        """
        <html>
          <body>
            <div class="teamName">Team One</div>
            <div class="teamName">Team Two</div>
            <div class="team1-gradient">
              <a href="/team/1/team-one">Team One</a>
              <div>16</div>
            </div>
            <div class="team2-gradient">
              <a href="/team/2/team-two">Team Two</a>
              <div>10</div>
            </div>
            <div class="event text-ellipsis">Test Event</div>
            <div class="padding preformatted-text">Best of 3</div>
            <div class="mapname">Inferno</div>
            <div class="date" data-unix="1704067200000"></div>
            <a class="results-stats" href="/stats/matches/mapstatsid/2/test-map"></a>
          </body>
        </html>
        """,
        "html.parser",
    )


def _build_map_soup(html_override: str | None = None) -> BeautifulSoup:
    if html_override is not None:
        return BeautifulSoup(html_override, "html.parser")

    return BeautifulSoup(
        """
        <html>
          <body>
            <div class="match-info-box">
              <div class="small-text">Map</div>
              Inferno
            </div>
            <table class="stats-table totalstats">
              <thead>
                <tr>
                  <th class="st-teamname">BIG</th>
                  <th>Op. K-D</th>
                  <th>MKs</th>
                  <th>KAST</th>
                  <th>1vsX</th>
                  <th>K (hs)</th>
                  <th>A (f)</th>
                  <th>D (t)</th>
                  <th>ADR</th>
                  <th>Swing</th>
                  <th>Rating 3.0</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td class="st-player"><a href="/player/22/test-player">TestPlayer</a></td>
                  <td class="st-opkd">1 : 1</td>
                  <td class="st-mks">1</td>
                  <td class="st-kast">70.0%</td>
                  <td class="st-clutches">0</td>
                  <td class="st-kills">20 (10)</td>
                  <td class="st-assists">2 (0)</td>
                  <td class="st-deaths">10 (1)</td>
                  <td class="st-adr">80.0</td>
                  <td class="st-roundSwing">+1.00%</td>
                  <td class="st-rating">1.01</td>
                </tr>
              </tbody>
            </table>
          </body>
        </html>
        """,
        "html.parser",
    )


def test_match_parser_raises_typed_error_for_missing_team_names() -> None:
    parser = MatchParser()
    soup = BeautifulSoup("<html><body></body></html>", "html.parser")

    with pytest.raises(
        MatchParseError, match="Missing team names on match page."
    ) as exc_info:
        parser.parse_match(soup, "https://www.hltv.org/matches/1/test-match")

    assert isinstance(exc_info.value.__cause__, ValueError)


def test_match_parser_returns_numeric_match_id() -> None:
    parser = MatchParser()
    soup = _build_match_soup()

    match, map_links, demo_links = parser.parse_match(
        soup, "https://www.hltv.org/matches/123456/test-match"
    )

    assert match.match_id == 123456
    assert isinstance(match.match_id, int)
    assert map_links == [
        (2, "https://www.hltv.org/stats/matches/mapstatsid/2/test-map")
    ]
    assert demo_links == []


def test_match_parser_raises_typed_error_for_missing_match_id_in_url() -> None:
    parser = MatchParser()
    soup = _build_match_soup()

    with pytest.raises(
        MatchParseError, match="Failed to extract match id from match URL."
    ):
        parser.parse_match(soup, "https://www.hltv.org/match/test-match")


def test_map_parser_raises_typed_error_for_missing_kills() -> None:
    parser = MapParser()
    soup = BeautifulSoup(
        """
        <html>
          <body>
            <div class="match-info-box">
              <div class="small-text">Map</div>
              Inferno
            </div>
            <table class="stats-table totalstats">
              <thead>
                <tr>
                  <th>Player</th>
                  <th>Op. K-D</th>
                  <th>MKs</th>
                  <th>KAST</th>
                  <th>1vsX</th>
                  <th>K (hs)</th>
                  <th>A (f)</th>
                  <th>D (t)</th>
                  <th>ADR</th>
                  <th>Swing</th>
                  <th>Rating 3.0</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td class="st-player"><a href="/player/22/test-player">TestPlayer</a></td>
                  <td class="st-opkd">1 : 1</td>
                  <td class="st-mks">1</td>
                  <td class="st-kast">70.0%</td>
                  <td class="st-clutches">0</td>
                  <td class="st-kills"></td>
                  <td class="st-assists">2 (0)</td>
                  <td class="st-deaths">10 (1)</td>
                  <td class="st-adr">80.0</td>
                  <td class="st-roundSwing">+1.00%</td>
                  <td class="st-rating">1.01</td>
                </tr>
              </tbody>
            </table>
          </body>
        </html>
        """,
        "html.parser",
    )

    with pytest.raises(MapParseError, match="No player kills logged."):
        parser.parse_map(
            soup,
            map_url="https://www.hltv.org/stats/matches/mapstatsid/2/test-map",
            map_id=2,
        )


def test_match_parser_raises_typed_error_for_missing_team_scores() -> None:
    parser = MatchParser()
    soup = _build_match_soup(
        """
        <html>
          <body>
            <div class="teamName">Team One</div>
            <div class="teamName">Team Two</div>
            <div class="team1-gradient">
              <a href="/team/1/team-one">Team One</a>
              <div>16</div>
            </div>
            <div class="team2-gradient">
              <a href="/team/2/team-two">Team Two</a>
            </div>
            <div class="event text-ellipsis">Test Event</div>
            <div class="padding preformatted-text">Best of 3</div>
            <div class="mapname">Inferno</div>
            <div class="date" data-unix="1704067200000"></div>
          </body>
        </html>
        """
    )

    with pytest.raises(
        MatchParseError, match="Failed to extract team scores from match page."
    ):
        parser.parse_match(soup, "https://www.hltv.org/matches/1/test-match")


def test_match_parser_raises_typed_error_for_missing_match_type() -> None:
    parser = MatchParser()
    soup = _build_match_soup(
        """
        <html>
          <body>
            <div class="teamName">Team One</div>
            <div class="teamName">Team Two</div>
            <div class="team1-gradient">
              <a href="/team/1/team-one">Team One</a>
              <div>16</div>
            </div>
            <div class="team2-gradient">
              <a href="/team/2/team-two">Team Two</a>
              <div>10</div>
            </div>
            <div class="event text-ellipsis">Test Event</div>
            <div class="mapname">Inferno</div>
            <div class="date" data-unix="1704067200000"></div>
          </body>
        </html>
        """
    )

    with pytest.raises(
        MatchParseError, match="Failed to extract match type from match page."
    ):
        parser.parse_match(soup, "https://www.hltv.org/matches/1/test-match")


def test_match_parser_raises_typed_error_for_missing_event_name() -> None:
    parser = MatchParser()
    soup = _build_match_soup(
        """
        <html>
          <body>
            <div class="teamName">Team One</div>
            <div class="teamName">Team Two</div>
            <div class="team1-gradient">
              <a href="/team/1/team-one">Team One</a>
              <div>16</div>
            </div>
            <div class="team2-gradient">
              <a href="/team/2/team-two">Team Two</a>
              <div>10</div>
            </div>
            <div class="padding preformatted-text">Best of 3</div>
            <div class="mapname">Inferno</div>
            <div class="date" data-unix="1704067200000"></div>
          </body>
        </html>
        """
    )

    with pytest.raises(
        MatchParseError, match="Failed to extract event name from match page."
    ):
        parser.parse_match(soup, "https://www.hltv.org/matches/1/test-match")


def test_match_parser_raises_typed_error_for_missing_forfeit_status() -> None:
    parser = MatchParser()
    soup = _build_match_soup(
        """
        <html>
          <body>
            <div class="teamName">Team One</div>
            <div class="teamName">Team Two</div>
            <div class="team1-gradient">
              <a href="/team/1/team-one">Team One</a>
              <div>16</div>
            </div>
            <div class="team2-gradient">
              <a href="/team/2/team-two">Team Two</a>
              <div>10</div>
            </div>
            <div class="event text-ellipsis">Test Event</div>
            <div class="padding preformatted-text">Best of 3</div>
            <div class="date" data-unix="1704067200000"></div>
          </body>
        </html>
        """
    )

    with pytest.raises(
        MatchParseError, match="Failed to extract forfeit status from match page."
    ):
        parser.parse_match(soup, "https://www.hltv.org/matches/1/test-match")


def test_match_parser_raises_typed_error_for_missing_match_date() -> None:
    parser = MatchParser()
    soup = _build_match_soup(
        """
        <html>
          <body>
            <div class="teamName">Team One</div>
            <div class="teamName">Team Two</div>
            <div class="team1-gradient">
              <a href="/team/1/team-one">Team One</a>
              <div>16</div>
            </div>
            <div class="team2-gradient">
              <a href="/team/2/team-two">Team Two</a>
              <div>10</div>
            </div>
            <div class="event text-ellipsis">Test Event</div>
            <div class="padding preformatted-text">Best of 3</div>
            <div class="mapname">Inferno</div>
          </body>
        </html>
        """
    )

    with pytest.raises(
        MatchParseError, match="Failed to extract match date from match page."
    ):
        parser.parse_match(soup, "https://www.hltv.org/matches/1/test-match")


def test_match_parser_raises_typed_error_for_overflow_match_date() -> None:
    parser = MatchParser()
    soup = _build_match_soup(
        """
        <html>
          <body>
            <div class="teamName">Team One</div>
            <div class="teamName">Team Two</div>
            <div class="team1-gradient">
              <a href="/team/1/team-one">Team One</a>
              <div>16</div>
            </div>
            <div class="team2-gradient">
              <a href="/team/2/team-two">Team Two</a>
              <div>10</div>
            </div>
            <div class="event text-ellipsis">Test Event</div>
            <div class="padding preformatted-text">Best of 3</div>
            <div class="mapname">Inferno</div>
            <div class="date" data-unix="999999999999999999999"></div>
          </body>
        </html>
        """
    )

    with pytest.raises(
        MatchParseError, match="Failed to extract match date from match page."
    ):
        parser.parse_match(soup, "https://www.hltv.org/matches/1/test-match")


def test_map_parser_raises_typed_error_for_missing_map_name() -> None:
    parser = MapParser()
    soup = _build_map_soup(
        """
        <html>
          <body>
          </body>
        </html>
        """
    )

    with pytest.raises(
        MapParseError, match="Failed to extract map name from map stats page."
    ):
        parser.parse_map(
            soup,
            map_url="https://www.hltv.org/stats/matches/mapstatsid/2/test-map",
            map_id=2,
        )


def test_map_parser_raises_typed_error_for_missing_player_name() -> None:
    parser = MapParser()
    soup = _build_map_soup(
        """
        <html>
          <body>
            <div class="match-info-box">
              <div class="small-text">Map</div>
              Inferno
            </div>
            <table class="stats-table totalstats">
              <thead>
                <tr>
                  <th class="st-teamname">BIG</th>
                  <th>Op. K-D</th>
                  <th>MKs</th>
                  <th>KAST</th>
                  <th>1vsX</th>
                  <th>K (hs)</th>
                  <th>A (f)</th>
                  <th>D (t)</th>
                  <th>ADR</th>
                  <th>Swing</th>
                  <th>Rating 3.0</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td class="st-player"></td>
                  <td class="st-opkd">1 : 1</td>
                  <td class="st-mks">1</td>
                  <td class="st-kast">70.0%</td>
                  <td class="st-clutches">0</td>
                  <td class="st-kills">20 (10)</td>
                  <td class="st-assists">2 (0)</td>
                  <td class="st-deaths">10 (1)</td>
                  <td class="st-adr">80.0</td>
                  <td class="st-roundSwing">+1.00%</td>
                  <td class="st-rating">1.01</td>
                </tr>
              </tbody>
            </table>
          </body>
        </html>
        """
    )

    with pytest.raises(
        MapParseError, match="Failed to extract player name from map stats page."
    ):
        parser.parse_map(
            soup,
            map_url="https://www.hltv.org/stats/matches/mapstatsid/2/test-map",
            map_id=2,
        )


def test_map_parser_raises_typed_error_for_missing_deaths() -> None:
    parser = MapParser()
    soup = _build_map_soup(
        """
        <html>
          <body>
            <div class="match-info-box">
              <div class="small-text">Map</div>
              Inferno
            </div>
            <table class="stats-table totalstats">
              <thead>
                <tr>
                  <th class="st-teamname">BIG</th>
                  <th>Op. K-D</th>
                  <th>MKs</th>
                  <th>KAST</th>
                  <th>1vsX</th>
                  <th>K (hs)</th>
                  <th>A (f)</th>
                  <th>D (t)</th>
                  <th>ADR</th>
                  <th>Swing</th>
                  <th>Rating 3.0</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td class="st-player"><a href="/player/22/test-player">TestPlayer</a></td>
                  <td class="st-opkd">1 : 1</td>
                  <td class="st-mks">1</td>
                  <td class="st-kast">70.0%</td>
                  <td class="st-clutches">0</td>
                  <td class="st-kills">20 (10)</td>
                  <td class="st-assists">2 (0)</td>
                  <td class="st-deaths"></td>
                  <td class="st-adr">80.0</td>
                  <td class="st-roundSwing">+1.00%</td>
                  <td class="st-rating">1.01</td>
                </tr>
              </tbody>
            </table>
          </body>
        </html>
        """
    )

    with pytest.raises(MapParseError, match="No player deaths logged."):
        parser.parse_map(
            soup,
            map_url="https://www.hltv.org/stats/matches/mapstatsid/2/test-map",
            map_id=2,
        )
