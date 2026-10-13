from app.database.graph_builder import DependencyGraphBuilder


class FakeDatabase:

    def __init__(self):
        self.queries = []

    def execute_query(self, query, parameters=None):
        self.queries.append((query, parameters or {}))

        return []


def symbol(symbol_type, name, line):
    return {
        "type": symbol_type,
        "name": name,
        "file_path": "models.py",
        "line": line
    }


def test_store_symbol_uses_label_for_symbol_type():

    database = FakeDatabase()
    builder = DependencyGraphBuilder(database)

    assert builder.store_symbol(symbol("class", "User", 1)) is True

    query, parameters = database.queries[0]

    assert "MERGE (s:Class" in query
    assert "MERGE (f)-[:CONTAINS]->(s)" in query
    assert parameters == {
        "file_path": "models.py",
        "name": "User",
        "line": 1
    }


def test_store_symbol_skips_types_without_a_label():

    database = FakeDatabase()
    builder = DependencyGraphBuilder(database)

    assert builder.store_symbol(symbol("interface", "Greeter", 1)) is False
    assert database.queries == []


def test_store_symbols_clears_stale_symbols_first():

    database = FakeDatabase()
    builder = DependencyGraphBuilder(database)

    stored = builder.store_symbols("models.py", [
        symbol("class", "User", 1),
        symbol("interface", "Greeter", 5),
        symbol("method", "greet", 2),
    ])

    assert stored == 2

    clear_query, clear_parameters = database.queries[0]

    assert "DETACH DELETE symbol" in clear_query
    assert clear_parameters == {
        "file_path": "models.py",
        "keep": [["Class", "User", 1], ["Method", "greet", 2]]
    }
