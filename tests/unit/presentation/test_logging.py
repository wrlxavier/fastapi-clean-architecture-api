import json
import logging
from collections.abc import Iterator
from typing import cast

import pytest
from fastapi.testclient import TestClient

from domain import InvalidTaskTransitionError, TaskId
from infrastructure.config.settings import get_observability_settings
from infrastructure.logging import CORRELATION_ID_HEADER
from presentation.dependencies import get_transition_task_use_case
from presentation.main import create_app


class StubInvalidTransitionUseCase:
    def execute(self, command: object) -> object:
        del command
        raise InvalidTaskTransitionError(
            current_status="done",
            target_status="doing",
        )


@pytest.fixture(autouse=True)
def development_observability(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    get_observability_settings.cache_clear()
    yield
    get_observability_settings.cache_clear()


def _load_json_logs(output: str) -> list[dict[str, object]]:
    parsed_logs: list[dict[str, object]] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            parsed_logs.append(cast(dict[str, object], payload))
    return parsed_logs


def test_health_requests_emit_structured_logs(
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200

    logs = _load_json_logs(capsys.readouterr().out)
    request_log = next(
        log
        for log in logs
        if log.get("message") == "Request completed" and log.get("path") == "/health"
    )

    assert isinstance(request_log.get("timestamp"), str)
    assert request_log.get("level") == "INFO"
    assert request_log.get("method") == "GET"
    assert request_log.get("status_code") == 200
    assert isinstance(request_log.get("duration_ms"), int | float)
    assert request_log.get("duration_ms") is not None
    correlation_id = request_log.get("correlation_id")
    assert isinstance(correlation_id, str)
    assert request_log.get("request_id") == correlation_id
    assert response.headers[CORRELATION_ID_HEADER] == correlation_id


def test_correlation_id_header_is_reused_across_request_logs(
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = create_app()
    trace_logger = logging.getLogger("tests.trace")

    @app.get("/trace")
    def trace() -> dict[str, str]:
        trace_logger.info("Internal operation executed")
        return {"status": "ok"}

    client = TestClient(app)
    correlation_id = "my-test-123"

    response = client.get(
        "/trace",
        headers={CORRELATION_ID_HEADER: correlation_id},
    )

    assert response.status_code == 200
    assert response.headers[CORRELATION_ID_HEADER] == correlation_id

    logs = _load_json_logs(capsys.readouterr().out)
    internal_log = next(
        log
        for log in logs
        if log.get("message") == "Internal operation executed"
    )
    request_log = next(
        log
        for log in logs
        if log.get("message") == "Request completed" and log.get("path") == "/trace"
    )

    assert internal_log.get("correlation_id") == correlation_id
    assert internal_log.get("request_id") == correlation_id
    assert request_log.get("correlation_id") == correlation_id
    assert request_log.get("request_id") == correlation_id


def test_handled_errors_emit_specific_error_codes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    task_id = TaskId.new()
    app = create_app()
    app.dependency_overrides[get_transition_task_use_case] = (
        lambda: StubInvalidTransitionUseCase()
    )

    try:
        client = TestClient(app)
        response = client.post(
            f"/v1/tasks/{task_id.value}/transition",
            json={"status": "doing"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409

    logs = _load_json_logs(capsys.readouterr().out)
    request_log = next(
        log
        for log in logs
        if log.get("path") == f"/v1/tasks/{task_id.value}/transition"
        and log.get("status_code") == 409
    )

    assert request_log.get("level") == "WARNING"
    assert request_log.get("message") == "Request completed with client error"
    assert request_log.get("error_code") == "INVALID_TRANSITION"


def test_unhandled_exceptions_emit_stack_traces_in_development(
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = create_app()

    @app.get("/boom")
    def boom() -> dict[str, str]:
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")

    assert response.status_code == 500

    logs = _load_json_logs(capsys.readouterr().out)
    error_log = next(
        log
        for log in logs
        if log.get("message") == "Unhandled exception during request"
        and log.get("path") == "/boom"
    )

    assert error_log.get("level") == "ERROR"
    assert error_log.get("status_code") == 500
    assert error_log.get("error_code") == "INTERNAL_SERVER_ERROR"
    assert isinstance(error_log.get("stack_trace"), str)
    assert "RuntimeError: boom" in cast(str, error_log.get("stack_trace"))
