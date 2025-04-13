"""Utility for chunking and queuing data into scrape queues."""

from typing import List, Tuple
from more_itertools import chunked


def chunk_and_queue(
    items: List[Tuple[str, str]],
    queue_obj,
    chunk_size: int = 1000,
    source: str = "scraper",
    priority: int = 0,
) -> None:
    """
    Efficiently insert a large list of items into a queue in chunks.

    Args:
        items (List[Tuple[str, str]]): List of (id, url) tuples to insert.
        queue_obj: Queue instance with a `queue_many()` method.
        chunk_size (int): Max number of rows per insert batch. Defaults to 1000.
        source (str): Source identifier string for logging/tracking. Defaults to "scraper".
        priority (int): Optional priority score for queue processing. Defaults to 0.

    Returns:
        None
    """
    for chunk in chunked(items, chunk_size):
        queue_obj.queue_many(chunk, source=source, priority=priority)
