# Production Deployment Checklist

Use this checklist before deploying EduTrack to a server.

## Required environment

- `ENVIRONMENT=production`
- `DEBUG=false`
- `ENABLE_API_DOCS=false`, unless the API docs are protected behind an internal network
- Strong unique values for `SECRET_KEY` and `JWT_SECRET_KEY`
- Real public `FRONTEND_URL` and `BACKEND_URL`
- Explicit `CORS_ORIGINS` for the deployed frontend origins only
- `RATE_LIMIT_ENABLED=true`
- `ALLOW_PASSWORD_RESET_SIGNED_FALLBACK=false`
- PostgreSQL and Redis reachable from the backend and Celery containers
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` explicitly set

Generate secrets locally:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

## Pre-deploy checks

```powershell
python -m py_compile app\services\grading_service.py app\api\v1\student\take.py app\api\v1\student\analytics.py app\services\assessment_service.py app\services\attempt_service.py
python -c "from app.main import app; print('app import ok')"
pytest

cd frontend
npm run lint
npm run build
npm run test
npm run test:e2e
```

Run DB-backed and Redis-backed tests against an isolated database before release:

```powershell
$env:EDUTRACK_RUN_DB_TESTS = "1"
$env:TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@127.0.0.1:55432/edu_track_test"
$env:TEST_REDIS_URL = "redis://127.0.0.1:56379/15"
pytest tests/integration
```

## Docker deployment

Validate the compose file first:

```powershell
docker compose -f docker-compose.prod.yml config
```

The production compose file uses required variable expansion for database, Redis, URL, and secret settings. If any required value is missing, `docker compose config` fails before containers start.

Then deploy:

```powershell
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f api
```

The API container runs `alembic upgrade head` before starting Uvicorn. Back up PostgreSQL before deploying migrations to an existing production database.

## Post-deploy smoke checks

- `GET /health/live`
- `GET /health/ready`
- Login with a real user
- Teacher dashboard loads
- Student can start, save, and submit an assessment
- Analytics pages render without server errors
- Password reset email delivery works
- Redis-backed logout/refresh revocation works

## Known production limitations

- Code execution preview is subprocess-based and must be moved to a hardened sandbox before running untrusted code in production.
- Max-attempt protection uses PostgreSQL advisory locking; keep a single shared production database and avoid bypassing the API.
- Rate-limit fallback is in-memory if Redis is unavailable and is not sufficient for multi-worker production.
