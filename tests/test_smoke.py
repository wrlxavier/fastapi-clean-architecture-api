from fastapi.testclient import TestClient

from presentation.dependencies import get_database_readiness
from presentation.main import create_app


def test_docs_loads() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/docs")
    assert response.status_code == 200


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
