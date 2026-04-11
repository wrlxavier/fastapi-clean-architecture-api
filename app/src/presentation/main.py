"""Main application entry point for the FastAPI Clean Architecture API."""

import logging
from collections.abc import Awaitable, Callable
from ipaddress import ip_address, ip_network
from time import perf_counter

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.datastructures import MutableHeaders

from infrastructure.config.settings import (
    ObservabilitySettings,
    get_observability_settings,
)
from infrastructure.logging import (
    CORRELATION_ID_HEADER,
    bind_correlation_id,
    configure_logging,
    reset_correlation_id,
    resolve_correlation_id,
)
from presentation.routers import api_router

logger = logging.getLogger(__name__)


def _first_forwarded_value(value: str | None) -> str | None:
    """Return the first value from a comma-separated forwarded header."""
    if value is None:
        return None

    first_value = value.split(",", maxsplit=1)[0].strip()
    return first_value or None


def _is_trusted_proxy(
    client_host: str | None,
    trusted_proxy_hosts: tuple[str, ...],
) -> bool:
    """Return whether the immediate client is an allowed reverse proxy."""
    if client_host is None:
        return False

    if "*" in trusted_proxy_hosts:
        return True

    try:
        client_ip = ip_address(client_host)
    except ValueError:
        client_ip = None

    for trusted_proxy in trusted_proxy_hosts:
        if trusted_proxy == client_host:
            return True

        if client_ip is None:
            continue

        try:
            if client_ip in ip_network(trusted_proxy, strict=False):
                return True
        except ValueError:
            continue

    return False


def _apply_proxy_headers(
    request: Request,
    observability_settings: ObservabilitySettings,
) -> None:
    """Normalize request metadata from trusted proxy headers."""
    if not observability_settings.proxy_headers_enabled:
        return

    client = request.client
    client_host = client.host if client is not None else None
    if not _is_trusted_proxy(
        client_host,
        observability_settings.trusted_proxy_hosts,
    ):
        return

    headers = MutableHeaders(scope=request.scope)

    forwarded_for = _first_forwarded_value(headers.get("x-forwarded-for"))
    if forwarded_for is not None:
        request.scope["client"] = (forwarded_for, client.port if client else 0)

    forwarded_proto = _first_forwarded_value(headers.get("x-forwarded-proto"))
    if forwarded_proto is not None:
        request.scope["scheme"] = forwarded_proto

    forwarded_host = _first_forwarded_value(headers.get("x-forwarded-host"))
    if forwarded_host is not None:
        headers["host"] = forwarded_host


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
    observability_settings = get_observability_settings()
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
        _apply_proxy_headers(request, observability_settings)
        correlation_id = resolve_correlation_id(
            request.headers.get(CORRELATION_ID_HEADER)
        )
        request.state.correlation_id = correlation_id
        request.state.request_id = correlation_id
        request_token = bind_correlation_id(correlation_id)
        start_time = perf_counter()

        try:
            response = await call_next(request)
            response.headers[CORRELATION_ID_HEADER] = correlation_id

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
            reset_correlation_id(request_token)

    app.include_router(api_router)
    return app


app = create_app()
