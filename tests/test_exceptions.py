from cs2_analytics.exceptions import (
    CS2AnalyticsError,
    DatabaseConnectionError,
    DatabaseError,
    MapParseError,
    MatchParseError,
    ParseError,
    PlayerStorageError,
    QueueError,
    RetryableScrapeError,
    ScrapeError,
    SessionScrapeError,
    StorageError,
)


def test_exception_hierarchy_uses_shared_base_classes() -> None:
    assert issubclass(ParseError, CS2AnalyticsError)
    assert issubclass(ScrapeError, CS2AnalyticsError)
    assert issubclass(StorageError, CS2AnalyticsError)
    assert issubclass(QueueError, CS2AnalyticsError)

    assert issubclass(MatchParseError, ParseError)
    assert issubclass(MapParseError, ParseError)
    assert issubclass(RetryableScrapeError, ScrapeError)
    assert issubclass(SessionScrapeError, RetryableScrapeError)
    assert issubclass(DatabaseError, StorageError)
    assert issubclass(DatabaseConnectionError, DatabaseError)
    assert issubclass(PlayerStorageError, StorageError)
