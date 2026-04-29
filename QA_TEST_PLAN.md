# EduTrack QA Test Plan

## Strategy

Use a test pyramid: fast unit tests for grading/security helpers, API integration tests for auth/RBAC/assessment workflows, and a small Playwright suite for critical UI paths.

## Backend Matrix

- Grading: MCQ single, MCQ multi, numeric tolerance, fill blank, manual-review text, zero-point edge cases.
- Attempts: time window validation, max attempts, save locks, submit locks, terminated attempt behavior, double submit, cross-student access.
- RBAC: admin-only routes, teacher-owned groups, cross-teacher denial, student-owned results, unauthenticated 401, wrong-role 403.
- Proctoring: violation count, time penalty, max-violation termination, violation persistence, invalid WebSocket token.
- Analytics: own-student dashboard only, teacher group scope, empty dataset defaults, pass-rate/average correctness, division-by-zero safety.
- Auth: login success/failure, refresh behavior, logout revocation, forgot/reset password safe responses.

## Frontend Matrix

- Login form validation and API error display.
- Protected route redirect/blocking.
- Assessment timer display, sync, expiry, and penalty behavior.
- Submit confirmation for unanswered questions.
- Analytics empty states.
- Question renderer basics for common question types.
- API client refresh/logout behavior.

## E2E Matrix

- Login page renders.
- Unauthenticated protected route redirects to login.
- Seeded user can log in.
- Teacher can view/create assessment from fixtures.
- Student can open take page and submit a simple assessment.
- Analytics page renders with empty and populated fixture data.
- Real backend E2E covers seeded teacher dashboard/list/detail/results, seeded student take/submit, analytics from persisted attempts, wrong-role redirects, and cross-teacher denial.

## Current Automated Coverage

- `pytest`: grading unit cases, attempt timer/lock helpers, JWT/RBAC helper negatives.
- `pytest tests/integration` with `EDUTRACK_RUN_DB_TESTS=1` and `TEST_DATABASE_URL`: PostgreSQL-backed auth, RBAC, assessment start/save/submit, max attempts, locked attempts, cross-student access, and WebSocket token rejection.
- `npm run test`: timer behavior, protected-route redirects, login validation/API errors, assessment submit confirmation, and MCQ renderer behavior.
- `npm run test:e2e`: Playwright regression coverage for login render, invalid login, protected-route redirect, teacher dashboard empty state, student dashboard available assessments, take page open, mocked simple submit, analytics empty states, and logout.

## Security Negative Cases

- Invalid JWT returns 401.
- Wrong role returns 403.
- Teacher requesting another teacher's group is blocked.
- Student saving/submitting another student's attempt is blocked by route scoping.
- Attempt save with question outside the assessment returns an error.
- Submitted, graded, and terminated attempts reject mutation.
- Invalid WebSocket attempt token is rejected.
- Login and assessment start return 429 after configured rate-limit thresholds.
- Redis logout blacklist and reset-token one-time-use behavior are covered when `TEST_REDIS_URL` is available.
- Old refresh tokens are rejected after refresh rotation when Redis is available.
- Password reset signed fallback is disabled unless explicitly enabled.

## Regression Checklist

- `python -m py_compile app/services/grading_service.py app/api/v1/student/take.py app/api/v1/student/analytics.py app/services/assessment_service.py app/services/attempt_service.py`
- `python -c "from app.main import app; print('app import ok')"`
- `pytest`
- `pytest --cov=app`
- `python -m alembic upgrade head` with a reachable PostgreSQL database.
- `cd frontend && npm run lint`
- `cd frontend && npm run build`
- `cd frontend && npm run test`
- `cd frontend && npm run test:e2e`
- `cd frontend && npm run test:e2e:real` with seeded backend running.

## Manual QA Checklist

- Admin can create/edit users and groups.
- Teacher can create, publish, unpublish, and deactivate assessments.
- Student can start, autosave, submit, and view released results.
- Timer remains server-consistent after refresh, WebSocket reconnect, and violation penalties.
- Proctoring warnings and termination match configured thresholds.
- Analytics pages handle empty and populated data without crashes.
- Password reset returns safe messaging for existing and non-existing emails.
- Run `python scripts/seed_e2e.py` before release-candidate real E2E and verify seeded teacher/student journeys in browser.
