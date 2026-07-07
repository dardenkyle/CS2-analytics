from cs2_analytics.exceptions import MatchStorageError
from cs2_analytics.models.match import Match
from cs2_analytics.storage.db_instance import get_db
from cs2_analytics.utils.log_manager import get_logger

logger = get_logger(__name__)

INSERT_MATCHES_QUERY = """
    INSERT INTO matches (
        match_id, match_url, team1, team2, score1, score2, winner,
        event, match_type, forfeit, date,
        map_links, demo_links,
        last_inserted_at, last_scraped_at, last_updated_at, data_complete
    )
    VALUES (
        %(match_id)s, %(match_url)s, %(team1)s, %(team2)s, %(score1)s, %(score2)s, %(winner)s,
        %(event)s, %(match_type)s, %(forfeit)s, %(date)s,
        %(map_links)s, %(demo_links)s,
        %(last_inserted_at)s, %(last_scraped_at)s, %(last_updated_at)s, %(data_complete)s
    )
    ON CONFLICT (match_id) DO UPDATE SET
        match_url = EXCLUDED.match_url,
        team1 = EXCLUDED.team1,
        team2 = EXCLUDED.team2,
        score1 = EXCLUDED.score1,
        score2 = EXCLUDED.score2,
        winner = EXCLUDED.winner,
        event = EXCLUDED.event,
        match_type = EXCLUDED.match_type,
        forfeit = EXCLUDED.forfeit,
        date = EXCLUDED.date,
        map_links = EXCLUDED.map_links,
        demo_links = EXCLUDED.demo_links,
        last_scraped_at = EXCLUDED.last_scraped_at,
        last_updated_at = EXCLUDED.last_updated_at,
        data_complete = EXCLUDED.data_complete;
    """


def store_matches(matches: list[Match], cur=None) -> None:
    """Upsert match rows.

    When cur is provided the statements join the caller's transaction and
    the caller owns commit/rollback (ADR-0013); otherwise the write runs in
    its own transaction, now through the shared get_cursor path instead of
    hand-rolled connection handling.
    """
    if not matches:
        return

    try:
        if cur is not None:
            _execute_store_matches(cur, matches)
        else:
            with get_db().get_cursor() as own_cur:
                _execute_store_matches(own_cur, matches)
    except Exception as e:
        raise MatchStorageError("Failed to store match records.") from e


def _execute_store_matches(cur, matches: list[Match]) -> None:
    for match in matches:
        cur.execute(
            INSERT_MATCHES_QUERY,
            {
                "match_id": match.match_id,
                "match_url": match.match_url,
                "team1": match.team1,
                "team2": match.team2,
                "score1": match.score1,
                "score2": match.score2,
                "winner": match.winner,
                "event": match.event,
                "match_type": match.match_type,
                "forfeit": match.forfeit,
                "date": match.date,
                "map_links": str(match.map_links),
                "demo_links": str(match.demo_links),
                "last_inserted_at": match.last_inserted_at,
                "last_scraped_at": match.last_scraped_at,
                "last_updated_at": match.last_updated_at,
                "data_complete": match.data_complete,
            },
        )
    logger.info("Stored %d match records.", len(matches))
