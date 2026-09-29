from fastapi import FastAPI
from pydantic import BaseModel

from app.parser.python_symbols import PythonSymbolExtractor


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