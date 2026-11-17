# Roadmap, Known Issues & Technical Debt

State at the end of FP10 (2026-11-17), and what comes next.

## Where the MVP stands

| Original goal | Status |
|---|---|
| Input: GitHub repository | ✅ Public repos via `/repositories/import` |
| Input: GitLab repository | ❌ Not started |
| Input: local folder | 🟡 Via ZIP upload, but imports between uploaded files aren't linked |
| Input: uploaded ZIP | 🟡 Same limitation as local folder |
| Dependency graph in Neo4j | ✅ Python, JS, TS. Symbols only for Go/Rust/Java/C/C++/Ruby |
| Code symbol index | ✅ Ranked and fuzzy search, 7–60 ms |
| Code (file) index | ✅ File path search |
| UI to explore | ✅ Upload, Search, Dependencies, interactive Graph |
| 50K lines in < 2 min | ✅ 86.8 s |
| Graph responsive at 5K+ nodes | ✅ API 715 ms for 8.5K nodes. Grouped layout in the UI |

## Known issues

Ordered by user impact.

| # | Issue | Impact | Where | Fix |
|---|---|---|---|---|
| K1 | Imports between **uploaded** files don't create `IMPORTS` edges. The resolver checks paths on disk under `backend/sample_code/`, and uploads are never written to disk | Uploads and ZIPs give a graph with no import links | `main.py` `PROJECT_ROOT`, `resolver.py`, `FileUploader.tsx` | Server-side ZIP endpoint (v2.1) |
| K2 | `.tsx` parsed with the TypeScript grammar. JSX causes `has_syntax_errors` and later symbols are dropped | React projects lose symbols | `parser/registry.py`, `typescript_parser.py` | Use the TSX grammar for `.tsx` |
| K3 | `CALLS` matched by name only | False "called by" results | `graph_builder.store_call` | Resolve via imports (v2.2) |
| K4 | Import of a ~50K-line repo blocks the HTTP request for about 90 s | Proxy timeouts, no progress shown | `main.import_github_repository` | Background jobs (v2.1) |
| K5 | `.tsx` missing from the file picker's `accept` list (drag-and-drop works) | Minor UX | `FileUploader.tsx` | One-line fix |
| K6 | Go/Rust/Java/C/C++/Ruby have symbols but no imports or calls | Partial graphs for those repos | `dependencies/extractor.py` | v2.3 |
| K7 | Indexes are created only at API startup | Search breaks if Neo4j starts after the API | `main.lifespan` | Retry or create lazily |

## Technical debt

| Item | Why it matters | Effort |
|---|---|---|
| **One Cypher query per relationship** in `DependencyGraphBuilder` | 98% of import time. Batching with `UNWIND` should cut storage several-fold | M |
| **`github_importer.py` at 15% coverage** and `/repositories/import` untested | Most security-sensitive code (archive handling) is least tested | M |
| **No CI** | Commit `ea987b5` replaced `search.py` with React code and broke the API, and nothing caught it. A proposed workflow is in the [Developer Guide](developer-guide.md#continuous-integration-proposed) | S |
| Hard-coded CORS origins and `PROJECT_ROOT` | Blocks deployment without code edits | S |
| `/health/neo4j` and `/symbols` open a new driver per call | About 2 s each on Windows. Health is polled every 15 s | S |
| `/symbols` is unpaginated | Can return the whole graph | S |
| `graph_queries.py` has unused queries (`DEPENDENCY_CHAIN`, `FILE_CALLS`, `GRAPH_SUMMARY`) | Dead code. Its `FILE_CALLS` references an undefined `r` and would fail if used (`graph_view.py` has its own working copy) | S |
| Response types duplicated in Pydantic and TypeScript | Drift risk | S (generate from OpenAPI) |
| No structured logging or metrics | Hard to operate | M |
| Orphan name-only `Function` nodes after repository deletes | Slow graph growth | S |
| `requirements.txt` leaves `neo4j` and `python-dotenv` unpinned | Unreproducible installs | S |
| `frontend/.env` is committed despite `.gitignore` | Harmless today (only `VITE_API_URL`) but invites committing secrets | S |
| Starlette `httpx` deprecation warning in tests | Will break on a future Starlette upgrade | S |
| React Router v7 future-flag warnings | Upgrade prep | S |
| Backend README still describes the FP3 pipeline in its Architecture section | Misleading for new developers | S |

## v2: Finish the brief and harden (next 2 iterations)

**v2.1 Inputs & throughput**
- `POST /repositories/upload`: a server-side ZIP and folder import that runs
  the GitHub pipeline, which fixes K1 and ADR-011.
- Background import jobs with progress (`202` + `GET /jobs/{id}`), which fixes K4.
- Batched Neo4j writes with `UNWIND`. Target: 50K lines in < 30 s.
- `tests/benchmark_import.py` so the 50K-line measurement is repeatable.

**v2.2 Accuracy**
- TSX grammar for `.tsx` (K2).
- Resolve calls through imports before falling back to the name (K3).
- Optional external-package nodes (`(:Package)`) for a third-party dependency view.

**v2.3 Sources & languages**
- **GitLab** import (gitlab.com and self-hosted), which is in the original brief.
- Private repos via a personal access token, which also raises GitHub rate limits.
- Dependency extraction for Go and Java first, based on likely demand.

**v2.4 Operations**
- CI (tests, typecheck, build) on every push.
- Configurable CORS, env-based settings module.
- Dockerfiles and compose committed and tested (see [Deployment](deployment.md)).
- Structured JSON logs and request timing.
- Authentication (at least a shared token or proxy auth) before any shared deployment.

## v3: Insight features

- **Change impact:** "if I change this file or function, what else is
  affected?" (transitive imported-by and callers), with a diff or PR input.
- **Cycle and hotspot detection:** import cycles, highly coupled modules,
  and fan-in/fan-out rankings.
- **Incremental re-analysis:** only re-parse changed files, using commit SHA
  or file hashes.
- **Repository comparison:** how the dependency structure changed between two
  branches or commits.
- **Inheritance and type edges:** `EXTENDS` and `IMPLEMENTS`, and type
  references where grammars allow.
- **Editor integration:** a VS Code extension that opens the graph for the current file.
- **Saved views and annotations** shared via URL (building on today's query-string state).

## Inputs for planning

Prioritization should also use the [User Testing](user-testing.md) results
once the sessions are run. The v2 order above is the team's engineering
judgment only.
