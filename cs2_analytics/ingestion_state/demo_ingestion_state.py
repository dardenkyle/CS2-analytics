"""Demo ingestion state manager."""

from cs2_analytics.exceptions import DemoIngestionStateError
from cs2_analytics.ingestion_state.base_ingestion_state import BaseIngestionState


class DemoIngestionState(BaseIngestionState):
    """Ingestion-state manager for demo discovery and processing."""

    def __init__(self) -> None:
        super().__init__(
            table_name="demo_ingestion_state",
            id_field="demo_id",
            url_field="demo_url",
            error_cls=DemoIngestionStateError,
        )
