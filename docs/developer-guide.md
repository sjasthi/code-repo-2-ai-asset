# Developer Guide

Everything needed to set up, understand and change the codebase.

## Prerequisites

| Tool | Version used | Minimum |
|---|---|---|
| Python | 3.14.3 | 3.10 (`X \| None` type syntax) |
| Node.js | 24.14 | 18 (Vite 5) |
| Neo4j | 2026.09 | 5.x (multi-label full-text and `TEXT` indexes) |

Neo4j Desktop or a Docker `neo4j:5` container are both fine for local work.

## First-time setup

```bash
git clone <repo-url>
cd code-repo-2-ai-asset/Final_Project
```

**Backend**

```bash
cd backend
python -m venv venv
venv\Scripts\Activate.ps1                       # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env` (git-ignored):

```env
NEO4J_URI=neo4j://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j
```

> **Windows:** If `Activate.ps1` is blocked, run
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once. You can also skip
> activation and call `venv\Scripts\python.exe` directly.

**Frontend**

```bash
cd ../frontend
npm install
cp .env.example .env                            # VITE_API_URL=http://localhost:8000
```

## Running locally

Run each in its own terminal:

```bash
# 1. Neo4j: start it from Neo4j Desktop, or:
docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/your-password neo4j:5

# 2. Backend (from Final_Project/backend; the working directory matters, see below)
uvicorn app.main:app --reload                   # http://localhost:8000/docs

# 3. Frontend (from Final_Project/frontend)
npm run dev                                     # http://localhost:5173
```

The header shows green **API** and **Neo4j** badges when everything is connected.

**Optional sample data:** `python -m migrations.load_sample_data` stores a small
JavaScript example in Neo4j. You can also upload the files in
`backend/sample_code/` on the Upload page.

## Repository layout

```
.
├── README.md                     project overview (start here)
├── FP_iteration_plan.md          FP1–FP10 plan
├── RESEARCH.md                   competitive analysis (FP2)
├── Preliminary Design Architecture-Tools   FP2 design notes
├── docs/                         FP10 documentation (this folder)
└── Final_Project/
    ├── backend/
    │   ├── app/
    │   │   ├── main.py           FastAPI app: every route lives here
    │   │   ├── parser/           tree-sitter symbol extraction, one module per language
    │   │   │   └── registry.py   extension → language → extractor (single source of truth)
    │   │   ├── dependencies/
    │   │   │   ├── extractor.py  imports and calls from a syntax tree
    │   │   │   └── resolver.py   import string → local file path
    │   │   ├── database/
    │   │   │   ├── neo4j.py      connection wrapper (reads .env)
    │   │   │   ├── schema.py     constraints and indexes, created at startup
    │   │   │   ├── graph_builder.py  writes files, symbols, IMPORTS/CALLS/CONTAINS
    │   │   │   ├── graph_queries.py  read queries for /dependencies/*
    │   │   │   ├── search.py     SymbolSearch (FP6) and DependencySearch (FP9)
    │   │   │   └── graph_view.py nodes/edges for /graph (FP8)
    │   │   └── repositories/
    │   │       └── github_importer.py  safe ZIP download and unpack
    │   ├── tests/                pytest suite and benchmark_*.py scripts
    │   ├── migrations/           one-off data loaders
    │   └── sample_code/          fixtures; also the import-resolution root for /dependencies/*
    └── frontend/
        └── src/
            ├── api/              typed fetch client (client.ts) and response types (types.ts)
            ├── components/       Layout, FileUploader, RepositoryImport, GraphCanvas, ...
            ├── pages/            one component per route
            ├── graph/            Cytoscape model, styling, clustered layout, interactions
            └── hooks/            useApiStatus (health polling)
```

## How it works

### Analysis pipeline

```
source file ──► registry.detect_language(path)
            ──► tree-sitter parse ──► symbol extractor ──► [{type, name, file_path, line}]
            ──► DependencyExtractor ──► [{type: import|call, target, line}]
            ──► ImportResolver ──► resolved_target (local path or None)
            ──► DependencyGraphBuilder ──► Neo4j
```

- **Symbols:** Python, JavaScript and TypeScript use hand-written extractors
  (`python_symbols.py`, etc.). Go, Rust, Java, C, C++ and Ruby share
  `tags_symbols.py`, which runs tree-sitter "tags" queries from
  `tree-sitter-language-pack`.
- **Dependencies:** only Python, JavaScript and TypeScript. The other languages
  get symbols but no imports or calls.
- **Resolution:** Python absolute imports resolve from the project root, and
  relative imports resolve from the importing file's package. JS/TS resolves
  only relative specifiers (`./x`) and tries `.js/.jsx/.ts/.tsx` and `index.*`.
  Package imports (`react`, `os`) stay unresolved and produce no edge.
  The resolver checks **files on disk**: for `/repositories/import` that is the
  unpacked temp directory, and for `/dependencies/*` it is `backend/sample_code/`.

### Graph data model

```
(:File {path, language})
   ├─[:CONTAINS]──► (:Class|:Function|:Method|:Variable {name, file_path, line})
   ├─[:IMPORTS {line}]──► (:File)
   └─[:CALLS {line}]──► (:Function {name})      ← keyed by name only
```

