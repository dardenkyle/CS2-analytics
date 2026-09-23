"""FastAPI app behind `cs2a ops`: one page, one snapshot, one refresh.

Separate from the public API in `api/`; it is bound to loopback by the
CLI and never deployed. The page is plain HTML, CSS, and JavaScript with
no build step, rendered from the saved snapshot so opening it costs no
database query; the update button rebuilds and saves a new one.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from cs2_analytics.exceptions import DatabaseConnectionError
from cs2_analytics.storage.ops_snapshot import (
    DEFAULT_SNAPSHOT_PATH,
    build_snapshot,
    load_snapshot,
    save_snapshot,
)

PAGE_PATH = Path(__file__).with_name("page.html")


def create_ops_app(snapshot_path: Path = DEFAULT_SNAPSHOT_PATH) -> FastAPI:
    """Create the ops app reading and writing the given snapshot file."""
    app = FastAPI(title="CS2 Analytics ops", docs_url=None, redoc_url=None)
    page_html = PAGE_PATH.read_text(encoding="utf-8")

    @app.get("/", response_class=HTMLResponse)
    def page() -> str:
        return page_html

    @app.get("/ops/snapshot")
    def snapshot() -> JSONResponse:
        saved = load_snapshot(snapshot_path)
        if saved is None:
            return JSONResponse(
                status_code=404,
                content={"detail": "No snapshot captured yet; use the update button."},
            )
        return JSONResponse(content=saved)

    @app.post("/ops/refresh")
    def refresh() -> JSONResponse:
        try:
            fresh = build_snapshot()
        except DatabaseConnectionError as e:
            return JSONResponse(
                status_code=503, content={"detail": f"Database unavailable: {e}"}
            )
        save_snapshot(fresh, snapshot_path)
        return JSONResponse(content=fresh)

    return app
