# EduTrack Optimization Report

## Inspected

- FastAPI app startup, settings, DB session lifecycle, Redis fallback, auth/RBAC dependencies.
- Student take/submit flow, student analytics, teacher analytics, proctoring WebSocket.
- Grading, assessment, analytics, proctoring, password reset, Celery workers.
- SQLAlchemy models and Alembic migrations.
- React/Vite package metadata, API client, assessment timer/take page, lint/build setup.
- Docker Compose and GitHub Actions CI.

## Bugs And Risks Found

- Student answer save queried once per answer and did not verify that submitted `question_id` values belonged to the active attempt's assessment.
- Submit/save did not row-lock the attempt, making double submit and save/submit races easier to trigger under concurrent requests.
- WebSocket answer save accepted arbitrary model attributes and did not validate question ownership.
- Server timer state was not authoritative during WebSocket heartbeat; `time_remaining_seconds` could stay stale without elapsed-time calculation.
- Student available-assessments endpoint had per-assessment attempt count and in-progress queries.
- Teacher group analytics performed per-assessment stats queries and could reveal scoped group data if a teacher requested another teacher's group.
- Hot assessment, attempt, answer, and violation queries had missing supporting indexes.
- Frontend had no checked-in test runner or E2E foundation.

## Fixed

- Added shared attempt lifecycle helpers in `app/services/attempt_service.py`.
- Added row locks for save/submit, bulk answer lookup, question ownership validation, locked-attempt checks, and server timer synchronization.
- Hardened WebSocket attempt/token parsing, answer field allow-listing, question ownership checks, and authoritative heartbeat time sync.
- Optimized student available assessment attempt metadata into grouped queries.
- Optimized teacher group analytics to avoid per-assessment stats queries and reject non-owned groups.
- Added Alembic hot-path indexes for groups, enrollments, assessments, questions, attempts, answers, and violations.
- Added pytest unit coverage for grading, attempt locking/timer behavior, JWT token type checks, and RBAC negative behavior.
- Added opt-in PostgreSQL integration tests for auth, teacher/student RBAC, assessment start/save/submit, max attempts, locked/terminated attempts, cross-student attempts, and invalid WebSocket tokens.
- Added Vitest + React Testing Library timer tests.
- Added Playwright smoke setup for login/protected-route behavior.
- Updated CI to run backend and frontend tests.
- Ran `npm audit fix` to clear high-severity Vite/axios-related advisories without force-downgrading Monaco.

## Intentionally Not Changed

- Public API route names and response wrapper shapes were preserved.
- Code preview still uses the existing Python subprocess approach; a stronger sandbox is documented as a security limitation.
- Refresh-token rotation/revocation was not redesigned beyond documenting the current behavior.
- Broad seeded end-to-end business journeys were not added; the new DB integration layer focuses on security and assessment critical paths.

## Remaining Risks

- Full race protection for max attempts should be backed by DB constraints or serializable transaction strategy.
- Password reset signed fallback is disabled by default; production should require Redis-backed one-time reset tokens.
- No application-level rate limiting is enforced.
- Playwright scenario coverage is currently smoke-level only.
- Alembic upgrade could not be run locally from this shell because PostgreSQL rejected the configured `postgres` password.
- `npm audit --audit-level=high` passes, but moderate DOMPurify advisories remain through `monaco-editor`; npm's suggested fix requires a breaking Monaco downgrade to `0.53.0`.

## Suggested Next Improvements

- Add PostgreSQL fixture-backed API tests for start/save/submit/RBAC routes.
- Add Redis-backed integration tests for logout blacklist and reset-token one-time use.
- Move Python code execution preview into a containerized sandbox with CPU, memory, filesystem, and network limits.
- Add rate limiting for auth, password reset, code preview, and proctoring violation ingestion.

## Sprint 2 Additions

