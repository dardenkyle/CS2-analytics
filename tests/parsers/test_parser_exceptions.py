from bs4 import BeautifulSoup
import pytest

from cs2_analytics.exceptions import MapParseError, MatchParseError
from cs2_analytics.parsers.map_parser import MapParser
from cs2_analytics.parsers.match_parser import MatchParser


def test_match_parser_raises_typed_error_for_missing_team_names() -> None:
    parser = MatchParser()
    soup = BeautifulSoup("<html><body></body></html>", "html.parser")

    with pytest.raises(MatchParseError, match="Missing team names on match page.") as exc_info:
        parser.parse_match(soup, "https://www.hltv.org/matches/1/test-match")

    assert isinstance(exc_info.value.__cause__, ValueError)


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
            map_id="2",
        )
