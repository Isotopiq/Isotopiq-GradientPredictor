# LC-MS Method Prediction Suite

A web-based application that predicts LC-MS method parameters (gradient, mobile phase pH, additives, column chemistry) from compound structure input, combining rules-based physicochemical heuristics with a trainable ML retention model.

Inspired by Chromsword Method Development Suite.

## Tech Stack
- **Backend**: Python 3.11, FastAPI, SQLAlchemy (async) + Alembic, RDKit, XGBoost/LightGBM, PostgreSQL
- **Frontend**: React + TypeScript, Vite, Tailwind CSS, shadcn/ui, Recharts, Ketcher
- **Infra**: Docker Compose, GitHub Actions CI

## Quick start (Docker)

```bash
cp .env.example .env
# IMPORTANT: change ADMIN_PASSWORD and JWT_SECRET in .env before production!
docker compose up --build
# App: http://localhost:18780  |  API: http://localhost:18780/api/health
# Swagger UI: http://localhost:18700/docs
# PostgreSQL: localhost:18732 (for external DB tools)
```

### Default admin login

On first startup, a default admin user is automatically seeded:

| Field    | Value                    |
|----------|--------------------------|
| Email    | `admin@example.com`      |
| Password | `changeme-admin-2024!`   |

**Change these immediately** by setting `ADMIN_EMAIL` and `ADMIN_PASSWORD` in your `.env` file (or Easypanel environment variables) before deploying to production.

Tear down:
```bash
docker compose down -v
```

## Local development (hot reload, opt-in)

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
# Backend: http://localhost:18700  |  Frontend: http://localhost:18717
```

## Easypanel deployment

An Easypanel-ready compose file is included at `docker-compose.easypanel.yml`.
It uses unique ports (19100 for backend, 19180 for frontend) to avoid conflicts
with other Easypanel services.

1. In Easypanel, create a new project and choose **Docker Compose** as the source.
2. Point to this repo or paste the contents of `docker-compose.easypanel.yml`.
3. Set these environment variables in the Easypanel UI:
   - `POSTGRES_PASSWORD` — strong password for the database
   - `JWT_SECRET` — long random string for JWT signing (e.g. `openssl rand -hex 32`)
   - `ADMIN_EMAIL` — admin login email
   - `ADMIN_PASSWORD` — admin login password (change from default!)
   - `CORS_ORIGINS` — your frontend domain (e.g. `https://lcms.yourdomain.com`)
   - `FRONTEND_URL` — your frontend domain (for password reset links)
4. Configure domains in Easypanel:
   - Primary domain (e.g. `lcms.yourdomain.com`) → `frontend` service (port 19180)
   - Optional API domain (e.g. `api.yourdomain.com`) → `backend` service (port 19100)
5. Deploy. Easypanel provisions SSL certificates automatically.

The database is internal-only (no published port) for security. The frontend
nginx proxies `/api/*` requests to the backend over the internal compose network.

The database stays internal to the compose network (not exposed to the host).

### Port assignments (chosen to avoid conflicts with common services)

| Service        | Port  | Notes                                    |
|----------------|-------|------------------------------------------|
| Frontend (nginx) | 18780 | Production SPA + nginx API proxy         |
| Frontend (Vite)  | 18717 | Dev hot-reload only                      |
| Backend (FastAPI)| 18700 | REST API + Swagger UI at `/docs`         |
| PostgreSQL       | 18732 | For external DB tools (DBeaver/pgAdmin)  |

## Testing (Docker, run-to-completion — no lingering containers)

### Backend
```bash
docker run --rm -v "$(pwd)/backend:/app" -w /app python:3.11-slim bash -c "pip install -e . && pytest"
```

### Frontend
```bash
docker run --rm -v "$(pwd)/frontend:/app" -w /app node:20 bash -c "npm ci && npm run test -- --run && npm run build"
```

### Integration / e2e (ephemeral compose stack, auto-teardown)
```bash
docker compose -f docker-compose.test.yml up --abort-on-container-exit --exit-code-from e2e --build
docker compose -f docker-compose.test.yml down -v
```

## Architecture

```
browser ──▶ nginx :18780 (frontend SPA) ──▶ /api/* ──▶ FastAPI :18700 (backend)
                                                              │
                                                              ├── PostgreSQL :5432 (internal only)
                                                              ├── RDKit (descriptors, pKa, logP)
                                                              ├── Rules engine (column / pH / additive / gradient)
                                                              ├── LSS gradient simulator
                                                              └── ML registry (per-column XGBoost/LightGBM/ensemble)
```

See `AGENTS.md` for build/test commands and conventions.

## Disclaimer
Predictions are estimates derived from physicochemical heuristics and statistical models trained on limited data. They require experimental verification before use in regulated or production analytical work.
