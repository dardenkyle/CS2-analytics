import run_api


def test_run_api_uses_environment_backed_runtime_settings(monkeypatch) -> None:
    run_calls: list[dict[str, object]] = []

    def fake_run(app: str, **kwargs: object) -> None:
        run_calls.append({"app": app, **kwargs})

    monkeypatch.setattr(run_api, "API_HOST", "0.0.0.0")
    monkeypatch.setattr(run_api, "API_PORT", 9000)
    monkeypatch.setattr(run_api, "API_DEBUG", True)
    monkeypatch.setattr(run_api.uvicorn, "run", fake_run)

    run_api.main()

    assert run_calls == [
        {
            "app": "api.main:app",
            "host": "0.0.0.0",
            "port": 9000,
            "reload": True,
        }
    ]
