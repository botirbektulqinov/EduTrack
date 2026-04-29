# EduTrack Real Backend E2E Testing

## Purpose

The real E2E suite verifies the React app against a live FastAPI backend, PostgreSQL database, and Redis instance using deterministic local-only seed data.

## Seeded Users

- `admin.e2e@edutrack.test`
- `teacher.e2e@edutrack.test`
- `teacher2.e2e@edutrack.test`
- `student.e2e@edutrack.test`
- `student2.e2e@edutrack.test`
- Default password: `E2EPassword123!`

Override the password with `E2E_PASSWORD`. The seed refuses to run when `ENVIRONMENT=production`.

## Local Workflow

```powershell
docker start edutrack-test-postgres edutrack-test-redis

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

In another shell:

```powershell
cd frontend
$env:E2E_REAL = "1"
$env:E2E_BASE_URL = "http://127.0.0.1:3000"
$env:E2E_API_URL = "http://127.0.0.1:8000/api/v1"
$env:E2E_PASSWORD = "E2EPassword123!"
npm run test:e2e:real
```

## Data Reset Strategy

`scripts/seed_e2e.py` is idempotent. It updates stable E2E users, preserves E2E subject/group records, deletes only E2E-named assessments and their attempts/answers/violations, then recreates:

- `E2E Seeded Assessment`
- `E2E Previous Analytics Quiz`
- `E2E Other Teacher Assessment`

Developer data outside the E2E namespace is left intact.

## Coverage Map

- Auth: invalid login, teacher login, student login, logout.
- Teacher: dashboard, assessment list, seeded assessment detail, published state, results page.
- Student: dashboard, available assessment, take page, MCQ answer, numeric answer, short answer, submit confirmation.
- Analytics: seeded previous attempt appears in student and teacher analytics.
- Access control: unauthenticated redirect, student blocked from teacher route, teacher blocked from student route, teacher blocked from another teacher assessment.

## Known Limitations

- The real E2E suite disables app rate limiting to avoid browser-suite IP throttling; rate limiting is covered by backend integration tests.
- Full teacher assessment creation through the UI is not covered yet.
- The seed creates schema via SQLAlchemy metadata because the repository does not currently include a full initial Alembic schema migration.
