"""
Benchmark symbol search on a large generated codebase.

Loads SYMBOL_COUNT symbols into Neo4j under the __benchmark__/ path
prefix, times searches through the HTTP API, then deletes the data.

Run from Final_Project/backend with Neo4j running:

    python -m tests.benchmark_search
"""
import itertools
import statistics
import time

from fastapi.testclient import TestClient

from app.main import app
from app.database.neo4j import Neo4jConnection


PREFIX = "__benchmark__/"
SYMBOL_COUNT = 12_000
FILE_COUNT = 600
TARGET_MS = 500
RUNS_PER_QUERY = 10

WORDS = [
    "user", "order", "payment", "invoice", "account", "session", "cache",
    "token", "report", "product", "customer", "message", "queue", "event",
    "config", "file", "graph", "node", "search", "index",
]
SUFFIXES = [
    "service", "repository", "controller", "manager", "handler", "factory",
    "client", "model", "view", "helper",
]

QUERIES = {
    "exact": "UserService",
    "prefix": "Payment",
    "substring": "repository",
    "typo": "CustmerHandlr",
    "short": "id",
    "two words": "order manager",
}


def generate_symbols():
    names = itertools.cycle(
        (first, second)
        for first in WORDS
        for second in SUFFIXES
    )

    for i in range(SYMBOL_COUNT):
        first, second = next(names)
        file_path = f"{PREFIX}module_{i % FILE_COUNT}.py"
        kind = ("Class", "Function", "Method", "Variable")[i % 4]

        if kind == "Class":
            name = first.title() + second.title()
        else:
            name = f"{first}_{second}_{i}"

        yield kind, {"name": name, "file_path": file_path, "line": i}


def load(database):
    by_label = {}

    for label, row in generate_symbols():
        by_label.setdefault(label, []).append(row)

    for label, rows in by_label.items():
        for start in range(0, len(rows), 2_000):
            database.execute_query(
                f"""
                UNWIND $rows AS row
                MERGE (f:File {{path: row.file_path}})
                SET f.language = 'python'
                CREATE (s:{label} {{
                    name: row.name,
                    file_path: row.file_path,
                    line: row.line
                }})
                CREATE (f)-[:CONTAINS]->(s)
                """,
                {"rows": rows[start:start + 2_000]},
            )


def cleanup(database):
    database.execute_query(
        """
        MATCH (n)
        WHERE n.path STARTS WITH $prefix OR n.file_path STARTS WITH $prefix
        CALL { WITH n DETACH DELETE n } IN TRANSACTIONS OF 5000 ROWS
        """,
        {"prefix": PREFIX},
    )


def time_request(client, path, params):
    start = time.perf_counter()
    response = client.get(path, params=params)
    elapsed_ms = (time.perf_counter() - start) * 1000

    response.raise_for_status()

    return elapsed_ms, response.json()["total"]


def benchmark():
    database = Neo4jConnection()
    client = TestClient(app)

    try:
        database.verify_connection()
        database.initialize_schema()
        database.execute_query("CALL db.awaitIndexes(120)")
        cleanup(database)

        start = time.perf_counter()
        load(database)
        print(
            f"Loaded {SYMBOL_COUNT:,} symbols in {FILE_COUNT} files "
            f"({time.perf_counter() - start:.1f} s)\n"
        )

        cases = [
            ("/search/symbols", label, {"q": query})
            for label, query in QUERIES.items()
        ]
        cases.append(("/search/symbols", "page 10", {"q": "user", "offset": 200}))
        cases.append(("/search/files", "files", {"q": "module_42"}))

        worst = 0

        for path, label, params in cases:
            # Warm-up request, not timed.
            time_request(client, path, params)

            timings = []

            for _ in range(RUNS_PER_QUERY):
                elapsed_ms, total = time_request(client, path, params)
                timings.append(elapsed_ms)

            worst = max(worst, max(timings))

            print(
                f"{label:<10} {params['q']!r:<17} "
                f"results={total:>6,}  "
                f"median={statistics.median(timings):6.1f} ms  "
                f"max={max(timings):6.1f} ms"
            )

        verdict = "PASS" if worst < TARGET_MS else "FAIL"
        print(f"\nSlowest request: {worst:.1f} ms (target < {TARGET_MS} ms): {verdict}")

    finally:
        cleanup(database)
        database.close()


if __name__ == "__main__":
    benchmark()
