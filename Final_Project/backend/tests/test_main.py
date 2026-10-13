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
        "/parse",
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
        "/parse",
        json={
            "file_path": "empty.py",
            "source_code": ""
        }
    )

    assert response.status_code == 200
    assert response.json()["symbols"] == []


def test_parse_javascript_returns_extracted_symbols():

    response = client.post(
        "/parse",
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

def test_parse_detects_language_from_extension():

    response = client.post(
        "/parse",
        json={
            "file_path": "example.ts",
            "source_code": "interface User {\n  id: number;\n}\nclass Admin {}\n"
        }
    )

    assert response.status_code == 200

    body = response.json()

    assert body["language"] == "typescript"
    assert "Admin" in [symbol["name"] for symbol in body["symbols"]]


def test_parse_reports_detected_language_for_python():

    response = client.post(
        "/parse",
        json={
            "file_path": "sample.py",
            "source_code": "def run():\n    pass\n"
        }
    )

    assert response.json()["language"] == "python"


def test_parse_explicit_language_overrides_extension():

    response = client.post(
        "/parse",
        json={
            "file_path": "script.txt",
            "language": "js",
            "source_code": "function start() {}\n"
        }
    )

    assert response.status_code == 200

    body = response.json()

    assert body["language"] == "javascript"
    assert body["symbols"][0]["name"] == "start"


def test_parse_rejects_unknown_extension():

    response = client.post(
        "/parse",
        json={
            "file_path": "notes.txt",
            "source_code": "puts 'hi'\n"
        }
    )

    assert response.status_code == 400


def test_parse_rejects_unknown_language():

    response = client.post(
        "/parse",
        json={
            "file_path": "main.py",
            "language": "cobol",
            "source_code": ""
        }
    )

    assert response.status_code == 400


def test_parse_handles_tags_query_language():

    response = client.post(
        "/parse",
        json={
            "file_path": "main.go",
            "source_code": "package main\n\nfunc main() {}\n"
        }
    )

    assert response.status_code == 200

    body = response.json()

    assert body["language"] == "go"
    assert body["symbols"][0]["name"] == "main"
