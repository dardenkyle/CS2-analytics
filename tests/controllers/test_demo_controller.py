import pytest

from cs2_analytics.controllers import demo_controller as demo_module
from cs2_analytics.stage_services import StageItemResult


class _FakeDemoState:
    def __init__(self) -> None:
        self.failed: list[tuple[str, str]] = []
        self.processed: list[str] = []
        self.processing: list[str] = []

    def fetch(self, limit: int = 25) -> list[tuple[str, str]]:
        assert limit == 2
        return [
            ("demo-1", "https://www.hltv.org/download/demo/1"),
            ("demo-2", "https://www.hltv.org/download/demo/2"),
        ]

    def mark_as_failed(self, item_id: str, reason: str) -> None:
        self.failed.append((item_id, reason))

    def mark_as_processed(self, item_id: str) -> None:
        self.processed.append(item_id)

    def mark_as_processing(self, item_id: str) -> None:
        self.processing.append(item_id)


class _PassiveScraper:
    pass


class _PassiveParser:
    pass


class _TrackingStageService:
    def __init__(self, *_args, **_kwargs) -> None:
        self.calls: list[tuple[str, str]] = []

    def process_item(self, demo_id: str, demo_url: str) -> StageItemResult:
        self.calls.append((demo_id, demo_url))
        if demo_id == "demo-1":
            raise RuntimeError("demo parse exploded")
        return StageItemResult.processed()


def test_demo_controller_delegates_per_item_work_and_continues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    exception_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    monkeypatch.setattr(demo_module, "DemoScraper", _PassiveScraper)
    monkeypatch.setattr(demo_module, "DemoParser", _PassiveParser)
    monkeypatch.setattr(demo_module, "DemoIngestionState", _FakeDemoState)
    monkeypatch.setattr(demo_module, "DemoStageService", _TrackingStageService)
    monkeypatch.setattr(demo_module, "store_demo_file", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        demo_module.logger,
        "info",
        lambda *args, **kwargs: info_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        demo_module.logger,
        "exception",
        lambda *args, **kwargs: exception_calls.append((args, kwargs)),
    )

    controller = demo_module.DemoController()
    controller.run(batch_size=2)

    assert controller.stage_service.calls == [
        ("demo-1", "https://www.hltv.org/download/demo/1"),
        ("demo-2", "https://www.hltv.org/download/demo/2"),
    ]
    assert controller.state.processing == ["demo-1", "demo-2"]
    assert controller.state.failed == [("demo-1", "demo parse exploded")]
    assert controller.state.processed == []
    assert len(exception_calls) == 1
    assert any(
        call_args[0]
        == "DemoController summary: selected=%d succeeded=%d failed=%d skipped=%d"
        and call_args[1:] == (2, 1, 1, 0)
        for call_args, _ in info_calls
    )
