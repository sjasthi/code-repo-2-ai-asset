from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_returns_running_message():

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Code Dependency Graph API is running"
    }


def test_health_returns_healthy_status():

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_parse_python_returns_extracted_symbols():

    response = client.post(
        "/parse/python",
        json={
            "file_path": "sample.py",
            "source_code": "class User:\n    pass\n"
        }
    )

    assert response.status_code == 200

    body = response.json()

    assert body["file"] == "sample.py"
    assert body["symbols"][0]["type"] == "class"
    assert body["symbols"][0]["name"] == "User"


def test_parse_python_handles_empty_source():

    response = client.post(
        "/parse/python",
        json={
            "file_path": "empty.py",
            "source_code": ""
        }
    )

    assert response.status_code == 200
    assert response.json()["symbols"] == []


def test_parse_javascript_returns_extracted_symbols():

    response = client.post(
        "/parse/javascript",
        json={
            "file_path": "example.js",
            "source_code": """
class User {
}
"""
        }
    )

    assert response.status_code == 200

    body = response.json()

    assert body["file"] == "example.js"

    names = [
        symbol["name"]
        for symbol in body["symbols"]
    ]

    assert "User" in names