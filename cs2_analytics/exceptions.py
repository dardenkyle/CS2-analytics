"""Shared exception hierarchy for CS2 Analytics."""


class CS2AnalyticsError(Exception):
    """Base exception for application-specific failures."""


class ConfigurationError(CS2AnalyticsError):
    """Raised when runtime configuration is invalid or incomplete."""


class ParseError(CS2AnalyticsError):
    """Base exception for parsing failures."""


class MatchParseError(ParseError):
    """Raised when a match page cannot be parsed."""


class MapParseError(ParseError):
    """Raised when a map stats page cannot be parsed."""


class ScrapeError(CS2AnalyticsError):
    """Base exception for scraping failures."""


class RetryableScrapeError(ScrapeError):
    """Raised for scrape failures that should be retried."""


class SessionScrapeError(RetryableScrapeError):
    """Raised for transient browser/session failures."""


class ResultsScrapeError(ScrapeError):
    """Raised when the results stage cannot scrape match discovery data."""


class MatchScrapeError(ScrapeError):
    """Raised when match HTML cannot be fetched."""


class MapScrapeError(ScrapeError):
    """Raised when map HTML cannot be fetched."""


class StorageError(CS2AnalyticsError):
    """Base exception for persistence failures."""


class DatabaseError(StorageError):
    """Base exception for database connection and operation failures."""


class DatabaseConnectionError(DatabaseError):
    """Raised when a database connection cannot be established or acquired."""


class DatabaseOperationError(DatabaseError):
    """Raised when a database operation fails."""


class MatchStorageError(StorageError):
    """Raised when match records cannot be stored."""


class MapStorageError(StorageError):
    """Raised when map records cannot be stored."""


class PlayerStorageError(StorageError):
    """Raised when player records cannot be stored."""


class IngestionStateError(CS2AnalyticsError):
    """Base exception for ingestion-state operation failures."""


class MatchIngestionStateError(IngestionStateError):
    """Raised when match ingestion-state operations fail."""


class MapIngestionStateError(IngestionStateError):
    """Raised when map ingestion-state operations fail."""


class DemoIngestionStateError(IngestionStateError):
    """Raised when demo ingestion-state operations fail."""


class PipelineError(CS2AnalyticsError):
    """Base exception for pipeline orchestration failures."""


class AnalyticsProcessingError(PipelineError):
    """Raised when analytics processing cannot complete."""
