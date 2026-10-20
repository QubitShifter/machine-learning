from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_api_documentation():
    response = client.get("/api")
    assert response.status_code == 200


def test_old_docs_disabled():
    assert client.get("/docs").status_code == 404
    assert client.get("/swagger").status_code == 404
