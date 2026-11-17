# Performance Benchmarks (FP10 final)

Measured **2026-11-17** on the development machine below. Every number on this
page comes from a script you can rerun (see [How to reproduce](#how-to-reproduce)).

| | |
|---|---|
| OS | Windows 11 Home (10.0.26200) |
| Python | 3.14.3 |
| Node.js | 24.14.1 |
| Neo4j | 2026.09.0 Enterprise, local, default memory settings |
| Graph at test time | 4,141 nodes, 95 files (restored after every run) |

## Results against MVP targets

| Target (from FP plan) | Measured | Result |
|---|---|---|
| Parse a 50K-line codebase in < 2 minutes | **86.8 s** end to end (50,952 lines, 149 files) | ✅ Pass, 28% headroom |
| Search requests < 500 ms | **59.5 ms** worst case over 12,000 symbols | ✅ Pass |
| Graph responsive with 5K+ nodes | API returns 8,472 nodes in **715 ms**. The UI renders 2,841 nodes in about 4 s (FP8 measurement) | ✅ Pass, see notes |

## 1. End-to-end import (50K lines)

Runs the same steps as `POST /repositories/import` (symbol extraction,
dependency extraction, import resolution, Neo4j storage), minus the GitHub
download. The corpus was 50,952 lines of real-world Python from installed
packages (FastAPI, Starlette, httpx, httpcore, AnyIO, h11, Click, Uvicorn,
python-dotenv, idna, Pygments).

| Stage | Time | Output |
|---|---|---|
| Parse + extract + resolve | 1.7 s | 6,897 symbols, 10,311 dependencies |
| Store in Neo4j | 85.1 s | 6,897 symbols, 9,618 relationships |
| **Total** | **86.8 s** | |

**Finding:** 98% of the time goes to Neo4j writes. `DependencyGraphBuilder`
sends one Cypher query per symbol, import and call. Batching them with
`UNWIND $rows` in one transaction per file (or per repository) is the biggest
remaining optimization. It is tracked in the [Roadmap](roadmap.md). Parsing
itself is fast at roughly 30,000 lines per second.

The GitHub download adds network time on top, bounded by the importer's
45-second timeout and 30 MB limit.

## 2. Dependency extraction scaling

`python -m tests.benchmark_dependencies` (synthetic single file, Python):

| Lines | Dependencies | Time |
|---|---|---|
| 10,000 | 10,000 | 0.12 s |
| 50,000 | 50,000 | 0.62 s |
| 100,000 | 100,000 | 1.34 s |

Scaling is linear.

## 3. Symbol search

`python -m tests.benchmark_search` loads 12,000 symbols in 600 files (2.5 s),
runs each query 10 times through the HTTP API, then deletes its data.

| Query kind | Query | Results | Median | Max |
|---|---|---|---|---|
| exact | `UserService` | 60 | 18.0 ms | 59.5 ms |
| prefix | `Payment` | 601 | 23.5 ms | 45.5 ms |
| substring | `repository` | 1,200 | 22.7 ms | 28.1 ms |
| typo | `CustmerHandlr` | 60 | 15.0 ms | 19.2 ms |
| short | `id` | 106 | 10.2 ms | 11.1 ms |
| two words | `order manager` | 60 | 14.5 ms | 22.3 ms |
| page 10 | `user` | 630 | 13.0 ms | 14.7 ms |
| files | `module_42` | 11 | 7.5 ms | 23.1 ms |

**Slowest request: 59.5 ms against the 500 ms target.**

## 4. Graph API (`GET /graph`)

Same 50K-line corpus as section 1, median of 3 runs, `limit=5000`:

| Options | Nodes | Edges | Median |
|---|---|---|---|
| Files only | 196 | 698 | 72 ms |
| + symbols | 7,089 | 7,591 | 432 ms |
| + symbols + calls | 8,472 | 11,834 | 715 ms |

Rendering is the bottleneck, not the API. From FP8: `psf/requests` with
everything on (2,841 nodes) renders in about 4 s. Above 400 nodes the UI
switches to the grouped-by-file layout. Above 1,500 nodes it hides labels until
you zoom in and pans using a snapshot. An 8K-node render was not timed in a
browser for FP10.

## 5. Frontend bundle

`npm run build` (Vite 5):

| Chunk | Size | Gzip |
|---|---|---|
| `index` (app shell, all pages except Graph) | 187.3 kB | 60.6 kB |
| `GraphPage` (lazy, includes Cytoscape) | 460.5 kB | 148.4 kB |
| `jszip` (lazy, only when a ZIP is uploaded) | 97.6 kB | 30.3 kB |
| CSS | 10.2 kB | 2.7 kB |

First load is about 64 kB gzipped. Cytoscape and JSZip load only when needed.

## 6. Test suite

| Suite | Result | Time |
|---|---|---|
| Backend (pytest, Neo4j running) | 139 passed | ~18–25 s |
| Frontend (Vitest) | 41 passed, 6 files | ~3 s |
| Frontend typecheck (`tsc -b`) | clean | |

Backend line coverage is **73%**. Gaps: `app/repositories/github_importer.py`
(15%) and `app/main.py` (60%, mainly the `/repositories/import` handler). See
the [Roadmap](roadmap.md#technical-debt).

## How to reproduce

From `Final_Project/backend` with the venv active and Neo4j running:

```bash
python -m tests.benchmark_dependencies      # section 2, no database needed
python -m tests.benchmark_search            # section 3, cleans up after itself
python -m pytest --cov=app                  # section 6
```

From `Final_Project/frontend`:

```bash
npm run build                               # section 5
npm test
```

Sections 1 and 4 used a one-off script that runs the import pipeline over
installed packages under a temporary path prefix, then deletes everything it
created. Turning it into `tests/benchmark_import.py` is on the roadmap so the
measurement can be repeated.
