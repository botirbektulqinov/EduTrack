# EduTrack

EduTrack is a university assessment and analytics platform built with FastAPI, PostgreSQL, Redis, Celery, React, and Vite.

## What is included

- Advanced assessments with MCQ, text, ordering, matching, categorization, and code questions
- Python code execution preview with visible test cases
- Subject, module, and topic curriculum structure
- Student review matrix across semester, year, class, teacher groups, and university
- Teacher analytics, bulk AI-assisted question import, and revision history
- Proctoring-aware assessment delivery with WebSocket monitoring

## Local development

### Backend

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python seed.py
uvicorn app.main:app --reload
```

### Frontend

```powershell
cd frontend
npm ci
npm run dev:h
```

## Quality gates

```powershell
python -m py_compile app\services\grading_service.py app\api\v1\student\take.py app\api\v1\student\analytics.py app\services\assessment_service.py app\services\attempt_service.py
@'
from app.main import app
print("app import ok")
'@ | python -
pytest
pytest --cov=app
python -m alembic upgrade head

cd frontend
npm run lint
npm run build
npm run test
npm run test:e2e
npm run test:e2e:real
```

PostgreSQL-backed integration tests are opt-in so they never reset a local database accidentally:

```powershell
$env:EDUTRACK_RUN_DB_TESTS = "1"
$env:TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/edu_track_test"
$env:TEST_REDIS_URL = "redis://localhost:6379/15"
pytest tests/integration
```

If Playwright browsers are not installed yet:

```powershell
cd frontend
npx playwright install chromium
```

## Real E2E Seed

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@127.0.0.1:55432/edu_track_test"
$env:REDIS_URL = "redis://127.0.0.1:56379/0"
$env:ENVIRONMENT = "development"
$env:RATE_LIMIT_ENABLED = "false"
python scripts/seed_e2e.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

cd frontend
$env:E2E_REAL = "1"
$env:E2E_API_URL = "http://127.0.0.1:8000/api/v1"
npm run test:e2e:real
```

## Production deployment

1. Copy `.env.example` to `.env` and fill every required production value.
2. Set `ENVIRONMENT=production`, `DEBUG=false`, and strong values for `SECRET_KEY` and `JWT_SECRET_KEY`.
3. Set `FRONTEND_URL` and `BACKEND_URL` to real public URLs.
4. Keep `RATE_LIMIT_ENABLED=true` and `ALLOW_PASSWORD_RESET_SIGNED_FALLBACK=false` in production.
5. Start the stack:

```powershell
docker compose -f docker-compose.prod.yml config
docker compose -f docker-compose.prod.yml up -d --build
```

The production frontend is served by Nginx and proxies `/api` and `/ws` to the FastAPI service.
The production compose file intentionally fails fast if required database, Redis, URL, or secret variables are missing.

## Health endpoints

- `GET /health/live`
- `GET /health/ready`
- `GET /health`

## Notes

- `.env` is intentionally not tracked; use `.env.example` as the template.
- In development, if SMTP is not configured, password reset links fall back to server logs.
- Redis is required in production for token revocation, rate limiting, and one-time password reset tokens. Signed password-reset fallback is disabled by default.
- DB-backed API tests are opt-in through `EDUTRACK_RUN_DB_TESTS=1` and require an isolated PostgreSQL database.
- See `TESTING.md`, `E2E_TESTING.md`, `CODE_EXECUTION_SECURITY.md`, `OPTIMIZATION_REPORT.md`, `QA_TEST_PLAN.md`, and `SECURITY_REVIEW.md` for the current quality and security review.
