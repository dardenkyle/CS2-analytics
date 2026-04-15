from contextlib import contextmanager

import pytest

from cs2_analytics.exceptions import MatchQueueError
from cs2_analytics.queues import base_scrape_queue as base_queue_module
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
