from cs2_analytics import stage_services as stage_services_package
from cs2_analytics.stage_services import (
    DemoStageService,
    MapStageService,
    MatchStageService,
    StageItemResult,
)
from cs2_analytics.stage_services.demo_stage_service import (
    DemoStageService as ConcreteDemoStageService,
)
from cs2_analytics.stage_services.map_stage_service import (
    MapStageService as ConcreteMapStageService,
)
from cs2_analytics.stage_services.match_stage_service import (
    MatchStageService as ConcreteMatchStageService,
)
from cs2_analytics.stage_services.stage_result import (
    StageItemResult as ConcreteStageItemResult,
)


def _store_stub(*_args, **_kwargs) -> None:
    return None


def test_stage_services_package_re_exports_concrete_classes() -> None:
    assert stage_services_package.MatchStageService is ConcreteMatchStageService
    assert stage_services_package.MapStageService is ConcreteMapStageService
    assert stage_services_package.DemoStageService is ConcreteDemoStageService
    assert stage_services_package.StageItemResult is ConcreteStageItemResult
    assert stage_services_package.__all__ == [
        "DemoStageService",
        "MapStageService",
        "MatchStageService",
        "StageItemResult",
    ]


def test_stage_item_result_exposes_named_outcomes() -> None:
    processed = StageItemResult.processed()
    failed = StageItemResult.failed("parser returned nothing")
    skipped = StageItemResult.skipped("deferred")

    assert processed.status == "processed"
    assert processed.succeeded is True
    assert failed.status == "failed"
    assert failed.message == "parser returned nothing"
    assert failed.succeeded is False
    assert skipped.status == "skipped"
    assert skipped.message == "deferred"


def test_match_stage_service_records_constructor_dependencies() -> None:
    parser = object()
    match_state = object()
    map_state = object()
    demo_state = object()

    service = MatchStageService(
        parser=parser,
        store_matches=_store_stub,
        match_state=match_state,
        map_state=map_state,
        demo_state=demo_state,
    )

    assert service.parser is parser
    assert service.store_matches is _store_stub
    assert service.match_state is match_state
    assert service.map_state is map_state
    assert service.demo_state is demo_state


def test_map_stage_service_records_constructor_dependencies() -> None:
    parser = object()
    map_state = object()

    service = MapStageService(
        parser=parser,
        store_players=_store_stub,
        map_state=map_state,
    )

    assert service.parser is parser
    assert service.store_players is _store_stub
    assert service.map_state is map_state


def test_demo_stage_service_records_constructor_dependencies() -> None:
    scraper = object()
    parser = object()
    demo_state = object()

    service = DemoStageService(
        scraper=scraper,
        parser=parser,
        store_demo_file=_store_stub,
        demo_state=demo_state,
    )

    assert service.scraper is scraper
    assert service.parser is parser
    assert service.store_demo_file is _store_stub
    assert service.demo_state is demo_state

