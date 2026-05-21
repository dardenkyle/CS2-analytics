from api import main as api_main


def test_create_app_uses_configured_cors_origins(monkeypatch) -> None:
    origins = ["https://analytics.example.com"]
    monkeypatch.setattr(api_main, "API_CORS_ORIGINS", origins)

    app = api_main.create_app()

    cors_middleware = next(
        middleware
        for middleware in app.user_middleware
        if middleware.cls.__name__ == "CORSMiddleware"
    )
    assert cors_middleware.kwargs["allow_origins"] == origins


def test_create_app_uses_configured_debug_mode(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "API_DEBUG", True)

    app = api_main.create_app()

    assert app.debug is True
