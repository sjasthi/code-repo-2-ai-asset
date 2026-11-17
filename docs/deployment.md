# Deployment Guide

How to run Code Dependency Graph outside a developer laptop. For local
development, see the [Developer Guide](developer-guide.md).

> **Status:** The bare-metal steps match what the team runs today. The Docker
> files below are reference configurations. They are **not in the repo yet and
> have not been built or tested**. Try them on a staging machine first.

## What you are deploying

```
Browser ──► Static frontend (React build, any web server/CDN)
   │
   └──────► Backend API (FastAPI + Uvicorn, port 8000) ──► Neo4j 5+ (Bolt, port 7687)
                    │
                    └──► api.github.com (repository import)
                    └──► grammar downloads (first use of Go/Rust/Java/C/C++/Ruby)
```

| Component | Runtime | State |
|---|---|---|
| Frontend | Static files from `npm run build` | none |
| Backend | Python 3.12+ (developed on 3.14) | none. Temp files only during imports |
| Neo4j | **5.x or 2025+** (uses multi-label full-text and `TEXT` indexes) | all graph data |

## Configuration

### Backend environment variables

Read from the environment, or from `Final_Project/backend/.env` via `python-dotenv`.

| Variable | Required | Example | Notes |
|---|---|---|---|
| `NEO4J_URI` | yes | `neo4j://localhost:7687` or `neo4j+s://xxxx.databases.neo4j.io` | |
| `NEO4J_USERNAME` | yes | `neo4j` | |
| `NEO4J_PASSWORD` | yes | | Keep in a secret store, never commit it |
| `NEO4J_DATABASE` | no | `neo4j` (default) | |

On startup the API creates its constraints and indexes
(`app/database/schema.py`). If Neo4j is down, the API still starts and logs
`Could not initialize Neo4j schema`. Restart the API once Neo4j is up so the
search indexes exist.

### Frontend build variable

| Variable | Default | Notes |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | **Baked in at build time.** Rebuild to change it |

### Code changes needed for a non-localhost deployment

These settings are hard-coded today, so a production deployment needs these edits:

1. **CORS origins.** `app/main.py` allows only `http://localhost:5173` and
   `http://127.0.0.1:5173`. Add your frontend origin, ideally from an env var
   such as `CORS_ORIGINS`. You can skip this if you serve the frontend and API
   from the same origin through a reverse proxy.
2. **`PROJECT_ROOT`.** `/dependencies/parse` and `/dependencies/analyze`
   resolve imports against `Path("sample_code")` relative to the working
   directory. Start Uvicorn from `Final_Project/backend`, or make this configurable.

## Option A: Bare metal / VM

### 1. Neo4j

Install Neo4j 5+ ([download](https://neo4j.com/deployment-center/)) or create a
managed **Neo4j AuraDB** instance. Note the URI, user and password.

Sizing: the 50K-line benchmark stored about 7K symbols and 10K relationships.
The default heap is plenty for a handful of repositories.

### 2. Backend

```bash
cd Final_Project/backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt

export NEO4J_URI=neo4j://db-host:7687 NEO4J_USERNAME=neo4j NEO4J_PASSWORD=...

uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --timeout-keep-alive 120
```

- Multiple workers are safe because each worker keeps its own pooled Neo4j driver.
- `POST /repositories/import` is synchronous and takes about 90 s for 50K
  lines. Set your proxy or load balancer read timeout to **at least 180 s**.
- Imports unzip into the OS temp directory (up to 100 MB per import). Make
  sure `/tmp` has room.
- Run Uvicorn under a supervisor (systemd, NSSM on Windows, or a PaaS process manager).

Example systemd unit:

```ini
[Unit]
Description=Code Dependency Graph API
After=network.target

[Service]
WorkingDirectory=/opt/cdg/Final_Project/backend
EnvironmentFile=/etc/cdg/backend.env
ExecStart=/opt/cdg/Final_Project/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=on-failure
User=cdg

[Install]
WantedBy=multi-user.target
```

### 3. Frontend

```bash
cd Final_Project/frontend
npm ci
VITE_API_URL=https://cdg.example.com/api npm run build
# upload dist/ to any static host: Nginx, S3 + CloudFront, Netlify, Azure Static Web Apps...
```

The app uses client-side routing (`/upload`, `/search`, `/dependencies`,
`/graph`). Configure the host to serve `index.html` for unknown paths.

### 4. Reverse proxy (single origin, no CORS change needed)

```nginx
server {
    listen 443 ssl;
    server_name cdg.example.com;

    root /var/www/cdg;                       # frontend dist/
    location / { try_files $uri /index.html; }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;   # strips /api
        proxy_read_timeout 180s;
        client_max_body_size 5m;
    }
}
```

Build the frontend with `VITE_API_URL=https://cdg.example.com/api`.

## Option B: Docker Compose (reference, untested)

`Final_Project/backend/Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY sample_code ./sample_code
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

`Final_Project/frontend/Dockerfile`:

```dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_API_URL=/api
RUN VITE_API_URL=$VITE_API_URL npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

`Final_Project/frontend/nginx.conf`:

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    location / { try_files $uri /index.html; }
    location /api/ {
        proxy_pass http://backend:8000/;
        proxy_read_timeout 180s;
    }
}
```

`Final_Project/docker-compose.yml`:

```yaml
services:
  neo4j:
    image: neo4j:5
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:?set NEO4J_PASSWORD}
    volumes: [neo4j-data:/data]
    healthcheck:
      test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "${NEO4J_PASSWORD}", "RETURN 1"]
      interval: 10s
      retries: 10

  backend:
    build: ./backend
    environment:
      NEO4J_URI: neo4j://neo4j:7687
      NEO4J_USERNAME: neo4j
      NEO4J_PASSWORD: ${NEO4J_PASSWORD}
    depends_on:
      neo4j: {condition: service_healthy}

  frontend:
    build: ./frontend
    ports: ["8080:80"]
    depends_on: [backend]

