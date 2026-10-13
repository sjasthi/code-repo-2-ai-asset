import pytest
from fastapi.testclient import TestClient

from app.main import app, get_database
from app.database.graph_queries import FILE_IMPORTS, FILE_IMPORTED_BY


class FakeDatabase:
    """
    Records queries instead of sending them to Neo4j.
    """

    def __init__(self, results=None):
        self.results = results or []
        self.queries = []

    def execute_query(self, query, parameters=None):
        self.queries.append((query, parameters or {}))

        return self.results


@pytest.fixture
def fake_database():
    database = FakeDatabase()

    app.dependency_overrides[get_database] = lambda: database

    yield database

    app.dependency_overrides.clear()


client = TestClient(app)


def test_imports_endpoint_queries_file_imports(fake_database):

    fake_database.results = [{"imported_file": "dependency_helpers.py"}]

    response = client.get(
        "/dependencies/imports",
        params={"file_path": "dependency_app.py"}
    )

    assert response.status_code == 200
    assert response.json() == [{"imported_file": "dependency_helpers.py"}]
    assert fake_database.queries == [
        (FILE_IMPORTS, {"file_path": "dependency_app.py"})
    ]


def test_imported_by_endpoint_queries_file_imported_by(fake_database):

    fake_database.results = [{"importing_file": "dependency_app.py"}]

    response = client.get(
        "/dependencies/imported-by",
        params={"file_path": "dependency_helpers.py"}
    )

    assert response.status_code == 200
    assert response.json() == [{"importing_file": "dependency_app.py"}]
    assert fake_database.queries == [
        (FILE_IMPORTED_BY, {"file_path": "dependency_helpers.py"})
    ]


def test_analyze_endpoint_stores_imports_and_calls(fake_database):

    response = client.post(
        "/dependencies/analyze",
        params={"language": "python"},
        json={
            "file_path": "dependency_app.py",
            "source_code": "import dependency_helpers\n\nrun()\n"
        }
    )

    assert response.status_code == 200

    body = response.json()

    # One stored IMPORTS edge (resolved to a local file) and one CALLS edge.
    assert body["dependencies_found"] == 2
    assert body["relationships_stored"] == 2

    imports = [
        dependency for dependency in body["dependencies"]
        if dependency["type"] == "import"
    ]

    assert imports[0]["resolved_target"] == "dependency_helpers.py"
    assert len(fake_database.queries) == 3
