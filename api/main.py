"""
Main entrypoint for the CS2 Analytics FastAPI application.
Includes middleware setup and route registration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from cs2_analytics.api.routes import players


def create_app() -> FastAPI:
    """
    Creates and configures the FastAPI application.
    """
    app = FastAPI(title="CS2 Analytics API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Replace with specific origins in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(players.router, prefix="/api", tags=["Players"])
    return app


app = create_app()
