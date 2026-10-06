from fastapi import FastAPI
from pydantic import BaseModel

from app.parser.python_symbols import PythonSymbolExtractor
from app.parser.javascript_symbols import JavaScriptSymbolExtractor
from app.parser.typescript_symbols import TypeScriptSymbolExtractor
from app.database.neo4j import Neo4jConnection


app = FastAPI(
    title="Code Dependency Graph API",
    description="Backend for analyzing source code and extracting symbols.",
    version="0.1.0"
)


class CodeRequest(BaseModel):
    file_path: str
    source_code: str


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


@app.post("/parse/python")
def parse_python(request: CodeRequest):

    extractor = PythonSymbolExtractor()

    symbols = extractor.extract_symbols(
        request.source_code,
        request.file_path
    )

    return {
        "file": request.file_path,
        "symbols": symbols
    }


@app.post("/parse/javascript")
def parse_javascript(request: CodeRequest):

    extractor = JavaScriptSymbolExtractor()

    symbols = extractor.extract_symbols(
        request.source_code,
        request.file_path
    )

    return {
        "file": request.file_path,
        "symbols": symbols
    }


@app.post("/parse/typescript")
def parse_typescript(request: CodeRequest):

    extractor = TypeScriptSymbolExtractor()

    symbols = extractor.extract_symbols(
        request.source_code,
        request.file_path
    )

    return {
        "file": request.file_path,
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
