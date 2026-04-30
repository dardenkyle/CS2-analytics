from contextlib import contextmanager

import pytest

from cs2_analytics.exceptions import MatchQueueError
from cs2_analytics.queues import base_scrape_queue as base_queue_module
from cs2_analytics.queues.demo_ingestion_state import DemoIngestionState
from cs2_analytics.queues.demo_scrape_queue import DemoScrapeQueue
from cs2_analytics.queues.map_ingestion_state import MapIngestionState
from cs2_analytics.queues.map_scrape_queue import MapScrapeQueue
from cs2_analytics.queues.match_ingestion_state import MatchIngestionState
from cs2_analytics.queues.match_scrape_queue import MatchScrapeQueue


class _FailingQueueDb:
    @contextmanager
    def get_cursor(self):
        raise RuntimeError("db down")
        yield


def test_match_queue_wraps_db_failures_in_typed_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(base_queue_module, "db", _FailingQueueDb())
    queue = MatchScrapeQueue()

    with pytest.raises(MatchQueueError, match="Failed to queue items in match_scrape_queue."):
        queue.queue_many([("1", "https://www.hltv.org/matches/1/test")])


def test_ingestion_state_classes_keep_existing_queue_behavior() -> None:
    match_state = MatchIngestionState()
    map_state = MapIngestionState()
    demo_state = DemoIngestionState()

    assert isinstance(match_state, MatchScrapeQueue)
    assert match_state.table_name == "match_scrape_queue"
    assert match_state.id_field == "match_id"
    assert match_state.url_field == "match_url"

    assert isinstance(map_state, MapScrapeQueue)
    assert map_state.table_name == "map_scrape_queue"
    assert map_state.id_field == "map_id"
    assert map_state.url_field == "map_url"

    assert isinstance(demo_state, DemoScrapeQueue)
    assert demo_state.table_name == "demo_scrape_queue"
    assert demo_state.id_field == "demo_id"
    assert demo_state.url_field == "demo_url"
