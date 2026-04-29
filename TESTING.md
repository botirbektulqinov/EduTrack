# EduTrack Testing Guide

## Backend Unit Tests

Run the fast backend suite from the repository root:

```powershell
pytest
```

The default suite includes grading logic, attempt lifecycle helpers, auth helper negatives, and API-level tests that do not require destructive access to a database.

## PostgreSQL API Integration Tests

DB-backed tests are opt-in because they reset the configured test schema.

```powershell
$env:EDUTRACK_RUN_DB_TESTS = "1"
$env:TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@127.0.0.1:55432/edu_track_test"
$env:TEST_REDIS_URL = "redis://127.0.0.1:56379/15"
pytest tests/integration
```

The integration fixtures create tables from SQLAlchemy metadata and seed admin, teacher A/B, student A/B, owned groups, assessments, attempts, and answers. They cover auth, admin permissions, teacher/student RBAC, assessment token validation, start/save/submit, max attempts, submitted/terminated immutability, rate limiting, Redis token behavior, and invalid WebSocket tokens.

## Redis Tests

Redis-backed tests use `TEST_REDIS_URL` when present. The fixture flushes only that Redis database before and after each Redis test.

Covered Redis behavior:

- Logout blacklists refresh-token `jti`.
- Password reset tokens are one-time-use.
- Rate limiter falls back cleanly when Redis fails.

If Redis is unavailable, the Redis-specific tests are skipped rather than mocked as passing.

## Coverage

```powershell
$env:EDUTRACK_RUN_DB_TESTS = "1"
$env:TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@127.0.0.1:55432/edu_track_test"
$env:TEST_REDIS_URL = "redis://127.0.0.1:56379/15"
pytest --cov=app
```

Current coverage is strongest around grading, schemas, core auth/security helpers, attempt lifecycle protections, and critical API workflows. Large admin/curriculum/worker surfaces still need deeper tests.

## Frontend Unit Tests

```powershell
cd frontend
npm run test
```

Vitest covers timer behavior, protected routes, login validation/API errors, assessment submit confirmation, and the common question renderer path.

## Playwright E2E

```powershell
cd frontend
npx playwright install chromium
npm run test:e2e
```

The default E2E suite uses browser-level API fixtures so it can run without a seeded backend. It covers login rendering, invalid login, protected-route redirects, teacher dashboard empty state, student dashboard available assessments, opening the take page, submitting a mocked assessment, student analytics empty states, and logout.

## Real Backend Playwright E2E

Real E2E uses deterministic seed data and a live backend:

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@127.0.0.1:55432/edu_track_test"
$env:REDIS_URL = "redis://127.0.0.1:56379/0"
$env:ENVIRONMENT = "development"
$env:DEBUG = "false"
$env:RATE_LIMIT_ENABLED = "false"
$env:FRONTEND_URL = "http://127.0.0.1:3000"
$env:BACKEND_URL = "http://127.0.0.1:8000"
python scripts/seed_e2e.py
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second shell:

```powershell
cd frontend
$env:E2E_REAL = "1"
$env:E2E_BASE_URL = "http://127.0.0.1:3000"
$env:E2E_API_URL = "http://127.0.0.1:8000/api/v1"
$env:E2E_PASSWORD = "E2EPassword123!"
npm run test:e2e:real
```

See `E2E_TESTING.md` for seeded users, reset strategy, and coverage.

## Local Test Services

One local option:

```powershell
docker run --name edutrack-test-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=edu_track_test -p 55432:5432 -d postgres:15
docker run --name edutrack-test-redis -p 56379:6379 -d redis:7-alpine
```

Then run:

```powershell
docker exec edutrack-test-postgres pg_isready -U postgres -d edu_track_test
docker exec edutrack-test-redis redis-cli ping
```

## Known Skips And Blockers

- `ruff check app tests` is skipped unless `ruff` is installed; it is not currently listed in `requirements.txt`.
- `mypy app` is skipped unless `mypy` is installed; no mypy configuration is checked in.
- Real backend browser tests are available through `npm run test:e2e:real`; they require a live backend and seeded E2E data.
