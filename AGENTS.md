# AGENTS.md — conventions for AI agents working on this repo

## Build / test / lint commands

All verification runs inside short-lived Docker containers (`--rm`, auto-removed). Never start long-lived dev servers on the host.

### Backend
- Test: `docker run --rm -v "$(pwd)/backend:/app" -w /app python:3.11-slim bash -c "pip install -e . && pytest"`
- Lint: `... ruff check .`
- Types: `... mypy app`
- Migrate: `... alembic upgrade head` (needs a DB — use the test compose stack)

### Frontend
- Test: `docker run --rm -v "$(pwd)/frontend:/app" -w /app node:20 bash -c "npm ci && npm run test -- --run"`
- Build: `... npm run build`
- Lint: `... npm run lint`
- E2E: via `docker compose -f docker-compose.test.yml up --abort-on-container-exit --exit-code-from e2e --build` then `down -v`

## Conventions
- **Backend**: async SQLAlchemy + asyncpg; Pydantic v2 schemas; service layer between routes and ORM; UUID PKs; `app/core` for domain logic (chem, rules, lss, ml), `app/services` for DB orchestration, `app/api/routes` for HTTP.
- **ML**: `RetentionModel` ABC in `app/core/ml/base.py`; never train/predict across column types; models keyed by `column_type` + `method_signature` hash; always surface confidence + extrapolation flag.
- **Frontend**: functional components + hooks; tanstack-query for server state; shadcn/ui primitives in `src/components/ui`; feature components in `src/components`; pages in `src/pages`; typed API clients in `src/api`.
- **Security**: bcrypt password hashing; JWT short TTL + refresh; CORS allowlist from env; no secrets in repo; parameterized queries; input validation on all uploads.
- **Deps**: pin versions; prefer releases ≥7 days old; no floating `latest`/`*`.
- **Honesty**: predictions must surface uncertainty (confidence, extrapolation, "insufficient data" states) — never present as certain.

## Project layout
See the plan file at `C:\Users\ekapelczak\.devin\plans\plan-4604c6cf77e17be1.md` for the full file-level architecture.
