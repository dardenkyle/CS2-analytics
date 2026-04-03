from typing import Any, cast

from bs4 import BeautifulSoup

from cs2_analytics.parsers.map_parser import MapParser


def test_parse_map_prefers_visible_over_hidden_metric_cells() -> None:
    html = """
    <html>
      <body>
        <div class="match-info-box">
          <div class="small-text">Map</div>
          Mirage
        </div>

        <table class="stats-table totalstats">
          <thead>
            <tr>
              <th>BIG</th>
              <th>Op. K-D</th>
              <th>Op. eK-eD</th>
              <th>MKs</th>
              <th>KAST</th>
              <th>eKAST</th>
              <th>1vsX</th>
              <th>K (hs)</th>
              <th>eK (hs)</th>
              <th>A (f)</th>
              <th>D (t)</th>
              <th>eD (t)</th>
              <th>ADR</th>
              <th>eADR</th>
              <th>KAST</th>
              <th>eKAST</th>
              <th>Swing</th>
              <th>Rating 3.0</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td class="st-player"><a href="/player/1234/test-player">TestPlayer</a></td>
              <td class="st-opkd traditional-data">5 : 2</td>
              <td class="st-opkd eco-adjusted-data hidden">9 : 9</td>
              <td class="st-mks">3</td>
              <td class="st-kast traditional-data">70.0%</td>
              <td class="st-kast eco-adjusted-data hidden">99.9%</td>
              <td class="st-clutches">1</td>
              <td class="st-kills traditional-data">20 (12)</td>
              <td class="st-kills eco-adjusted-data hidden">99 (99)</td>
              <td class="st-assists">6 (2)</td>
              <td class="st-deaths traditional-data">15 (3)</td>
              <td class="st-deaths eco-adjusted-data hidden">1 (0)</td>
              <td class="st-adr traditional-data">95.2</td>
              <td class="st-adr eco-adjusted-data hidden">199.9</td>
              <td class="st-kast traditional-data">70.0%</td>
              <td class="st-kast eco-adjusted-data hidden">99.9%</td>
              <td class="st-roundSwing won">+3.00%</td>
              <td class="st-rating ratingPositive">1.24</td>
            </tr>
          </tbody>
        </table>
      </body>
    </html>
    """

    soup = BeautifulSoup(html, "html.parser")
    parser = cast(Any, MapParser())
    players = parser.parse_map(
        soup,
        map_url="https://www.hltv.org/stats/matches/mapstatsid/999999/test-vs-test",
        map_id="999999",
    )

    assert len(players) == 1
    player = players[0]

    assert player.player_name == "TestPlayer"
    assert player.player_id == 1234
    assert player.map_name == "Mirage"

    # Visible values should win over hidden eco-adjusted duplicates.
    assert player.kills == 20
    assert player.headshots == 12
    assert player.assists == 6
    assert player.flash_assists == 2
    assert player.deaths == 15
    assert player.traded_deaths == 3
    assert player.kast == 0.7
    assert player.adr == 95.2
    assert player.round_swing == 0.03
    assert player.rating == 1.24

    assert player.opening_kills == 5
    assert player.opening_deaths == 2
    assert player.kd_diff == 5
    assert player.fk_diff == 3
