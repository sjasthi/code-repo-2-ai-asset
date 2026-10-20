"""
Neo4jConnection tests against a real Neo4j database.

Skipped when Neo4j is not running. All test data lives under the
__neo4j_test__/ path prefix and is deleted after each test.
"""
import pytest

from app.database.neo4j import Neo4jConnection


PREFIX = "__neo4j_test__/"


def cleanup(connection):
    connection.execute_query(
        """
        MATCH (n)
        WHERE n.path STARTS WITH $prefix OR n.file_path STARTS WITH $prefix
        DETACH DELETE n
        """,
        {"prefix": PREFIX},
    )


@pytest.fixture
def database():

    connection = Neo4jConnection()

    try:
        connection.verify_connection()
    except Exception:
        connection.close()
        pytest.skip(
            "Neo4j database is not running."
        )

    connection.initialize_schema()

    yield connection

    cleanup(connection)
    connection.close()


def test_neo4j_connection(database):

    assert database.driver is not None


def test_create_file(database):

    result = database.create_file(
        PREFIX + "test_file.ts",
        "typescript"
    )

    assert result[0]["f"]["path"] == PREFIX + "test_file.ts"


def test_create_symbol(database):

    database.create_file(
        PREFIX + "test_symbols.js",
        "javascript"
    )

    symbol = {
        "type": "function",
        "name": "testFunction",
        "file_path": PREFIX + "test_symbols.js",
        "line": 1
    }

    result = database.create_symbol(
        symbol
    )

    assert result[0]["s"]["name"] == "testFunction"


def test_create_file_symbol_relationship(database):

    database.create_file(
        PREFIX + "relationship.js",
        "javascript"
    )

    symbol = {
        "type": "function",
        "name": "function_test",
        "file_path": PREFIX + "relationship.js",
        "line": 1
    }

    database.create_symbol(symbol)

    database.create_file_symbol_relationship(
        symbol
    )

    contained = database.execute_query(
        """
        MATCH (:File {path: $path})-[:CONTAINS]->(s:Function)
        RETURN s.name AS name
        """,
        {"path": PREFIX + "relationship.js"},
    )

    assert contained == [{"name": "function_test"}]


def test_tests_leave_no_data_behind(database):

    # Runs last in this file: earlier tests' data must already be gone.
    leftover = database.execute_query(
        """
        MATCH (n)
        WHERE n.path STARTS WITH $prefix OR n.file_path STARTS WITH $prefix
        RETURN count(n) AS count
        """,
        {"prefix": PREFIX},
    )

    assert leftover == [{"count": 0}]
