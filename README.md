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
docker compose up --build
# App: http://localhost:18780  |  API: http://localhost:18780/api/health
```

Tear down:
```bash
docker compose down -v
```

## Local development (hot reload, opt-in)

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml up --build
# Backend: http://localhost:18700  |  Frontend: http://localhost:18717
```

### Port assignments (chosen to avoid conflicts with common services)

| Service        | Port  | Notes                          |
|----------------|-------|--------------------------------|
| Frontend (nginx) | 18780 | Production SPA + API proxy     |
| Frontend (Vite)  | 18717 | Dev hot-reload                 |
| Backend (FastAPI)| 18700 | REST API                       |
| PostgreSQL       | 18732 | Only if explicitly exposed     |

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
