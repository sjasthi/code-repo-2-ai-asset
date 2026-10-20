"""
Search tests against a real Neo4j database.

Skipped when Neo4j is not running. All test data lives under the
__search_test__/ path prefix and is deleted afterwards.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.neo4j import Neo4jConnection
from app.database.graph_builder import DependencyGraphBuilder
from app.database.search import SymbolSearch


PREFIX = "__search_test__/"
FILE = PREFIX + "models.py"

SYMBOLS = [
    ("class", "UserService", 1),
    ("class", "User", 10),
    ("method", "get_user", 11),
    ("class", "UserRepository", 20),
    ("function", "create_user", 30),
    ("variable", "user_count", 40),
    ("class", "OrderService", 50),
]


def cleanup(database):
    database.execute_query(
        """
        MATCH (n)
        WHERE n.path STARTS WITH $prefix
           OR n.file_path STARTS WITH $prefix
           OR n.name = 'zz_search_test_unresolved'
        DETACH DELETE n
        """,
        {"prefix": PREFIX},
    )


@pytest.fixture(scope="module")
def database():
    connection = Neo4jConnection()

    try:
        connection.verify_connection()
    except Exception:
        connection.close()
        pytest.skip("Neo4j database is not running.")

    connection.initialize_schema()
    connection.execute_query("CALL db.awaitIndexes(60)")
    cleanup(connection)

    builder = DependencyGraphBuilder(connection)
    builder.store_file(FILE, "python")
    builder.store_symbols(FILE, [
        {"type": kind, "name": name, "file_path": FILE, "line": line}
        for kind, name, line in SYMBOLS
    ])

    # Placeholder node like the ones store_call creates for unresolved calls.
    connection.execute_query(
        "MERGE (:Function {name: 'zz_search_test_unresolved'})"
    )

    yield connection

    cleanup(connection)
    connection.close()


def search(database, query, **options):
    options.setdefault("file_path", FILE)

    return SymbolSearch(database).search_symbols(query, **options)


def names(results):
    return [result["name"] for result in results]


def test_exact_match_ranks_first(database):

    total, results = search(database, "user")

    assert results[0]["name"] == "User"
    assert results[0]["match"] == "exact"


def test_results_are_ordered_by_match_quality(database):

    _, results = search(database, "user", limit=100)

    order = ["exact", "prefix", "contains", "fuzzy"]
    tiers = [order.index(result["match"]) for result in results]

    assert tiers == sorted(tiers)
    assert {"UserService", "UserRepository", "user_count"} <= set(names(results))


def test_typo_finds_intended_symbol(database):

    _, results = search(database, "UserServce")

    assert "UserService" in names(results)
    assert results[names(results).index("UserService")]["match"] == "fuzzy"


def test_typo_not_found_when_fuzzy_disabled(database):

    total, _ = search(database, "UserServce", fuzzy=False)

    assert total == 0


def test_substring_in_middle_of_name_matches(database):

    _, results = search(database, "service")

    assert {"UserService", "OrderService"} <= set(names(results))
    assert all(result["match"] == "contains" for result in results[:2])


def test_type_filter(database):

    _, results = search(database, "user", types=["function", "method"])

    assert set(names(results)) == {"get_user", "create_user"}


def test_pagination_pages_do_not_overlap(database):

    total, first = search(database, "user", limit=2, offset=0)
    same_total, second = search(database, "user", limit=2, offset=2)

    assert total == same_total
    assert len(first) == 2
    assert not set(names(first)) & set(names(second))


def test_unresolved_call_placeholders_are_not_returned(database):

    total, _ = SymbolSearch(database).search_symbols(
        "zz_search_test_unresolved"
    )

    assert total == 0


def test_search_endpoint_against_real_database(database):

    response = TestClient(app).get(
        "/search/symbols",
        params={"q": "User", "file_path": FILE}
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["name"] == "User"


def test_file_search(database):

    total, results = SymbolSearch(database).search_files("__search_test__/MODELS")

    assert total == 1
    assert results[0]["path"] == FILE
