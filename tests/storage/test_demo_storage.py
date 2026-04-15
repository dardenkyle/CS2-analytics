from datetime import UTC
from contextlib import contextmanager

from cs2_analytics.storage import demo_storage as demo_storage_module


class _RecordingCursor:
    def __init__(self) -> None:
        self.executed = False
        self.query: str | None = None
        self.values: dict | None = None

    def execute(self, query: str, values: dict) -> None:
        self.executed = True
        self.query = query
        self.values = values


class _CursorOnlyDb:
    def __init__(self) -> None:
        self.cursor = _RecordingCursor()

    @contextmanager
    def get_cursor(self):
        yield self.cursor


def test_store_demo_file_relies_on_get_cursor_for_commit(
    monkeypatch,
) -> None:
    fake_db = _CursorOnlyDb()
    monkeypatch.setattr(demo_storage_module, "db", fake_db)

    demo_storage_module.store_demo_file(
        map_id=123,
        demo_url="https://www.hltv.org/download/demo/123",
        local_path="demos/test.dem",
        parsed=True,
    )

    assert fake_db.cursor.executed is True
    assert fake_db.cursor.values is not None
    assert fake_db.cursor.values["map_id"] == 123
    assert fake_db.cursor.values["demo_url"] == "https://www.hltv.org/download/demo/123"
    assert fake_db.cursor.values["last_inserted_at"].tzinfo is UTC
    assert fake_db.cursor.values["last_processed_at"].tzinfo is UTC
