"""Structured logging configuration and request-scoped correlation context."""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from infrastructure.config.settings import (
    ObservabilitySettings,
    get_observability_settings,
)

CORRELATION_ID_HEADER = "X-Correlation-ID"

_correlation_id_context: ContextVar[str | None] = ContextVar(
    "correlation_id",
    default=None,
)


def generate_correlation_id() -> str:
    """Generate a correlation identifier for per-request tracing."""
    return str(uuid4())


def resolve_correlation_id(correlation_id: str | None) -> str:
    """Reuse the client-provided correlation ID when present."""
    if correlation_id is None:
        return generate_correlation_id()

    normalized_correlation_id = correlation_id.strip()
    if normalized_correlation_id:
        return normalized_correlation_id
    return generate_correlation_id()


def bind_correlation_id(correlation_id: str) -> Token[str | None]:
    """Bind the current correlation identifier to the execution context."""
    return _correlation_id_context.set(correlation_id)


def reset_correlation_id(token: Token[str | None]) -> None:
    """Reset the correlation identifier for the current execution context."""
    _correlation_id_context.reset(token)


def get_correlation_id() -> str | None:
    """Return the correlation identifier bound to the current execution context."""
    return _correlation_id_context.get()


class JsonFormatter(logging.Formatter):
    """Serialize log records to single-line JSON payloads."""

    def __init__(self, *, include_traceback: bool) -> None:
        """Configure whether traceback details should be included."""
        super().__init__()
        self._include_traceback = include_traceback

    def format(self, record: logging.LogRecord) -> str:
        """Render the log record as a JSON string."""
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "message": record.getMessage(),
        }

        correlation_id = get_correlation_id()
        if correlation_id is not None:
            payload["correlation_id"] = correlation_id
            payload["request_id"] = correlation_id

        for attribute in (
            "path",
            "method",
            "status_code",
            "duration_ms",
            "error_code",
        ):
            value = getattr(record, attribute, None)
            if value is not None:
                payload[attribute] = value

        if self._include_traceback and record.exc_info is not None:
            payload["stack_trace"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(settings: ObservabilitySettings | None = None) -> None:
    """Configure application loggers to emit structured logs to stdout."""
    resolved_settings = (
        settings if settings is not None else get_observability_settings()
    )
    log_level = _resolve_log_level(resolved_settings.log_level)
    formatter = JsonFormatter(include_traceback=resolved_settings.is_development)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        runtime_logger = logging.getLogger(logger_name)
        runtime_logger.handlers.clear()
        runtime_logger.setLevel(log_level)
        runtime_logger.propagate = False
        runtime_logger.addHandler(handler)


def _resolve_log_level(log_level: str) -> int:
    """Resolve a textual log level to the stdlib logging constant."""
    resolved_level = logging.getLevelName(log_level.upper())
    if isinstance(resolved_level, int):
        return resolved_level
    return logging.INFO
