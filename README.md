# EduTrack

EduTrack is a university assessment and analytics platform built with FastAPI, PostgreSQL, Redis, Celery, React, TypeScript, and Vite.

## Features

- Assessment creation, publishing, delivery, saving, and submission
- MCQ, numeric/fill-blank, text/manual-review, ordering, matching, categorization, and code-preview questions
- Student dashboards, results, review matrix, and analytics
- Teacher assessment analytics, attempt review, manual grading, bulk import, and revision history
- Proctoring-aware assessment delivery with WebSocket monitoring
- PostgreSQL-backed RBAC, attempt lifecycle, token, rate-limit, and WebSocket regression tests
- Playwright smoke tests and real-backend seeded E2E journeys

## Stack

- Backend: FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, Celery
- Frontend: React, Vite, TypeScript, Vitest, Playwright
- Security controls: JWT auth, role-based dependencies, Redis-backed refresh/logout/reset behavior, fixed-window rate limiting, server-side attempt timers

## Local Development

Backend:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python seed.py
uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
npm ci
npm run dev:h
```

## Test Database

Use an isolated database for integration tests. The commands below start local Docker test services on non-default host ports:

```powershell
docker run --name edutrack-test-postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=edu_track_test -p 55432:5432 -d postgres:15
docker run --name edutrack-test-redis -p 56379:6379 -d redis:7-alpine
```

If they already exist:

```powershell
docker start edutrack-test-postgres edutrack-test-redis
```

## Quality Gates

Backend:

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@127.0.0.1:55432/edu_track_test"
$env:DATABASE_URL_SYNC = "postgresql+psycopg2://postgres:postgres@127.0.0.1:55432/edu_track_test"
$env:REDIS_URL = "redis://127.0.0.1:56379/0"
$env:ENVIRONMENT = "development"
$env:DEBUG = "false"

python -m py_compile app\services\grading_service.py app\api\v1\student\take.py app\api\v1\student\analytics.py app\services\assessment_service.py app\services\attempt_service.py
python -c "from app.main import app; print('app import ok')"
python -m alembic upgrade head

$env:EDUTRACK_RUN_DB_TESTS = "1"
$env:TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@127.0.0.1:55432/edu_track_test"
$env:TEST_REDIS_URL = "redis://127.0.0.1:56379/15"
python -m pytest
python -m pytest tests/integration
python -m pytest --cov=app
```

Frontend:

```powershell
cd frontend
npm ci
npm run lint
npm run build
npm run test
npm run test:e2e
```

Install Playwright browsers if needed:

```powershell
cd frontend
npx playwright install chromium
```

## Real Backend E2E

The deterministic E2E seed creates local-only users:

- `admin.e2e@edutrack.test`
- `teacher.e2e@edutrack.test`
- `teacher2.e2e@edutrack.test`
- `student.e2e@edutrack.test`
- `student2.e2e@edutrack.test`

Default password is `E2EPassword123!`; override it with `E2E_PASSWORD`. The seed refuses to run when `ENVIRONMENT=production`.

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@127.0.0.1:55432/edu_track_test"
$env:DATABASE_URL_SYNC = "postgresql+psycopg2://postgres:postgres@127.0.0.1:55432/edu_track_test"
$env:REDIS_URL = "redis://127.0.0.1:56379/0"
$env:ENVIRONMENT = "development"
$env:DEBUG = "false"
$env:RATE_LIMIT_ENABLED = "false"
python -m alembic upgrade head
python scripts/seed_e2e.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

cd frontend
$env:E2E_REAL = "1"
$env:E2E_BASE_URL = "http://127.0.0.1:3000"
$env:E2E_API_URL = "http://127.0.0.1:8000/api/v1"
npm run test:e2e:real
```

Real E2E currently covers auth, protected-route behavior, teacher dashboard/assessment/results views, student start-answer-submit flow, and analytics pages against persisted backend data.

## Production Deployment

Full DigitalOcean + name.com instructions are in [DEPLOYMENT.md](DEPLOYMENT.md).

1. Copy `.env.example` to `.env` and fill every required production value.
2. Set `ENVIRONMENT=production`, `DEBUG=false`, and `ENABLE_API_DOCS=false` unless docs are internal-only.
3. Generate strong unique values for `SECRET_KEY` and `JWT_SECRET_KEY`.
4. Set `FRONTEND_URL`, `BACKEND_URL`, and `CORS_ORIGINS` to real public origins.
5. Keep `RATE_LIMIT_ENABLED=true` and `ALLOW_PASSWORD_RESET_SIGNED_FALLBACK=false`.
6. Confirm PostgreSQL and Redis are reachable by the API and Celery services.
7. Validate and start the production stack:

```powershell
docker compose -f docker-compose.prod.yml config
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
```

The production compose file fails fast if required database, Redis, URL, or secret variables are missing. The API container runs `alembic upgrade head` before starting Uvicorn. Back up PostgreSQL before applying migrations to an existing production database.
For `edutrack.systems`, Nginx serves the frontend on `https://edutrack.systems`, proxies the API under `/api`, proxies WebSockets under `/ws`, and exposes `/health`, `/health/live`, and `/health/ready`.

## CI

GitHub Actions runs:

- Backend compile/import/tests with PostgreSQL and Redis services
- Frontend lint/build/unit tests
- Playwright smoke tests
- Real-backend Playwright E2E with seeded PostgreSQL and Redis data

## Health Checks

- `GET /health/live`
- `GET /health/ready`
- `GET /health`

## Security Notes

- `.env` is intentionally ignored and must not be committed.
- Redis is required in production for token revocation, rate limiting, and one-time password reset tokens.
- Code execution preview is still subprocess-based. Before running untrusted code in production, move execution into a hardened sandbox with network disabled, CPU/memory/time limits, read-only filesystem, non-root user, language allowlist, output cap, rate limit, and audit logging.
- Max-attempt protection uses PostgreSQL advisory locking. Keep one shared production database and do not bypass the API.
