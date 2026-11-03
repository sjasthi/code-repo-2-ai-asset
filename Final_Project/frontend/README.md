# Code Dependency Graph - Frontend

React + TypeScript (Vite) UI for the FastAPI backend.

## Run

1. Start Neo4j and the backend (from `backend/`):

       uvicorn app.main:app --reload

2. Start the frontend (from `frontend/`):

       npm install
       npm run dev

   Open http://localhost:5173.

Run the component tests with `npm test` (Vitest + React Testing Library).

The backend URL is read from `VITE_API_URL` (see `.env.example`, default `http://localhost:8000`).

## Pages

| Route           | What it does                                              | Backend endpoints                                    |
| --------------- | --------------------------------------------------------- | ---------------------------------------------------- |
| `/upload`       | Upload source files or a ZIP, or import a GitHub repository | `POST /dependencies/analyze`, `POST /repositories/import` |
| `/search`       | Search symbols or files                                   | `GET /search/symbols`, `GET /search/files`           |
| `/dependencies` | Show what a file imports and which files import it        | `GET /dependencies/imports`, `GET /dependencies/imported-by` |
| `/graph`        | Interactive dependency graph (Cytoscape.js)               | `GET /graph`, `GET /graph/projects`                  |

The header shows live API and Neo4j status (`/health`, `/health/neo4j`).

## Structure

    src/api/         typed API client and response types
    src/hooks/       useApiStatus (health polling)
    src/components/  Layout, FileUploader, RepositoryImport, shared bits
    src/pages/       one component per route
    src/graph/       graph model, Cytoscape styling/highlighting, clustered layout

## Graph page

- Pick a repository (or uploaded files), or center on one file with 1-3 import hops.
- Optionally include classes/functions/variables and function calls.
- Click a node: what it imports turns teal, what imports it turns orange, the
  rest fades; the side panel lists them as buttons for keyboard navigation.
- "Highlight" marks nodes whose name or path matches, as you type. The
  Search page's "Graph" links open the graph centered and highlighted.
- Type checkboxes hide node kinds; zoom/fit/re-layout/PNG buttons on the canvas.
- Large graphs (over 400 nodes) use a "Grouped by file" layout: files are laid
  out first and their symbols spiral around them. Over 1,500 nodes, labels
  show only when zoomed in and panning uses a snapshot, to keep it smooth.
  `psf/requests` with everything on (2,841 nodes) renders in about 4 s.
- In dev mode the Cytoscape instance is on `window.cy` for debugging.
