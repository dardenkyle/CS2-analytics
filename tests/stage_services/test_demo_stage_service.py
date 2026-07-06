from cs2_analytics.stage_services import DemoStageService


class _FakeDemoState:
    def __init__(self) -> None:
        self.processed: list[str] = []
        self.failed: list[tuple[str, str]] = []
        self.skipped: list[tuple[str, str]] = []

    def mark_as_processed(self, item_id: str) -> None:
        self.processed.append(item_id)

    def mark_as_failed(self, item_id: str, reason: str) -> None:
        self.failed.append((item_id, reason))

    def mark_as_skipped(self, item_id: str, reason: str) -> None:
        self.skipped.append((item_id, reason))


def test_demo_stage_service_marks_demo_ingestion_deferred() -> None:
    demo_state = _FakeDemoState()
    service = DemoStageService(
        scraper=object(),
        parser=object(),
        store_demo_file=lambda *_args: None,
        demo_state=demo_state,
    )

    result = service.process_item("demo-1", "https://www.hltv.org/download/demo/1")

    assert result.succeeded is False
    assert result.status == "skipped"
    assert (
        result.message
        == "Demo ingestion is deferred until the demo pipeline is operational"
    )
    assert demo_state.processed == []
    assert demo_state.failed == []
    assert demo_state.skipped == [
        (
            "demo-1",
            "Demo ingestion is deferred until the demo pipeline is operational",
        )
    ]
