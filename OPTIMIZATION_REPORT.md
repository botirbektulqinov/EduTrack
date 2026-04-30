# Optimization Report

## Deployment Preparation

### Changed

- Added production Nginx routing for `edutrack.systems`.
- Added HTTPS listeners, canonical domain redirects, `/api`, `/ws`, and `/health*` proxying.
- Added static asset caching, gzip, body-size limits, and basic browser security headers.
- Updated production Docker Compose to publish only frontend Nginx on `80` and `443`.
- Added Redis persistence volume.
- Added host-mounted Let's Encrypt certificate paths for the frontend Nginx container.
- Added production build args for `VITE_API_BASE_URL=/api/v1` and `VITE_WS_BASE_URL=/ws`.
- Updated frontend WebSocket URL construction so same-origin `/ws` works as `wss://edutrack.systems/ws/attempt/...`.
- Hardened production config validation for backend URL and CORS.
- Added `DEPLOYMENT.md` for DigitalOcean + name.com deployment.

### Manual

- Create DNS records at name.com.
- Fill `.env` with real secrets on the server.
- Issue the first Let's Encrypt certificate with Certbot.
- Run migrations and start Docker Compose.
- Configure backups and monitoring.

### Verification commands

```bash
docker compose -f docker-compose.prod.yml config
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
docker compose -f docker-compose.prod.yml up -d --build
curl https://edutrack.systems/health
curl -i https://edutrack.systems/api/v1/auth/me
```