- Symbol identity is `(label, name, file_path, line)`, enforced by constraints.
- `CALLS` targets are `MERGE (:Function {name})` with no file. Calls aren't
  linked to a specific definition. See [ADR-007](adr.md#adr-007-calls-are-matched-by-function-name).
- File paths from GitHub imports are prefixed `github.com/<owner>/<repo>/`.
  Uploaded files keep their own path. `/graph/projects` groups on that prefix.

### Indexes (`schema.py`)

| Name | Kind | Used by |
|---|---|---|
| `file_path_unique`, `class_unique`, ... | uniqueness constraints | `MERGE` correctness |
| `symbol_name_fulltext` | Lucene full-text on `name` | `/search/symbols` ranking and fuzzy |
| `file_path_text` | text index on `File.path` | `/search/files` |
| `class_name`, `function_name`, ... | range | exact-name lookups, `store_call` |

### Database connection

`main.get_database()` keeps **one shared `Neo4jConnection`** for the process,
created lazily and closed on shutdown. Opening a driver per request cost about
2 s on Windows. Routes take it via `Depends(get_database)`, so tests override it
with `app.dependency_overrides`. (`/health/neo4j` and `/symbols` still open their
own connection, which is listed as tech debt.)

### Frontend

- `api/client.ts` is the only place that calls `fetch`. It throws `ApiError`
  with the server's `detail` message, and pages render it via `ErrorMessage`.
- ZIP uploads are unpacked **in the browser** with JSZip, and each file is sent
  to `/dependencies/analyze` one by one.
- `GraphPage` is lazy-loaded because Cytoscape is about 460 kB. Large graphs
  switch to `graph/clusterLayout.ts` and reduce label rendering.
- Graph URLs are shareable: `/graph?file=<path>&depth=2&symbols=1&calls=1&q=<highlight>`.

## Common tasks

### Add a symbol language supported by `tree-sitter-language-pack`

1. In `app/parser/registry.py`, add the language to `TAGS_LANGUAGES` and its
   extensions to `EXTENSIONS` (and any aliases).
2. Add a case to `tests/test_tags_parser.py`.
3. Document it in the language table in [api.md](api.md#post-parse).
4. To accept it on the Upload page, also add it to `LANGUAGE_BY_EXTENSION` in
   `frontend/src/api/client.ts` and to the `accept` list in `FileUploader.tsx`.

### Add dependency extraction for a language

Extend `DependencyExtractor.extract` and `ImportResolver.resolve`, then allow
the language in the `detected_language in (...)` check in
`main.import_github_repository`. Add tests in `tests/test_dependencies.py` and
`tests/test_resolver.py`.

### Add an endpoint

1. Add the route and Pydantic response model to `app/main.py`, and inject the
   database with `Depends(get_database)`.
2. Put Cypher in `app/database/`, not in the route.
3. Test with `TestClient` and a fake database, following `tests/test_search.py`.
4. Add a method to `frontend/src/api/client.ts` and its types to `types.ts`.
5. Document it in [api.md](api.md).

## Testing

| Command (from the package folder) | What |
|---|---|
| `python -m pytest` | Backend suite (139 tests). Neo4j-backed tests skip themselves if Neo4j is down |
| `python -m pytest --cov=app` | With coverage (currently 73%) |
| `npm test` | Frontend Vitest + Testing Library (41 tests) |
| `npm run typecheck` | TypeScript, no emit |
| `npm run build` | Typecheck + production build |
| `python -m tests.benchmark_search` | Search latency vs. the 500 ms target ([results](benchmarks.md)) |
| `python -m tests.benchmark_dependencies` | Extractor throughput |

Conventions:

- Unit tests use a fake database object that records queries and returns
  canned rows. Only `test_neo4j.py` and `test_search_neo4j.py` hit a real
  database, and they clean up after themselves.
- Benchmarks write under a reserved prefix (`__benchmark__/`) and delete it at the end.
- Never point tests at a database you care about without checking their cleanup.

## Continuous integration (proposed)

There is no CI yet. A minimal GitHub Actions workflow, `.github/workflows/ci.yml`,
which has **not been run**:

```yaml
name: CI
on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      neo4j:
        image: neo4j:5
        env: {NEO4J_AUTH: neo4j/ci-password}
        ports: ["7687:7687"]
        options: >-
          --health-cmd "cypher-shell -u neo4j -p ci-password 'RETURN 1'"
          --health-interval 10s --health-retries 10
    env:
      NEO4J_URI: neo4j://localhost:7687
      NEO4J_USERNAME: neo4j
      NEO4J_PASSWORD: ci-password
    defaults: {run: {working-directory: Final_Project/backend}}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12"}
      - run: pip install -r requirements.txt
      - run: python -m pytest --cov=app

  frontend:
    runs-on: ubuntu-latest
    defaults: {run: {working-directory: Final_Project/frontend}}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: {node-version: "22", cache: npm, cache-dependency-path: Final_Project/frontend/package-lock.json}
      - run: npm ci
      - run: npm test
      - run: npm run build
```

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `SyntaxError` on `import app.main` | A non-Python file was committed over a `.py` module. Check `git log -- <file>` |
| Neo4j badge red, `/health/neo4j` shows an auth or connection error | Check `.env` values and that Neo4j is running on the Bolt port |
| Search returns nothing right after setup | Indexes are created at API startup. Restart the API after Neo4j is up |
| Uploaded files have no import edges | Uploads resolve imports against `backend/sample_code/` (known issue, see [Roadmap](roadmap.md#known-issues)). Import a GitHub repo for full edges |
| `.tsx` file shows syntax errors or missing symbols | `.tsx` uses the TypeScript grammar, not TSX (known issue) |
| Repository import fails with "rate limit" | Unauthenticated GitHub API allows 60 requests per hour per IP. Wait, or add token support (roadmap) |
| First Go/Rust/... parse is slow or fails offline | The grammar downloads on first use. Needs internet once |
| Browser CORS error | Frontend isn't on `localhost:5173`. Add its origin in `main.py` |
