from fastapi.testclient import TestClient

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
