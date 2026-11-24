import json

from fastapi.testclient import TestClient

from app import main
from app.repositories.github_importer import (
    GitHubRepositoryImporter,
    GitHubRepositoryImportError,
)


def _events(response):
    return [json.loads(line) for line in response.text.splitlines() if line]


def _client_with_fake_database():
    main.app.dependency_overrides[main.get_database] = lambda: object()
    return TestClient(main.app)


def teardown_function():
    main.app.dependency_overrides.clear()


def test_stream_reports_error_event_for_importer_failure(monkeypatch):
    def fail(self, *args, **kwargs):
        kwargs["progress"]("metadata", 0.0, "Contacting GitHub…")
        raise GitHubRepositoryImportError("Repository not found.")

    monkeypatch.setattr(GitHubRepositoryImporter, "import_repository", fail)

    response = _client_with_fake_database().post(
        "/repositories/import/stream",
        json={"repository_url": "https://github.com/a/b"},
    )

    events = _events(response)
    assert events[0]["type"] == "progress"
    assert events[-1] == {
        "type": "error",
        "status": 400,
        "detail": "Repository not found.",
    }


def test_progress_is_scaled_into_phase_ranges(monkeypatch):
    def fake(self, *args, **kwargs):
        kwargs["progress"]("download", 0.5, "half")
        raise GitHubRepositoryImportError("stop")

    monkeypatch.setattr(GitHubRepositoryImporter, "import_repository", fake)

    response = _client_with_fake_database().post(
        "/repositories/import/stream",
        json={"repository_url": "https://github.com/a/b"},
    )

    start, end = main.IMPORT_PHASES["download"]
    assert _events(response)[0]["progress"] == round((start + end) / 2, 4)
