import pytest
from fastapi.testclient import TestClient

from app.main import app, get_database
from app.database.search import (
    SEARCH_FILES,
    SEARCH_SYMBOLS,
    SymbolSearch,
    build_lucene_query,
    escape_lucene,
)


class FakeDatabase:
    """
    Records queries and returns one canned result row.
    """

    def __init__(self, total=0, page=None):
        self.rows = [{"total": total, "page": page or []}]
        self.queries = []

    def execute_query(self, query, parameters=None):
        self.queries.append((query, parameters or {}))

        return self.rows


def symbol_match(name, label="Class", tier=3, score=1.0):
    return {
        "label": label,
        "name": name,
        "file_path": "models.py",
        "line": 1,
        "score": score,
        "tier": tier,
    }


@pytest.fixture
def fake_database():
    database = FakeDatabase()

    app.dependency_overrides[get_database] = lambda: database

    yield database

    app.dependency_overrides.clear()


client = TestClient(app)


# Lucene query building

def test_escape_lucene_escapes_special_characters():

    assert escape_lucene("a+b") == r"a\+b"
    assert escape_lucene("foo(bar)") == r"foo\(bar\)"
    assert escape_lucene("x:y/z") == r"x\:y\/z"
    assert escape_lucene("plain_name") == "plain_name"


def test_build_lucene_query_matches_exact_prefix_contains_and_typos():

    assert build_lucene_query("UserService") == (
        "(userservice^4 OR userservice*^2 OR *userservice* OR userservice~2)"
    )


def test_build_lucene_query_uses_smaller_edit_distance_for_short_words():

    assert build_lucene_query("usr").endswith("usr~1)")


def test_build_lucene_query_without_fuzzy_has_no_typo_clause():

    assert "~" not in build_lucene_query("UserService", fuzzy=False)


def test_build_lucene_query_requires_every_word():

    assert build_lucene_query("user  service", fuzzy=False) == (
        "(user^4 OR user*^2 OR *user*) AND "
        "(service^4 OR service*^2 OR *service*)"
    )


def test_build_lucene_query_cannot_be_broken_by_user_input():

    lucene = build_lucene_query('foo") OR *:*', fuzzy=False)

    assert '\\"' in lucene
    assert "\\*\\:\\*" in lucene


# SymbolSearch

def test_search_symbols_passes_parameters_to_query():

    database = FakeDatabase()

    SymbolSearch(database).search_symbols(
        "  User ",
        types=["function", "method"],
        file_path="app.py",
        limit=5,
        offset=10,
    )

    query, parameters = database.queries[0]

    assert query == SEARCH_SYMBOLS
    assert parameters["index"] == "symbol_name_fulltext"
    assert parameters["term"] == "user"
    assert parameters["labels"] == ["Function", "Method"]
    assert parameters["file_path"] == "app.py"
    assert parameters["limit"] == 5
    assert parameters["offset"] == 10


def test_search_symbols_without_types_searches_all_labels():

    database = FakeDatabase()

    SymbolSearch(database).search_symbols("User")

    assert database.queries[0][1]["labels"] is None


def test_search_symbols_converts_rows_to_results():

    database = FakeDatabase(total=2, page=[
        symbol_match("User", tier=3, score=2.5),
        symbol_match("greet_user", label="Method", tier=1),
    ])

    total, results = SymbolSearch(database).search_symbols("user")

    assert total == 2
    assert results[0] == {
        "type": "class",
        "name": "User",
        "file_path": "models.py",
        "line": 1,
        "score": 2.5,
        "match": "exact",
    }
    assert results[1]["type"] == "method"
    assert results[1]["match"] == "contains"


def test_search_handles_empty_result():

    database = FakeDatabase()
    database.rows = []

    assert SymbolSearch(database).search_symbols("nothing") == (0, [])


def test_search_files_passes_lowercased_term():

    database = FakeDatabase(total=1, page=[
        {"path": "app/Main.py", "language": "python", "tier": 3},
    ])

    total, results = SymbolSearch(database).search_files("MAIN.py", 10, 0)

    query, parameters = database.queries[0]

    assert query == SEARCH_FILES
    assert parameters == {"term": "main.py", "limit": 10, "offset": 0}
    assert total == 1
    assert results == [
        {"path": "app/Main.py", "language": "python", "match": "exact"}
    ]


# Endpoints

def test_search_symbols_endpoint_returns_paginated_response(fake_database):

    fake_database.rows = [{
        "total": 41,
        "page": [symbol_match("User")],
    }]

    response = client.get(
        "/search/symbols",
        params={"q": "User", "limit": 1, "offset": 20}
    )

    assert response.status_code == 200
    assert response.json() == {
        "query": "User",
        "total": 41,
        "limit": 1,
        "offset": 20,
        "results": [{
            "type": "class",
            "name": "User",
            "file_path": "models.py",
            "line": 1,
            "score": 1.0,
            "match": "exact",
        }],
    }


def test_search_symbols_endpoint_accepts_several_types(fake_database):

    client.get(
        "/search/symbols",
        params=[("q", "run"), ("type", "class"), ("type", "variable")]
    )

    assert fake_database.queries[0][1]["labels"] == ["Class", "Variable"]


def test_search_classes_endpoint_only_searches_classes(fake_database):

    client.get("/search/classes", params={"q": "User"})

    assert fake_database.queries[0][1]["labels"] == ["Class"]


def test_search_functions_endpoint_includes_methods(fake_database):

    client.get("/search/functions", params={"q": "greet"})

    assert fake_database.queries[0][1]["labels"] == ["Function", "Method"]


def test_search_fuzzy_can_be_turned_off(fake_database):

    client.get("/search/symbols", params={"q": "UserService", "fuzzy": False})

    assert "~" not in fake_database.queries[0][1]["lucene"]


def test_search_files_endpoint(fake_database):

    fake_database.rows = [{
        "total": 1,
        "page": [{"path": "app/main.py", "language": "python", "tier": 2}],
    }]

    response = client.get("/search/files", params={"q": "main"})

    assert response.status_code == 200
    assert response.json()["results"] == [
        {"path": "app/main.py", "language": "python", "match": "prefix"}
    ]


@pytest.mark.parametrize("params", [
    {},
    {"q": ""},
    {"q": "User", "limit": 0},
    {"q": "User", "limit": 101},
    {"q": "User", "offset": -1},
    {"q": "User", "type": "interface"},
])
def test_search_symbols_rejects_invalid_parameters(fake_database, params):

    response = client.get("/search/symbols", params=params)

    assert response.status_code == 422
    assert fake_database.queries == []


@pytest.mark.parametrize("path", ["/search/symbols", "/search/files"])
def test_search_rejects_whitespace_only_query(fake_database, path):

    response = client.get(path, params={"q": "   "})

    assert response.status_code == 400
    assert fake_database.queries == []
