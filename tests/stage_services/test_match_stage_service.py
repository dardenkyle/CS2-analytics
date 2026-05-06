from cs2_analytics.stage_services import MatchStageService


class _FakeScraper:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def fetch_soup(self, url: str) -> object:
        self.urls.append(url)
        return object()


class _FakeParser:
    def __init__(
        self,
        match: object | None,
        map_links: list[tuple[str, str]] | None = None,
        demo_links: list[tuple[str, str]] | None = None,
    ) -> None:
        self.match = match
        self.map_links = map_links or []
        self.demo_links = demo_links or []
        self.calls: list[str] = []

    def parse_match(
        self, _soup: object, match_url: str
    ) -> tuple[object | None, list[tuple[str, str]], list[tuple[str, str]]]:
        self.calls.append(match_url)
        return self.match, self.map_links, self.demo_links


class _FakeMatchState:
    def __init__(self) -> None:
        self.processing: list[str] = []
        self.processed: list[str] = []
        self.failed: list[tuple[str, str]] = []

    def mark_as_processing(self, item_id: str) -> None:
        self.processing.append(item_id)

    def mark_as_processed(self, item_id: str) -> None:
        self.processed.append(item_id)

    def mark_as_failed(self, item_id: str, reason: str) -> None:
        self.failed.append((item_id, reason))


class _FakeFollowupState:
    def __init__(self) -> None:
        self.queued: list[tuple[str, str, str]] = []

    def queue(self, item_id: str, url: str, source: str = "unknown") -> None:
        self.queued.append((item_id, url, source))


def test_match_stage_service_processes_success_and_queues_followups() -> None:
    stored_matches: list[list[object]] = []
    match = object()
    match_state = _FakeMatchState()
    map_state = _FakeFollowupState()
    demo_state = _FakeFollowupState()
    service = MatchStageService(
        parser=_FakeParser(
            match=match,
            map_links=[("map-1", "https://www.hltv.org/stats/matches/mapstatsid/1/test")],
            demo_links=[("demo-1", "https://www.hltv.org/download/demo/test")],
        ),
        store_matches=lambda matches: stored_matches.append(matches),
        match_state=match_state,
        map_state=map_state,
        demo_state=demo_state,
    )

    processed = service.process_item(
        "match-1", "https://www.hltv.org/matches/1/test", scraper=_FakeScraper()
    )

    assert processed is True
    assert match_state.processing == []
    assert match_state.processed == ["match-1"]
    assert match_state.failed == []
    assert stored_matches == [[match]]
    assert map_state.queued == [
        (
            "map-1",
            "https://www.hltv.org/stats/matches/mapstatsid/1/test",
            "match_parser",
        )
    ]
    assert demo_state.queued == [
        ("demo-1", "https://www.hltv.org/download/demo/test", "match_parser")
    ]


def test_match_stage_service_marks_failed_when_parser_returns_none() -> None:
    stored_matches: list[list[object]] = []
    match_state = _FakeMatchState()
    service = MatchStageService(
        parser=_FakeParser(match=None),
        store_matches=lambda matches: stored_matches.append(matches),
        match_state=match_state,
        map_state=_FakeFollowupState(),
        demo_state=_FakeFollowupState(),
    )

    processed = service.process_item(
        "match-1", "https://www.hltv.org/matches/1/test", scraper=_FakeScraper()
    )

    assert processed is False
    assert match_state.processing == []
    assert match_state.processed == []
    assert match_state.failed == [("match-1", "Parsing returned None")]
    assert stored_matches == []


def test_match_stage_service_processes_with_attempt_scraper() -> None:
    attempt_scraper = _FakeScraper()
    service = MatchStageService(
        parser=_FakeParser(match=object()),
        store_matches=lambda _matches: None,
        match_state=_FakeMatchState(),
        map_state=_FakeFollowupState(),
        demo_state=_FakeFollowupState(),
    )

    service.process_item(
        "match-1", "https://www.hltv.org/matches/1/test", scraper=attempt_scraper
    )

    assert attempt_scraper.urls == ["https://www.hltv.org/matches/1/test"]
