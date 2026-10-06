from app.database.neo4j import Neo4jConnection
from app.parser.javascript_symbols import JavaScriptSymbolExtractor


SOURCE_CODE = """
class User {
    constructor(name) {
        this.name = name;
    }

    greet() {
        console.log("Hello", this.name);
    }
}

function calculateTotal(a, b) {
    const total = a + b;
    return total;
}

const message = "Code Dependency Graph";
"""


def main():

    database = Neo4jConnection()

    try:
        database.verify_connection()

        database.initialize_schema()

        file_path = "example.js"

        database.create_file(
            file_path,
            "javascript"
        )

        extractor = JavaScriptSymbolExtractor()

        symbols = extractor.extract_symbols(
            SOURCE_CODE,
            file_path
        )

        for symbol in symbols:

            database.create_symbol(
                symbol
            )

            database.create_file_symbol_relationship(
                symbol
            )

        print(
            f"Loaded {len(symbols)} symbols into Neo4j."
        )

    finally:
        database.close()


if __name__ == "__main__":
    main()