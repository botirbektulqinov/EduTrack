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
python -m py_compile app\services\grading_service.py app\api\v1\student\take.py app\api\v1\student\analytics.py app\services\assessment_service.py
@'
from app.main import app
print("app import ok")
'@ | python -

cd frontend
npm run lint
npm run build
```

## Production deployment

1. Copy `.env.example` to `.env` and fill every production secret.
2. Set `ENVIRONMENT=production`, `DEBUG=false`, and strong values for `SECRET_KEY` and `JWT_SECRET_KEY`.
3. Set `FRONTEND_URL` and `BACKEND_URL` to real public URLs.
4. Start the stack:

```powershell
docker compose -f docker-compose.prod.yml up -d --build
```

The production frontend is served by Nginx and proxies `/api` and `/ws` to the FastAPI service.

## Health endpoints

- `GET /health/live`
- `GET /health/ready`
- `GET /health`

## Notes

- `.env` is intentionally not tracked; use `.env.example` as the template.
- In development, if SMTP is not configured, password reset links fall back to server logs.
- Redis is recommended in production for token revocation and one-time reset tokens. If Redis is unavailable, password reset falls back to a short-lived signed token.
