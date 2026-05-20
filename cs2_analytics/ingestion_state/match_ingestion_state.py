"""Match ingestion state manager."""

from cs2_analytics.exceptions import MatchIngestionStateError
from cs2_analytics.ingestion_state.base_ingestion_state import BaseIngestionState


class MatchIngestionState(BaseIngestionState):
    """Ingestion-state manager for match discovery and processing."""

    def __init__(self) -> None:
        super().__init__(
            table_name="match_ingestion_state",
            id_field="match_id",
            url_field="match_url",
            error_cls=MatchIngestionStateError,
        )
