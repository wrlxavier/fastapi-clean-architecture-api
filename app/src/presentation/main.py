"""Main application entry point for the FastAPI Clean Architecture API."""

import logging
from collections.abc import Awaitable, Callable
from time import perf_counter

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse

from infrastructure.logging import (
    bind_request_id,
    configure_logging,
    generate_request_id,
    reset_request_id,
)
from presentation.routers import api_router

logger = logging.getLogger(__name__)


def _default_error_code(status_code: int) -> str:
    """Map HTTP status codes to a stable log error code."""
    error_codes = {
        status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
        status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
        status.HTTP_403_FORBIDDEN: "FORBIDDEN",
        status.HTTP_404_NOT_FOUND: "NOT_FOUND",
        status.HTTP_409_CONFLICT: "CONFLICT",
        422: "REQUEST_VALIDATION_ERROR",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "INTERNAL_SERVER_ERROR",
    }
    return error_codes.get(status_code, f"HTTP_{status_code}")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        FastAPI: The configured FastAPI application instance.
    """
    configure_logging()
    app = FastAPI(title="FastAPI Clean Architecture API")

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        request.state.error_code = "INTERNAL_SERVER_ERROR"
        request.state.error_logged = True
        logger.error(
            "Unhandled exception during request",
            extra={
                "path": request.url.path,
                "method": request.method,
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "error_code": request.state.error_code,
            },
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal Server Error"},
        )

    @app.middleware("http")
    async def log_requests(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = generate_request_id()
        request.state.request_id = request_id
        request_token = bind_request_id(request_id)
        start_time = perf_counter()

        try:
            response = await call_next(request)

            duration_ms = round((perf_counter() - start_time) * 1000, 3)
            log_extra: dict[str, str | int | float] = {
                "path": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            }

            if response.status_code >= status.HTTP_400_BAD_REQUEST:
                error_code = getattr(
                    request.state,
                    "error_code",
                    _default_error_code(response.status_code),
                )
                request.state.error_code = error_code
                log_extra["error_code"] = error_code

            if response.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
                log_method = (
                    logger.info
                    if getattr(request.state, "error_logged", False)
                    else logger.error
                )
                log_message = "Request completed after server error"
            elif response.status_code >= status.HTTP_400_BAD_REQUEST:
                log_method = logger.warning
                log_message = "Request completed with client error"
            else:
                log_method = logger.info
                log_message = "Request completed"

            log_method(log_message, extra=log_extra)
            return response
        finally:
            reset_request_id(request_token)

    app.include_router(api_router)
    return app


app = create_app()
