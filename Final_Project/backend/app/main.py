from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from app.parser.registry import extract_symbols, UnsupportedLanguageError
from app.database.neo4j import Neo4jConnection
from app.dependencies.extractor import DependencyExtractor
from app.dependencies.resolver import ImportResolver
from app.database.graph_builder import DependencyGraphBuilder
from app.database.graph_queries import (
    FILE_IMPORTS,
    FILE_IMPORTED_BY,
    CLASS_IMPORTED_BY,
)


app = FastAPI(
    title="Code Dependency Graph API",
    description="Backend for analyzing source code and extracting symbols.",
    version="0.1.0"
)


def get_database():
    """
    Open a Neo4j connection for one request and close it afterwards.
    """
    database = Neo4jConnection()

    try:
        yield database

    finally:
        database.close()


class CodeRequest(BaseModel):
    file_path: str
    source_code: str


class ParseRequest(CodeRequest):
    # Optional override; detected from file_path's extension when omitted.
    language: str | None = None


@app.get("/")
def root():
    return {
        "message": "Code Dependency Graph API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.post("/parse")
def parse(request: ParseRequest):

    try:
        language, symbols, has_syntax_errors = extract_symbols(
            request.source_code,
            request.file_path,
            request.language
        )

    except UnsupportedLanguageError as error:
        raise HTTPException(status_code=400, detail=str(error))

    return {
        "file": request.file_path,
        "language": language,
        "has_syntax_errors": has_syntax_errors,
        "symbols": symbols
    }


@app.get("/health/neo4j")
def neo4j_health():

    database = Neo4jConnection()

    try:
        database.verify_connection()

        return {
            "status": "healthy",
            "neo4j": "connected"
        }

    except Exception as error:

        return {
            "status": "unhealthy",
            "neo4j": str(error)
        }

    finally:
        database.close()


@app.get("/symbols")
def get_symbols():

    database = Neo4jConnection()

    try:

        query = """
        MATCH (s)
        WHERE s.name IS NOT NULL
        RETURN labels(s) AS type,
               s.name AS name,
               s.file_path AS file_path,
               s.line AS line
        ORDER BY s.file_path, s.line
        """

        results = database.execute_query(query)

        return {
            "symbols": results
        }

    finally:
        database.close()


from pathlib import Path

# Set this to the root directory of the code project being analyzed.
PROJECT_ROOT = Path("sample_code").resolve()


@app.post("/dependencies/parse")
def parse_dependencies(request: CodeRequest, language: str = "python"):
    extractor = DependencyExtractor()

    dependencies = extractor.extract(
        request.source_code,
        request.file_path,
        language,
    )

    resolver = ImportResolver(str(PROJECT_ROOT))

    for dependency in dependencies:
        if dependency["type"] == "import":
            resolved = resolver.resolve(
                request.file_path,
                dependency["target"],
                language,
            )
            dependency["resolved_target"] = resolved

    return {
        "file": request.file_path,
        "language": language,
        "dependencies": dependencies,
    }


@app.get("/dependencies/imports")
def get_file_imports(
    file_path: str,
    database: Neo4jConnection = Depends(get_database),
):
    return database.execute_query(
        FILE_IMPORTS,
        {"file_path": file_path},
    )


@app.get("/dependencies/imported-by")
def get_file_imported_by(
    file_path: str,
    database: Neo4jConnection = Depends(get_database),
):
    return database.execute_query(
        FILE_IMPORTED_BY,
        {"file_path": file_path},
    )


@app.get("/dependencies/class-imported-by")
def get_class_imported_by(
    class_name: str,
    database: Neo4jConnection = Depends(get_database),
):
    return database.execute_query(
        CLASS_IMPORTED_BY,
        {"class_name": class_name},
    )


@app.post("/dependencies/analyze")
def analyze_and_store_dependencies(
    request: CodeRequest,
    language: str = "python",
    database: Neo4jConnection = Depends(get_database),
):
    extractor = DependencyExtractor()

    dependencies = extractor.extract(
        request.source_code,
        request.file_path,
        language,
    )

    resolver = ImportResolver(str(PROJECT_ROOT))

    for dependency in dependencies:
        if dependency["type"] == "import":
            dependency["resolved_target"] = resolver.resolve(
                request.file_path,
                dependency["target"],
                language,
            )

    builder = DependencyGraphBuilder(database)

    stored_count = builder.store_dependencies(
        request.file_path,
        language,
        dependencies,
    )

    _, symbols, _ = extract_symbols(
        request.source_code,
        request.file_path,
        language,
    )

    symbols_stored = builder.store_symbols(request.file_path, symbols)

    return {
        "file": request.file_path,
        "language": language,
        "dependencies_found": len(dependencies),
        "relationships_stored": stored_count,
        "symbols_stored": symbols_stored,
        "dependencies": dependencies,
    }
