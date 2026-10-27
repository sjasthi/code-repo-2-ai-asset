import logging
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from tempfile import TemporaryDirectory

from app.parser.registry import extract_symbols, UnsupportedLanguageError
from app.database.neo4j import Neo4jConnection
from app.dependencies.extractor import DependencyExtractor
from app.dependencies.resolver import ImportResolver
from app.database.graph_builder import DependencyGraphBuilder
from app.database.search import SymbolSearch
from app.repositories.github_importer import (
    GitHubRepositoryImporter,
    GitHubRepositoryImportError,
)
from app.database.graph_queries import (
    FILE_IMPORTS,
    FILE_IMPORTED_BY,
    CLASS_IMPORTED_BY,
)


logger = logging.getLogger(__name__)


# One connection shared by all requests. The Neo4j driver pools and
# reuses sockets; opening a new driver per request cost ~2 s on Windows.
_database = None


def get_database():
    """
    Return the shared Neo4j connection, creating it on first use.
    """
    global _database

    if _database is None:
        _database = Neo4jConnection()

    return _database


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _database

    # Create constraints and search indexes. The API still starts without
    # Neo4j so /parse works offline; search needs the indexes later.
    try:
        get_database().initialize_schema()

    except Exception as error:
        logger.warning("Could not initialize Neo4j schema: %s", error)

    yield

    if _database is not None:
        _database.close()
        _database = None


app = FastAPI(
    title="Code Dependency Graph API",
    description="Backend for analyzing source code and extracting symbols.",
    version="0.1.0",
    lifespan=lifespan,
)


# Allow the React dev server (Vite) to call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CodeRequest(BaseModel):
    file_path: str
    source_code: str


class RepositoryImportRequest(BaseModel):
    repository_url: str
    branch: str | None = None


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


@app.post("/repositories/import")
def import_github_repository(
    request: RepositoryImportRequest,
    database: Neo4jConnection = Depends(get_database),
):
    importer = GitHubRepositoryImporter()

    with TemporaryDirectory(prefix="code-repo-import-") as temporary_directory:
        try:
            repository = importer.import_repository(
                request.repository_url,
                temporary_directory,
                request.branch,
            )
        except GitHubRepositoryImportError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        project_root = Path(temporary_directory)
        repository_prefix = (
            f"github.com/{repository['owner']}/{repository['repository']}/"
        )
        resolver = ImportResolver(str(project_root))
        dependency_extractor = DependencyExtractor()
        graph_builder = DependencyGraphBuilder(database)

        # Analyze everything before replacing the repository's previous graph.
        analyzed_files = []
        dependencies_found = 0

        for file_info in repository["files"]:
            relative_path = file_info["path"]
            language = file_info["language"]
            source_code = (
                project_root / Path(*relative_path.split("/"))
            ).read_text(encoding="utf-8")
            graph_path = repository_prefix + relative_path

            try:
                detected_language, symbols, has_syntax_errors = extract_symbols(
                    source_code,
                    graph_path,
                    language,
                )
            except UnsupportedLanguageError as error:
                # Defensive: importer filters extensions using the same registry.
                raise HTTPException(status_code=400, detail=str(error)) from error

            dependencies = []
            if detected_language in ("python", "javascript", "typescript"):
                dependencies = dependency_extractor.extract(
                    source_code,
                    relative_path,
                    detected_language,
                )

                for dependency in dependencies:
                    if dependency["type"] != "import":
                        continue

                    resolved = resolver.resolve(
                        relative_path,
                        dependency["target"],
                        detected_language,
                    )
                    dependency["resolved_target"] = (
                        repository_prefix + resolved if resolved else None
                    )

            dependencies_found += len(dependencies)
            analyzed_files.append({
                "path": graph_path,
                "language": detected_language,
                "symbols": symbols,
                "dependencies": dependencies,
                "has_syntax_errors": has_syntax_errors,
            })

        # Re-imports replace this repository's old files/symbols instead of
        # leaving deleted or renamed files in the graph.
        database.execute_query(
            """
            MATCH (s)
            WHERE s.file_path STARTS WITH $prefix
            DETACH DELETE s
            """,
            {"prefix": repository_prefix},
        )
        database.execute_query(
            """
            MATCH (f:File)
            WHERE f.path STARTS WITH $prefix
            DETACH DELETE f
            """,
            {"prefix": repository_prefix},
        )

        symbols_stored = 0
        relationships_stored = 0

        for file_info in analyzed_files:
            relationships_stored += graph_builder.store_dependencies(
                file_info["path"],
                file_info["language"],
                file_info["dependencies"],
            )
            symbols_stored += graph_builder.store_symbols(
                file_info["path"],
                file_info["symbols"],
            )

        return {
            "status": "imported",
            "repository": (
                f"{repository['owner']}/{repository['repository']}"
            ),
            "branch": repository["branch"],
            "files_analyzed": len(analyzed_files),
            "symbols_stored": symbols_stored,
            "dependencies_found": dependencies_found,
            "relationships_stored": relationships_stored,
            "skipped_files": repository["skipped_files"],
            "files_with_syntax_errors": sum(
                1 for file_info in analyzed_files
                if file_info["has_syntax_errors"]
            ),
            "graph_path_prefix": repository_prefix,
        }