volumes:
  neo4j-data:
```

```bash
cd Final_Project
NEO4J_PASSWORD=change-me docker compose up --build
# open http://localhost:8080
```

Because nginx proxies `/api`, the browser sees a single origin and no CORS
change is needed. Also add a `.dockerignore` with `venv/`, `node_modules/`,
`.env` and `__pycache__/`, so local secrets and environments stay out of images.

## Option C: Managed cloud

The pieces map onto any cloud:

| Piece | AWS | Azure | GCP | Other |
|---|---|---|---|---|
| Neo4j | AuraDB (on AWS) or EC2 | AuraDB (on Azure) or VM | AuraDB (on GCP) or GCE | AuraDB Free for demos |
| Backend container | App Runner / ECS Fargate | Container Apps | Cloud Run | Render, Fly.io, Railway |
| Frontend | S3 + CloudFront | Static Web Apps | Cloud Storage + CDN | Netlify, Vercel |

Platform notes:

- **Request timeouts.** Cloud Run, App Runner and Container Apps cap request
  time, but the defaults allow the ~90 s import. Raise the limit if you import
  larger repos.
- **Neo4j AuraDB.** Use the `neo4j+s://` URI. Aura Free has node and
  relationship caps that a couple of mid-sized repositories can hit.
- **Secrets.** Inject `NEO4J_PASSWORD` from the platform's secret manager.
- **Outbound network.** The backend needs HTTPS egress to `api.github.com` and
  `codeload.github.com`. It also needs egress for grammar downloads the first
  time each Go/Rust/Java/C/C++/Ruby file is parsed. Otherwise, warm the cache
  in the image.

## Monitoring and logging

| Check | Endpoint | Healthy response |
|---|---|---|
| Liveness | `GET /health` | `{"status": "healthy"}` |
| Database | `GET /health/neo4j` | `{"status": "healthy", "neo4j": "connected"}` (always HTTP 200, so check the body) |

- Point the load balancer's health check at `/health`. Alert on `/health/neo4j`
  body `status != "healthy"`.
- Uvicorn writes access logs to stdout. The app logs schema-initialization
  failures through Python `logging` at `WARNING`. Ship stdout and stderr to your
  platform's log service.
- Structured request logging and metrics are not implemented yet (see
  [Roadmap](roadmap.md)).

## Security checklist

The API has **no authentication**. Before exposing it beyond a trusted network:

- [ ] Put it behind an authenticating proxy, VPN or IP allow-list.
- [ ] Restrict CORS to your frontend's origin.
- [ ] Rate-limit `POST /repositories/import`. Each call downloads up to 30 MB
      and holds a worker for up to 2 minutes, and it also spends the server's
      unauthenticated GitHub quota (60 requests/hour per IP).
- [ ] Remove or protect `GET /symbols`, which returns the whole graph unpaginated.
- [ ] Remember that `POST /repositories/import` **deletes and replaces** all
      data under the repository's prefix, and anyone who can call it can do this.
- [ ] Keep Neo4j off the public internet. Only the backend needs to reach it.
- [ ] `Final_Project/frontend/.env` is committed (it only contains
      `VITE_API_URL`). Never put secrets in `VITE_*` variables, because they
      ship in the browser bundle.

Already handled by the importer: HTTPS github.com URLs only, public repos only,
size and entry limits, path-traversal and symlink rejection. Imported code is
never executed.

## Backup and reset

All state lives in Neo4j:

```bash
neo4j-admin database dump neo4j --to-path=/backups     # stop the DB first on Community edition
```

To clear one repository, re-import it, or run:

```cypher
MATCH (n) WHERE n.file_path STARTS WITH 'github.com/owner/repo/' DETACH DELETE n;
MATCH (f:File) WHERE f.path STARTS WITH 'github.com/owner/repo/' DETACH DELETE f;
```

Function nodes created for calls are keyed by name only. After a reset, remove
orphans with `MATCH (f:Function) WHERE f.file_path IS NULL AND NOT (f)--() DELETE f`.
