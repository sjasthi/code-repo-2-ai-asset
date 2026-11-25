# Code Dependency Graph

Map how a codebase fits together. Import a GitHub repository or upload source
files, and Code Dependency Graph parses them with tree-sitter and stores files,
classes, functions and their import and call relationships in Neo4j. You can
then search symbols, trace who-imports-what, and explore an interactive graph.

**Status:** MVP complete (FP10). See [MVP status and roadmap](docs/roadmap.md).

## Project Overview:
Code Dependency Graph is a web-based application designed to help developers understand the structure and relationships within a software codebase.

When working with large software projects, it can be difficult to understand how different files, classes, functions, and methods connect to one another. Developers may need to manually search through multiple files to identify dependencies and understand how changes in one part of a project could affect another.

Our application addresses this challenge by analyzing source code repositories and transforming their contents into structured, searchable dependency information.

Users can import a public GitHub repository or upload individual source files and ZIP folders. The application parses supported source code, extracts symbols and dependency relationships, and stores the information in a Neo4j graph database.

Users can then search for specific code elements, investigate file dependencies, and visually explore the codebase through an interactive graph.

## Features

- **Bring code in:** import any public GitHub repository (optionally a branch),
  or upload files or a ZIP.
- **Symbol index:** classes, functions, methods and variables for Python,
  JavaScript, TypeScript, Go, Rust, Java, C, C++ and Ruby.
- **Dependency graph:** file-to-file `IMPORTS`, `CALLS` and `CONTAINS`
  relationships for Python, JavaScript and TypeScript, stored in Neo4j.
- **Search:** ranked symbol search (exact > prefix > contains > typo-tolerant)
  and file path search, in 7–60 ms over 12K symbols.
- **Dependencies view:** what a file imports, what imports it, and what it calls.
- **Interactive graph:** Cytoscape.js. Center on a file with 1–3 hops,
  highlight neighbors, filter node types, export PNG, and share views by URL.
  Stays responsive with thousands of nodes.

## Technology Stack
Our application uses a combination of frontend, backend, database, and code-analysis technologies. Each technology serves a specific purpose in processing source code, storing dependency information, and presenting the results to users.

- ##React:## Allows us to create an interactive application with separate pages for uploads, search, dependencies, and graph visualization
- ##TypeScript:## Helps organize application data and catch potential type-related errors, especially when handling API responses, files, and graph information.
- ##CytoScape.js:## Provides graph visualization features such as zooming, panning, selecting nodes, and exploring relationships between code elements.
- ##Python:## Provides a strong ecosystem for processing source code, working with files, and integrating with databases.
- ##FastAPI:## Allows the frontend to communicate with the backend through HTTP requests and provides automatically generated API documentation.
- ##Tree-sitter:## Helps extract classes, functions, methods, variables, and other code elements instead of treating source code as plain text.
- ##NEO4j:## Our project focuses on connections between code elements. Neo4j's graph database model makes it suitable for representing and querying relationships between files, classes, and functions.

## Architecture

```
┌──────────────────────────┐     ┌──────────────────────────────────────┐     ┌──────────┐
│ React + TypeScript (Vite)│────►│ FastAPI                              │────►│ Neo4j 5+ │
│ Upload · Search ·        │ HTTP│  parser/        tree-sitter symbols  │Bolt │          │
│ Dependencies · Graph     │◄────│  dependencies/  imports, calls       │◄────│          │
└──────────────────────────┘ JSON│  database/      graph, search, view  │     └──────────┘
                                 │  repositories/  GitHub ZIP importer  │──► api.github.com
                                 └──────────────────────────────────────┘
```

Graph model:

```
(:File)-[:IMPORTS]->(:File)
(:File)-[:CONTAINS]->(:Class | :Function | :Method | :Variable)
(:File)-[:CALLS]->(:Function {name})
```

Why it's built this way: [Architecture Decision Records](docs/adr.md).

## Quick start

**Requires:** Python 3.10+, Node.js 18+, Neo4j 5+ running locally.

```bash
# Backend
cd Final_Project/backend
python -m venv venv
venv\Scripts\Activate.ps1            # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
# create .env with NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD (see docs/developer-guide.md)
uvicorn app.main:app --reload        # http://localhost:8000/docs

# Frontend (second terminal)
cd Final_Project/frontend
npm install
npm run dev                          # http://localhost:5173
```

Open http://localhost:5173, go to **Upload → GitHub repository**, paste
`https://github.com/psf/requests`, and click **Import repository**. Then try
**Search** and **Graph**.

## Performance

| MVP target | Measured |
|---|---|
| 50K-line codebase parsed in < 2 min | **86.8 s** |
| Search < 500 ms | **≤ 60 ms** (12K symbols) |
| Graph with 5K+ nodes | API returns 8.5K nodes in **715 ms** |

Details and how to reproduce: [Benchmarks](docs/benchmarks.md).

## Documentation

| | |
|---|---|
| [User Guide](docs/user-guide.md) | Using the app, page by page |
| [Developer Guide](docs/developer-guide.md) | Setup, code layout, data model, testing, CI |
| [API Reference](docs/api.md) | Every endpoint (live docs at `/docs`) |
| [Deployment Guide](docs/deployment.md) | Bare metal, Docker, cloud, security checklist |
| [Architecture Decisions](docs/adr.md) | ADR-001 to ADR-012 |
| [Benchmarks](docs/benchmarks.md) | Final performance results |
| [Roadmap](docs/roadmap.md) | Known issues, technical debt, v2/v3 |
| [User Testing](docs/user-testing.md) | Session plan and report template |

## Testing

```bash
cd Final_Project/backend && python -m pytest     # 139 tests; Neo4j tests skip if it's down
cd Final_Project/frontend && npm test            # 41 tests
```

## Known limitations

- Imports between *uploaded* files aren't linked yet. Use GitHub import for full import graphs.
- GitLab and private repositories aren't supported yet.
- Function calls are matched by name, so same-named functions can be conflated.
- `.tsx` files with JSX can lose symbols.
- No authentication. Run it on a trusted network only.

Full list: [Roadmap › Known issues](docs/roadmap.md#known-issues).

## Project brief

Build a tool that creates a dependency graph for a software codebase, using
Neo4j.

- Accept source code from a GitHub repository, a GitLab repository, a local
  folder, or an uploaded ZIP file.
- Analyze relationships and dependencies within the code.
- Represent the dependency information using Neo4j or another appropriate graph technology.
- Provide useful ways to visualize and navigate the dependency graph.
- Build a code symbol index as well.
- Allow users to explore relationships within the codebase.

**Primary goals / artifacts**

1. Code Dependency Graph
2. Code Symbol Index
3. Code Index
4. UI to navigate and explore these indexes

Iteration plan: [FP_iteration_plan.md](FP_iteration_plan.md) · Research:
[RESEARCH.md](RESEARCH.md)

## License

[MIT](LICENSE)
