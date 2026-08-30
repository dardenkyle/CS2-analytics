"""Tests for the dbt CI fixture seeder's local-database guard and shape."""

from scripts import seed_dbt_ci_fixture
from scripts.seed_dbt_ci_fixture import (
    fixture_maps,
    fixture_matches,
    fixture_players,
    require_local_database,
)
from datetime import UTC, datetime


def test_require_local_database_accepts_local_hosts(monkeypatch) -> None:
    for host in seed_dbt_ci_fixture.LOCAL_HOSTS:
        monkeypatch.setenv("DB_HOST", host)
        require_local_database(allow_remote=False)


def test_require_local_database_rejects_remote_host(monkeypatch) -> None:
    monkeypatch.setenv("DB_HOST", "some-remote-host.example.com")

    try:
        require_local_database(allow_remote=False)
    except RuntimeError as exc:
        assert "not local" in str(exc)
    else:
        raise AssertionError("Expected a remote DB_HOST to be rejected")

    require_local_database(allow_remote=True)


def test_fixture_satisfies_tested_invariants() -> None:
    now = datetime.now(UTC)
    matches = fixture_matches(now)
    maps = fixture_maps(now)
    players = fixture_players(now)

    team_pairs = {m.match_id: {m.team1, m.team2} for m in matches}
    for match in matches:
        assert match.winner in team_pairs[match.match_id]

    map_ids = {m.map_id for m in maps}
    map_names = {m.map_name for m in maps}
    assert len({(m.match_id, m.map_order) for m in maps}) == len(maps)
    for player in players:
        assert player.map_id in map_ids
        assert player.map_name in map_names
        assert player.rating is not None
    assert len({(p.map_id, p.player_id) for p in players}) == len(players)