SymbolType = Literal["class", "function", "method", "variable"]


class SymbolSearchResult(BaseModel):
    type: str
    name: str
    file_path: str
    line: int
    score: float
    match: Literal["exact", "prefix", "contains", "fuzzy"]


class SymbolSearchResponse(BaseModel):
    query: str
    total: int
    limit: int
    offset: int
    results: list[SymbolSearchResult]


class FileSearchResult(BaseModel):
    path: str
    language: str | None
    match: Literal["exact", "prefix", "contains"]


class FileSearchResponse(BaseModel):
    query: str
    total: int
    limit: int
    offset: int
    results: list[FileSearchResult]


def _require_query(q: str) -> str:
    q = q.strip()

    if not q:
        raise HTTPException(status_code=400, detail="Search query is empty.")

    return q


def _search_symbols(database, q, types, file_path, fuzzy, limit, offset):
    q = _require_query(q)

    total, results = SymbolSearch(database).search_symbols(
        q,
        types=types,
        file_path=file_path,
        fuzzy=fuzzy,
        limit=limit,
        offset=offset,
    )

    return {
        "query": q,
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": results,
    }


@app.get("/search/symbols", response_model=SymbolSearchResponse)
def search_symbols(
    q: str = Query(..., min_length=1, description="Symbol name to search for."),
    type: list[SymbolType] | None = Query(
        None,
        description="Only return these symbol types. Repeat to pass several.",
    ),
    file_path: str | None = Query(
        None,
        description="Only return symbols defined in this file.",
    ),
    fuzzy: bool = Query(True, description="Also match names with typos."),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    database: Neo4jConnection = Depends(get_database),
):
    """
    Search every stored symbol by name.

    Results are ranked exact match > prefix > contains > fuzzy (typo),
    then by full-text relevance score.
    """
    return _search_symbols(database, q, type, file_path, fuzzy, limit, offset)


@app.get("/search/classes", response_model=SymbolSearchResponse)
def search_classes(
    q: str = Query(..., min_length=1, description="Class name to search for."),
    fuzzy: bool = Query(True, description="Also match names with typos."),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    database: Neo4jConnection = Depends(get_database),
):
    """
    Find classes by name. Same ranking as /search/symbols.
    """
    return _search_symbols(database, q, ["class"], None, fuzzy, limit, offset)


@app.get("/search/functions", response_model=SymbolSearchResponse)
def search_functions(
    q: str = Query(..., min_length=1, description="Function name to search for."),
    fuzzy: bool = Query(True, description="Also match names with typos."),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    database: Neo4jConnection = Depends(get_database),
):
    """
    Find functions and methods by name. Same ranking as /search/symbols.
    """
    return _search_symbols(
        database, q, ["function", "method"], None, fuzzy, limit, offset
    )


@app.get("/search/files", response_model=FileSearchResponse)
def search_files(
    q: str = Query(..., min_length=1, description="Part of a file path."),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    database: Neo4jConnection = Depends(get_database),
):
    """
    Find files whose path contains the query (case-insensitive).

    Ranked exact file name > file name prefix > path contains, then
    shorter paths first.
    """
    q = _require_query(q)

    total, results = SymbolSearch(database).search_files(q, limit, offset)

    return {
        "query": q,
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": results,
    }
