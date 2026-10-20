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
```

## Dependency Endpoints

These endpoints support Python and JavaScript/TypeScript (`language` query
parameter, default `python`). All except `/dependencies/parse` need Neo4j running.

### POST /dependencies/parse

Returns a file's imports and function calls without storing anything.

### POST /dependencies/analyze

Stores the file in Neo4j with its relationships:

- `IMPORTS` to local files it imports
- `CALLS` to functions it calls
- `CONTAINS` to the classes, functions, methods and variables defined in it

Re-analysing a file removes symbols that no longer exist (or moved lines)
and keeps the rest.

### GET /dependencies/imports?file_path=...

What files does this file import?

### GET /dependencies/imported-by?file_path=...

What files import this file?

### GET /dependencies/class-imported-by?class_name=...

What files import the file that defines this class? Imports are tracked per
file, so a file is listed if it imports the class's file, even if it uses a
different name from it. Both files must have been analysed first.

## Search Endpoints

Search covers every symbol stored in Neo4j by `/dependencies/analyze` or
`/repositories/import`. Interactive docs with every parameter are at
`http://localhost:8000/docs` while the server is running.

| Endpoint | Searches |
|---|---|
| `GET /search/symbols?q=...` | All symbols. Filter with `type` (repeatable: `class`, `function`, `method`, `variable`) and `file_path`. |
| `GET /search/classes?q=...` | Classes |
| `GET /search/functions?q=...` | Functions and methods |
| `GET /search/files?q=...` | File paths (case-insensitive substring) |

Common parameters:

- `q` (required): the name, or part of it. Several words must all match.
- `fuzzy` (default `true`, symbol endpoints only): also match typos, e.g.
  `UserServce` finds `UserService`. Words of 4 characters or fewer allow one
  typo, longer words allow two.
- `limit` (1-100, default 20) and `offset` (default 0): pagination.

Results are ranked by how the name matches the query, then by full-text
relevance. Each result's `match` field says which tier it is in:

1. `exact`: the whole name equals the query (case-insensitive)
2. `prefix`: the name starts with the query
3. `contains`: the query appears inside the name, e.g. `service` in `OrderService`
4. `fuzzy`: matched only by allowing typos

Example: `GET /search/symbols?q=user&limit=2`

```json
{
    "query": "user",
    "total": 6,
    "limit": 2,
    "offset": 0,
    "results": [
        {"type": "class", "name": "User", "file_path": "models.py", "line": 10, "score": 3.1, "match": "exact"},
        {"type": "class", "name": "UserService", "file_path": "models.py", "line": 1, "score": 2.4, "match": "prefix"}
    ]
}
```

`total` is the number of matches across all pages. An empty or whitespace-only
`q` returns `400`; invalid `limit`, `offset` or `type` values return `422`.

### Indexes

The API creates these on startup (see `app/database/schema.py`); startup
continues without them if Neo4j is not running:

- `symbol_name_fulltext`: full-text (Lucene) index on `name` for `Class`,
  `Function`, `Method` and `Variable`, used for ranked and fuzzy search
- `file_path_text`: text index on `File.path` for file search
- `class_name`, `function_name`, `method_name`, `variable_name`: range indexes
  for exact name lookups (e.g. `MERGE (:Function {name})` when storing calls)

### Testing and performance

- `tests/test_search.py`: unit tests with a fake database
- `tests/test_search_neo4j.py`: runs real searches against Neo4j; skipped when
  Neo4j is not running
- `python -m tests.benchmark_search`: loads 12,000 symbols, times searches
  through the API against the 500 ms target, then deletes its data

Measured on a local Neo4j 2026.09 with 12,000 symbols: 7-17 ms per request.

