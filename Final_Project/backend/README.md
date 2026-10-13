# Code Dependency Graph - Backend

## Overview

This is the Python backend for the Code Dependency Graph project.

The backend is responsible for analyzing source code and extracting structured information about the codebase.

## Technology Stack

- Python
- FastAPI
- Uvicorn
- Tree-sitter
- tree-sitter-python
- pytest

## Architecture

The current FP3 pipeline is:

Python source code
        |
        v
FastAPI API
        |
        v
Python Symbol Extractor
        |
        v
Tree-sitter Parser
        |
        v
Python Syntax Tree
        |
        v
Extracted Symbols
        |
        v
JSON response

## Tree-sitter

Tree-sitter is used to parse Python source code into a syntax tree.

Instead of treating source code as plain text, Tree-sitter identifies syntactic structures such as:

- Classes
- Functions
- Methods
- Assignments

The symbol extractor walks through the syntax tree and identifies these structures.

## Python Symbol Extraction

The FP3 symbol extractor currently identifies:

- Classes
- Functions
- Methods
- Variables

Each extracted symbol contains:

- Symbol type
- Symbol name
- File path
- Line number

## API Endpoints

### GET /

Checks that the backend is running.

### GET /health

Returns the backend health status.

### POST /parse

Parses source code and returns the extracted symbols.

The language is detected from the `file_path` extension, or set explicitly
with an optional `language` field. Unsupported languages or extensions return `400`.

| Language   | `language` values      | Extensions                                 |
|------------|------------------------|--------------------------------------------|
| Python     | `python`, `py`         | `.py`, `.pyi`                              |
| JavaScript | `javascript`, `js`     | `.js`, `.jsx`, `.mjs`, `.cjs`              |
| TypeScript | `typescript`, `ts`     | `.ts`, `.mts`, `.cts`                      |
| Go         | `go`, `golang`         | `.go`                                      |
| Rust       | `rust`, `rs`           | `.rs`                                      |
| Java       | `java`                 | `.java`                                    |
| C          | `c`                    | `.c`, `.h`                                 |
| C++        | `cpp`, `c++`           | `.cpp`, `.cc`, `.cxx`, `.hpp`, `.hh`, `.hxx` |
| Ruby       | `ruby`, `rb`           | `.rb`                                      |

Python, JavaScript, and TypeScript use hand-written extractors. The other
languages share one generic extractor (`app/parser/tags_symbols.py`) that runs
tree-sitter "tags" queries from `tree-sitter-language-pack`. To add a language
the pack supports, add it to `TAGS_LANGUAGES` and `EXTENSIONS` in
`app/parser/registry.py`.

The response includes `has_syntax_errors`. It is `true` when the code does
not parse cleanly, for example a half-edited file or code sent with the wrong
extension (Rust source in a `.java` file). Symbols are still returned, but may
be incomplete or empty.

The language pack downloads each grammar the first time it is used and caches
it locally, so the first request for a new language needs internet access.

Example request:

```json
{
    "file_path": "example.py",
    "source_code": "class User:\n    pass"
}