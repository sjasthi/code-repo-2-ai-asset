"""
FP8 graph endpoint tests.

The unit tests use a scripted fake database. The tests at the bottom run
against a real Neo4j and are skipped when it is not running; their data
lives under the github.com/__graph_test__/ prefix and is deleted afterwards.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app, get_database
from app.database.neo4j import Neo4jConnection
from app.database.graph_builder import DependencyGraphBuilder
from app.database.graph_view import (
    FILE_CALLS,
    FILE_SYMBOLS,
    IMPORT_EDGES,
    NEIGHBOURHOOD_FILES,
    PROJECT_FILE_COUNT,
    PROJECT_FILES,
    PROJECTS,
    GraphView,
)


class ScriptedDatabase:
    """
    Returns canned rows per query and records what was asked.
    """

    def __init__(self, responses):
        self.responses = responses
        self.queries = []

    def execute_query(self, query, parameters=None):
        self.queries.append((query, parameters or {}))

        for known, rows in self.responses.items():
            if query == known:
                return rows

        return []


FILES = [
    {"path": "app.py", "language": "python"},
    {"path": "lib/helpers.py", "language": "python"},
]


def test_projects_labels_uploads_and_repositories():
    database = ScriptedDatabase({
        PROJECTS: [
            {"project": "github.com/psf/requests/", "files": 40},
            {"project": "uploads", "files": 3},
        ]
    })

    assert GraphView(database).projects() == [
        {"id": "github.com/psf/requests/", "label": "github.com/psf/requests", "files": 40},
        {"id": "uploads", "label": "Uploaded files", "files": 3},
    ]


def test_graph_returns_file_nodes_and_import_edges():
    database = ScriptedDatabase({
        PROJECT_FILES: FILES,
        IMPORT_EDGES: [{"source": "app.py", "target": "lib/helpers.py", "line": 1}],
    })

    graph = GraphView(database).graph(project="uploads")

    assert graph["nodes"] == [
        {"id": "file:app.py", "type": "file", "label": "app.py",
         "path": "app.py", "language": "python"},
        {"id": "file:lib/helpers.py", "type": "file", "label": "helpers.py",
         "path": "lib/helpers.py", "language": "python"},
    ]
    assert graph["edges"] == [{
        "id": "imports:app.py->lib/helpers.py",
        "source": "file:app.py",
        "target": "file:lib/helpers.py",
        "type": "imports",
        "line": 1,
    }]
    assert graph["truncated"] is False
    assert graph["total_files"] == 2

    # Symbols and calls are opt-in.
    asked = [query for query, _ in database.queries]
    assert FILE_SYMBOLS not in asked and FILE_CALLS not in asked


def test_graph_adds_symbols_and_calls_when_asked():
    database = ScriptedDatabase({
        PROJECT_FILES: FILES,
        FILE_SYMBOLS: [
            {"id": "4:x:1", "label": "Function", "name": "helper",
             "line": 3, "file_path": "lib/helpers.py"},
        ],
        FILE_CALLS: [
            # Resolved to the stored function above: reuse its node.
            {"source": "app.py", "id": "4:x:1", "name": "helper",
             "file_path": "lib/helpers.py", "line": 3, "calls": 2},
            # Unresolved: becomes an "external" node.
            {"source": "app.py", "id": "4:x:2", "name": "print",
             "file_path": None, "line": None, "calls": 1},
        ],
    })

    graph = GraphView(database).graph(include_symbols=True, include_calls=True)
    nodes = {node["id"]: node for node in graph["nodes"]}

    assert nodes["4:x:1"]["type"] == "function"
    assert nodes["4:x:2"]["type"] == "external"
    assert len(nodes) == 4
    assert {(edge["type"], edge["source"], edge["target"]) for edge in graph["edges"]} == {
        ("contains", "file:lib/helpers.py", "4:x:1"),
        ("calls", "file:app.py", "4:x:1"),
        ("calls", "file:app.py", "4:x:2"),
    }


def test_graph_reports_truncation_with_total():
    database = ScriptedDatabase({
        PROJECT_FILES: FILES + [{"path": "z.py", "language": "python"}],
        PROJECT_FILE_COUNT: [{"total": 1200}],
    })

    graph = GraphView(database).graph(limit=2)

    assert graph["files"] == 2
    assert graph["truncated"] is True
    assert graph["total_files"] == 1200
    # It asked for one more row than the limit to detect the cut-off.
    assert database.queries[0][1]["limit"] == 3


def test_graph_centred_on_file_uses_neighbourhood_query():
    query = NEIGHBOURHOOD_FILES.format(depth=2)
    database = ScriptedDatabase({query: FILES})

    graph = GraphView(database).graph(project="ignored", file="app.py", depth=2)

    assert database.queries[0] == (query, {"file": "app.py", "limit": 501})
    assert graph["files"] == 2


# ---------- Endpoints ----------


@pytest.fixture
def scripted():
    database = ScriptedDatabase({PROJECT_FILES: FILES})
    app.dependency_overrides[get_database] = lambda: database
    yield database
    app.dependency_overrides.clear()


client = TestClient(app)


def test_graph_endpoint_passes_options(scripted):
    response = client.get("/graph", params={
        "project": "uploads", "include_symbols": True, "limit": 50,
    })

    assert response.status_code == 200
    assert response.json()["files"] == 2
    query, parameters = scripted.queries[0]
    assert query == PROJECT_FILES
    assert parameters["project"] == "uploads"
    assert parameters["limit"] == 51
    assert FILE_SYMBOLS in [q for q, _ in scripted.queries]


@pytest.mark.parametrize("params", [{"depth": 4}, {"limit": 0}, {"limit": 5001}])
def test_graph_endpoint_validates_bounds(scripted, params):
    assert client.get("/graph", params=params).status_code == 422


# ---------- Real Neo4j ----------


PREFIX = "github.com/__graph_test__/repo/"


def cleanup(database):
    database.execute_query(
        """
        MATCH (n)
        WHERE n.path STARTS WITH $prefix
           OR n.file_path STARTS WITH $prefix
           OR n.name = 'zz_graph_test_unresolved'
        DETACH DELETE n
        """,
        {"prefix": PREFIX},
    )


@pytest.fixture(scope="module")
def neo4j():
    connection = Neo4jConnection()

    try:
        connection.verify_connection()
    except Exception:
        connection.close()
        pytest.skip("Neo4j database is not running.")

    cleanup(connection)

    # a.py -> b.py -> c.py, d.py on its own.
    builder = DependencyGraphBuilder(connection)
    for name in ["a.py", "b.py", "c.py", "d.py"]:
        builder.store_file(PREFIX + name, "python")
    builder.store_import(PREFIX + "a.py", PREFIX + "b.py", 1)
    builder.store_import(PREFIX + "b.py", PREFIX + "c.py", 1)
    builder.store_symbols(PREFIX + "c.py", [
        {"type": "class", "name": "Thing", "file_path": PREFIX + "c.py", "line": 1},
    ])
    builder.store_call(PREFIX + "a.py", "zz_graph_test_unresolved", 2)

    yield connection

    cleanup(connection)
    connection.close()


def test_real_projects_include_test_repository(neo4j):
    projects = {p["id"]: p for p in GraphView(neo4j).projects()}

    assert projects[PREFIX]["files"] == 4


def test_real_project_graph(neo4j):
    graph = GraphView(neo4j).graph(
        project=PREFIX, include_symbols=True, include_calls=True
    )
    types = sorted(node["type"] for node in graph["nodes"])

    assert types == ["class", "external", "file", "file", "file", "file"]
    assert sorted(e["type"] for e in graph["edges"]) == [
        "calls", "contains", "imports", "imports",
    ]


def test_real_neighbourhood_respects_depth(neo4j):
    view = GraphView(neo4j)

    one_hop = view.graph(file=PREFIX + "a.py", depth=1)
    two_hops = view.graph(file=PREFIX + "a.py", depth=2)

    assert [n["path"] for n in one_hop["nodes"]] == [PREFIX + "a.py", PREFIX + "b.py"]
    assert {n["path"] for n in two_hops["nodes"]} == {
        PREFIX + "a.py", PREFIX + "b.py", PREFIX + "c.py",
    }