- Added Redis/in-memory fixed-window rate limiting for login, refresh, forgot-password, reset-password, assessment start, answer save, code preview, and WebSocket violation ingestion.
- Added PostgreSQL advisory locking around assessment start max-attempt checks.
- Hardened teacher attempt detail/manual grading ownership checks.
- Changed missing bearer credentials to return 401 from the shared auth dependency.
- Fixed the frontend API interceptor so login/reset 401s do not trigger refresh redirects and hide user-facing errors.
- Expanded PostgreSQL integration coverage to auth token behavior, admin permissions, teacher RBAC, student assessment lifecycle, Redis logout/reset behavior, rate limiting, and WebSocket token rejection.
- Expanded Vitest coverage for login validation/API errors, protected routes, question rendering, and assessment submit confirmation.
- Expanded Playwright coverage from smoke-only to login, invalid login, role dashboards, student assessment list, take page, mocked submit, analytics empty states, and logout.

## Sprint 2 Commands

- Passed: `python -m py_compile app/services/grading_service.py app/api/v1/student/take.py app/api/v1/student/analytics.py app/services/assessment_service.py app/services/attempt_service.py`
- Passed: `python -c "from app.main import app; print('app import ok')"`
- Passed: `pytest`
- Passed: `pytest tests/integration`
- Passed: `pytest --cov=app`
- Passed: `alembic upgrade head` against the local test PostgreSQL database.
- Passed: `cd frontend && npm run lint`
- Passed: `cd frontend && npm run build`
- Passed: `cd frontend && npm run test`
- Passed: `cd frontend && npm run test:e2e`
- Skipped: `ruff check app tests`; `ruff` is not installed or listed in `requirements.txt`.
- Skipped: `mypy app`; `mypy` is not installed and no mypy config is checked in.

## Sprint 2 Remaining Risks

- Rate limiting must use shared Redis in production; the fallback is process-local.
- Refresh-token rotation still does not revoke the previous refresh token automatically.
- Redis-down password reset fallback is disabled by default; enabling it is a development-only escape hatch.
- Full max-attempt race protection would be stronger with a DB-level constraint or serializable transaction design.
- Playwright still uses API fixtures rather than a real seeded backend.
- Code execution preview remains subprocess-based and is not a hardened sandbox.

## Sprint 3 Additions

- Added `scripts/seed_e2e.py`, an idempotent, production-guarded E2E seed for stable admin/teacher/student users, E2E groups, a published active assessment, another-teacher assessment, and a previous graded analytics attempt.
- Added real backend Playwright tests for auth, teacher dashboard/assessment/results, student take/answer/submit, analytics, wrong-role redirects, and cross-teacher assessment denial.
- Added `npm run test:e2e:real` while keeping the existing mocked Playwright suite under `npm run test:e2e`.
- Updated CI with a dedicated `e2e-real` job using PostgreSQL, Redis, seed data, a live backend, Vite, and Playwright.
- Hardened refresh-token rotation by blacklisting the used refresh token after successful refresh.
- Disabled signed password-reset fallback by default and kept forgot-password responses non-enumerating if reset delivery fails.
- Added a max-attempt concurrency regression test for the PostgreSQL advisory lock.
- Added code-preview boundary tests for timeout and invalid-code failure behavior.
- Added `E2E_TESTING.md` and `CODE_EXECUTION_SECURITY.md`.

## Sprint 3 Commands

- Passed: `python scripts/seed_e2e.py` twice against local test PostgreSQL to verify idempotent reruns.
- Passed: `npm run test:e2e:real` against live local FastAPI/PostgreSQL/Redis.
- Passed: backend compile/import, `pytest`, `pytest tests/integration`, `pytest --cov=app`, `alembic upgrade head`, frontend lint/build/unit tests, mocked Playwright, and real-backend Playwright.
- Failed then rerun correctly: integration and coverage were accidentally launched in parallel against the same destructive test database, causing schema drop/create collisions. Sequential reruns passed.

## Sprint 3 Remaining Risks

- Real E2E disables application rate limiting to avoid browser-suite IP throttling; backend integration tests still cover rate limits.
- The repo still lacks a full initial Alembic schema migration; E2E seed creates metadata schema before applying existing migrations.
- Real E2E verifies seeded published assessment behavior, not full teacher UI creation of a brand-new assessment.
- Redis is still required for reliable refresh-token revocation and one-time reset tokens.
- Code execution preview remains subprocess-based; see `CODE_EXECUTION_SECURITY.md`.
