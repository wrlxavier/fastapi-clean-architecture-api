from collections.abc import Iterator

import pytest
from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.testclient import TestClient

from infrastructure.config.settings import get_observability_settings
from presentation.dependencies import get_database_readiness
from presentation.main import create_app


@pytest.fixture(autouse=True)
def clear_observability_settings_cache() -> Iterator[None]:
    get_observability_settings.cache_clear()
    yield
    get_observability_settings.cache_clear()


def test_docs_loads() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/docs")
    assert response.status_code == 200


def test_docs_loads_with_forwarded_proxy_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PROXY_HEADERS_ENABLED", "true")
    monkeypatch.setenv("FORWARDED_ALLOW_IPS", "*")

    app = create_app()
    client = TestClient(app)

    response = client.get(
        "/docs",
        headers={
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "api.example.com:8443",
            "Host": "api.example.com:8443",
        },
    )

    assert response.status_code == 200


def test_proxy_headers_preserve_external_origin_for_generated_urls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PROXY_HEADERS_ENABLED", "true")
    monkeypatch.setenv("FORWARDED_ALLOW_IPS", "*")

    app = create_app()

    @app.get("/proxy-target", name="proxy_target")
    def proxy_target() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/proxy-redirect")
    def proxy_redirect(request: Request) -> RedirectResponse:
        return RedirectResponse(request.url_for("proxy_target"))

    @app.get("/proxy-metadata")
    def proxy_metadata(request: Request) -> dict[str, str]:
        client_host = request.client.host if request.client is not None else ""
        return {
            "scheme": request.url.scheme,
            "host": request.headers["host"],
            "client_host": client_host,
        }

    client = TestClient(app)
    headers = {
        "X-Forwarded-Proto": "https",
        "X-Forwarded-Host": "api.example.com:8443",
        "X-Forwarded-For": "203.0.113.10",
        "Host": "internal-api",
    }

    redirect_response = client.get(
        "/proxy-redirect",
        headers=headers,
        follow_redirects=False,
    )
    metadata_response = client.get("/proxy-metadata", headers=headers)

    assert redirect_response.status_code == 307
    assert (
        redirect_response.headers["location"]
        == "https://api.example.com:8443/proxy-target"
    )
    assert metadata_response.json() == {
        "scheme": "https",
        "host": "api.example.com:8443",
        "client_host": "203.0.113.10",
    }


def test_openapi_json_is_accessible() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/openapi.json")
    assert response.status_code == 200

    payload = response.json()
    assert "openapi" in payload


def test_health_endpoint_returns_ok() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload == {"status": "ok"}


def test_ready_endpoint_returns_ok_when_database_is_reachable() -> None:
    app = create_app()
    app.dependency_overrides[get_database_readiness] = lambda: True

    try:
        client = TestClient(app)
        response = client.get("/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {"database": "ok"},
    }


def test_ready_endpoint_returns_service_unavailable_when_database_is_down() -> None:
    app = create_app()
    app.dependency_overrides[get_database_readiness] = lambda: False

    try:
        client = TestClient(app)
        response = client.get("/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "checks": {"database": "down"},
    }
