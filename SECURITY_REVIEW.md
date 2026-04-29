# EduTrack Security Review

## Auth Review

- Access and refresh JWTs include `sub`, `type`, expiry, issued-at, and `jti`.
- Access-token dependencies reject invalid, expired, wrong-type, inactive-user, and missing-sub tokens.
- Logout blacklists refresh-token `jti` in Redis when a refresh token is supplied.
- Password reset avoids email enumeration and uses Redis one-time tokens when Redis is available.
- High-risk auth endpoints are rate-limited by IP: login, refresh, forgot-password, and reset-password.
- Refresh-token rotation now revokes the refresh token that was just used when Redis is available.

## RBAC Review

- Route dependencies separate admin, teacher, student, and any-authenticated access.
- Teacher analytics now rejects groups that do not belong to the requesting teacher.
- Student assessment save/submit/result routes are scoped to `attempt.student_id == current_user.id`.
- Student analytics routes use the authenticated student id rather than a request-provided student id.
- Missing bearer credentials now return 401 through the shared auth dependency instead of the default HTTPBearer 403.

## Assessment Session Security

- Save and submit now row-lock the attempt before mutation.
- Submitted, grading, graded, and terminated attempts cannot be modified.
- Answer saves validate that each question belongs to the attempt's assessment.
- Server-side elapsed time plus violation penalties is used for authoritative remaining time.
- Double submit accepts only the first in-progress mutation; later submits return conflict.
- Attempt start now uses a PostgreSQL advisory transaction lock per assessment/student pair before max-attempt validation.
- Assessment start and answer save are rate-limited by authenticated user.
- A PostgreSQL concurrency regression test verifies that parallel starts do not exceed `max_attempts=1` under the advisory lock.

## WebSocket Security

- WebSocket attempt id and server token are parsed as UUIDs and rejected on invalid input.
- The server token must match the attempt token and the attempt must still be in progress.
- WebSocket answer saves use an allow-list of mutable answer fields.
- WebSocket answer saves validate question ownership and reject inactive/expired attempts.
- WebSocket violation ingestion is rate-limited per attempt id.

## Token And Session Risks

- Refresh-token rotation depends on Redis blacklist persistence; if Redis is unavailable, old-token revocation cannot be guaranteed.
- Password reset signed-token fallback is disabled by default and must be explicitly enabled with `ALLOW_PASSWORD_RESET_SIGNED_FALLBACK=true`.
- Access token revocation is not implemented; access tokens remain valid until expiry.

## Production Config Risks

- Production settings reject `DEBUG=true`, weak `SECRET_KEY`, weak `JWT_SECRET_KEY`, and localhost frontend URLs.
- CORS is environment-driven, but production deployments must set explicit frontend origins.
- `.env.example` should remain the template; real secrets must stay out of git.

## Known Limitations

- Rate limiting uses Redis when available and an in-memory fallback for development. In-memory limits are process-local and are not sufficient for multi-worker production deployments.
- Python code preview is subprocess-based and should not be treated as a hardened execution sandbox.
- Real backend E2E covers seeded auth, RBAC redirects, cross-teacher assessment denial, student assessment submit, and analytics rendering against persisted data.
- Moderate DOMPurify advisories remain transitively through `monaco-editor`; the non-breaking audit path cleared high-severity advisories, while the remaining npm fix path is breaking.
- WebSocket server tokens are bearer secrets; leaking an active attempt token can allow connection to that attempt.
- File upload validation was not reviewed because no active upload endpoint was found in this pass.

## Recommended Next Hardening

- Back rate limiting with shared Redis in production and add upstream gateway/WAF limits.
- Add server-side refresh-session state if product requirements need device/session management beyond Redis blacklist rotation.
- Use Redis or database-backed one-time attempt WebSocket tokens with short expiry.
- Execute code previews in an isolated container with network disabled and strict CPU/memory/file limits.
- Add DB-level max-attempt protection with an `attempt_number` column and a unique `(assessment_id, student_id, attempt_number)` constraint.
