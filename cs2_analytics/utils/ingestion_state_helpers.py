"""Utility for chunking ingestion-state refreshes."""

from more_itertools import chunked


def chunk_and_record(
    items: list[tuple[int | str, str]],
    state_obj,
    chunk_size: int = 1000,
    source: str = "scraper",
    priority: int = 0,
) -> None:
    """
    Efficiently record a large list of items in an ingestion-state table in chunks.

    Args:
        items: List of (id, url) tuples to record.
        state_obj: Ingestion-state manager used to refresh rows.
        chunk_size (int): Max number of rows per insert batch. Defaults to 1000.
        source (str): Source identifier string for logging/tracking. Defaults to "scraper".
        priority (int): Optional priority score for processing. Defaults to 0.

    Returns:
        None
    """
    for chunk in chunked(items, chunk_size):
        state_obj.record_many(chunk, source=source, priority=priority)
