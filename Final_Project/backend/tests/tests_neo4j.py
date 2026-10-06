import os

import pytest

from app.database.neo4j import Neo4jConnection


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

    yield connection

    connection.close()


def test_neo4j_connection(database):

    assert database.driver is not None


def test_create_file(database):

    database.initialize_schema()

    result = database.create_file(
        "test_file.ts",
        "typescript"
    )

    assert result is not None


def test_create_symbol(database):

    database.initialize_schema()

    database.create_file(
        "test_symbols.js",
        "javascript"
    )

    symbol = {
        "type": "function",
        "name": "testFunction",
        "file_path": "test_symbols.js",
        "line": 1
    }

    result = database.create_symbol(
        symbol
    )

    assert result is not None


def test_create_file_symbol_relationship(database):

    database.initialize_schema()

    database.create_file(
        "relationship.js",
        "javascript"
    )

    symbol = {
        "type": "function",
        "name": "function_test",
        "file_path": "relationship.js",
        "line": 1
    }

    database.create_symbol(symbol)

    result = database.create_file_symbol_relationship(
        symbol
    )

    assert result == []