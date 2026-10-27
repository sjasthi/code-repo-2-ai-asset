# Code Dependency Graph - Frontend

React + TypeScript (Vite) UI for the FastAPI backend.

## Run

1. Start Neo4j and the backend (from `backend/`):

       uvicorn app.main:app --reload

2. Start the frontend (from `frontend/`):

       npm install
       npm run dev

   Open http://localhost:5173.

The backend URL is read from `VITE_API_URL` (see `.env.example`, default `http://localhost:8000`).

## Pages

| Route           | What it does                                              | Backend endpoints                                    |
| --------------- | --------------------------------------------------------- | ---------------------------------------------------- |
| `/upload`       | Upload source files, or import a GitHub repository        | `POST /dependencies/analyze`, `POST /repositories/import` |
| `/search`       | Search symbols or files                                   | `GET /search/symbols`, `GET /search/files`           |
| `/dependencies` | Show what a file imports and which files import it        | `GET /dependencies/imports`, `GET /dependencies/imported-by` |

The header shows live API and Neo4j status (`/health`, `/health/neo4j`).

## Structure

    src/api/         typed API client and response types
    src/hooks/       useApiStatus (health polling)
    src/components/  Layout, FileUploader, RepositoryImport, shared bits
    src/pages/       one component per route
