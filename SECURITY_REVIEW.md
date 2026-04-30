# Security Review

## Deployment security

- DNS must point only `edutrack.systems` and `www.edutrack.systems` to `134.122.92.113`.
- HTTP is redirected to HTTPS by Nginx.
- `www.edutrack.systems` is redirected to the canonical `https://edutrack.systems`.
- PostgreSQL and Redis are internal Docker services and are not published publicly by `docker-compose.prod.yml`.
- Production settings reject `DEBUG=true`, weak secrets, localhost frontend/backend URLs, wildcard CORS, and localhost CORS origins.
- `RATE_LIMIT_ENABLED=true` should stay enabled in production and uses Redis-backed counters when Redis is reachable.
- `.env` is ignored by Git and must never be committed.

## Operational risks

- DNS propagation can take time after name.com changes. Verify with `dig`.
- Certificate issuance requires ports `80` and `443` open on the DigitalOcean firewall and Ubuntu UFW.
- Rotate `SECRET_KEY`, `JWT_SECRET_KEY`, database password, SMTP password, and any object-storage secrets if they are exposed.
- Back up PostgreSQL before migrations and before major deployments.
- Redis persistence is enabled with append-only files, but Redis is not a substitute for PostgreSQL backups.

## Known limitations

- Code execution preview is subprocess-based and is not a hardened sandbox. Do not execute untrusted production code until it is isolated with container-level CPU, memory, network, filesystem, timeout, user, output, and audit controls.
- Max-attempt enforcement uses PostgreSQL advisory locking. Keep one shared production database and avoid bypassing the API.
- Browser security headers are set in Nginx, but a full CSP should be added after checking frontend asset and Monaco requirements.
