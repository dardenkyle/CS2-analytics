"""Map ingestion state manager."""

from cs2_analytics.exceptions import MapQueueError
from cs2_analytics.ingestion_state.base_ingestion_state import BaseIngestionState


class MapIngestionState(BaseIngestionState):
    """Ingestion-state manager for map discovery and processing."""

    def __init__(self) -> None:
        super().__init__(
            table_name="map_ingestion_state",
            id_field="map_id",
            url_field="map_url",
            error_cls=MapQueueError,
        )
