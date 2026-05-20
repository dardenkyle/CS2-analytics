"""Utility for chunking ingestion-state refreshes."""

from more_itertools import chunked


def chunk_and_queue(
    items: list[tuple[int | str, str]],
    queue_obj,
    chunk_size: int = 1000,
    source: str = "scraper",
    priority: int = 0,
) -> None:
    """
    Efficiently record a large list of items in an ingestion-state table in chunks.

    Args:
        items: List of (id, url) tuples to record.
        queue_obj: Ingestion-state instance with a `queue_many()` method.
        chunk_size (int): Max number of rows per insert batch. Defaults to 1000.
        source (str): Source identifier string for logging/tracking. Defaults to "scraper".
        priority (int): Optional priority score for processing. Defaults to 0.

    Returns:
        None
    """
    for chunk in chunked(items, chunk_size):
        queue_obj.queue_many(chunk, source=source, priority=priority)
