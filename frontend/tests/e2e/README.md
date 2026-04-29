# EduTrack E2E Tests

This is the Playwright regression foundation for the React app. The default suite
uses network-level fixtures so it can run without a seeded backend while still
exercising the real router, auth store, layouts, and critical pages.

## Run

```powershell
cd frontend
npm run test:e2e
```

The config starts the Vite dev server on `http://127.0.0.1:3000`.

For real backend E2E, seed and start the backend first, then run:

```powershell
cd frontend
$env:E2E_REAL = "1"
$env:E2E_API_URL = "http://127.0.0.1:8000/api/v1"
npm run test:e2e:real
```

## Current Coverage

- Login page renders.
- Protected student routes redirect unauthenticated users to login.
- Invalid login displays an API error.
- Teacher login reaches the analytics dashboard empty state.
- Student dashboard renders available assessments.
- Student can open the assessment take page.
- Student can submit a simple mocked assessment.
- Student analytics empty states render without crashing.
- User can logout.
- Real backend auth, teacher, student assessment, analytics, and access-control flows are covered by `*.real.spec.ts`.

## Seeded Backend Expansion

- Seed a known admin, teacher, and student fixture set.
- Add one DB-backed browser scenario that logs in against the real API.
- Verify teacher creates or opens an assessment from seeded data.
- Verify student saves answers and submits against PostgreSQL.
- Add visual checks for analytics with non-empty datasets.
