"""Main application entry point for the FastAPI Clean Architecture API."""

from fastapi import FastAPI

from presentation.routers import api_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        FastAPI: The configured FastAPI application instance.
    """
    app = FastAPI(title="FastAPI Clean Architecture API")
    app.include_router(api_router)
    return app


app = create_app()
