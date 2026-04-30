# EduTrack Production Deployment

This guide deploys EduTrack on a DigitalOcean Ubuntu server with Docker Compose, Nginx, PostgreSQL, Redis, Celery, and HTTPS for `edutrack.systems`.

## Target

- Frontend: `https://edutrack.systems`
- API: `https://edutrack.systems/api`
- WebSocket: `wss://edutrack.systems/ws`
- Health:
  - `https://edutrack.systems/health`
  - `https://edutrack.systems/health/live`
  - `https://edutrack.systems/health/ready`

## DNS at name.com

Create these records:

| Type | Host | Value | TTL |
| --- | --- | --- | --- |
| A | `@` | `134.122.92.113` | 300 |
| A | `www` | `134.122.92.113` | 300 |

Wait until both records resolve:

```bash
dig +short edutrack.systems
dig +short www.edutrack.systems
```

## Server preparation

```bash
ssh root@134.122.92.113
apt update && apt upgrade -y
apt install -y ca-certificates curl git ufw certbot
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
```

Install Docker:

```bash
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
docker --version
docker compose version
```

## Clone and configure

```bash
mkdir -p /opt
cd /opt
git clone https://github.com/botirbektulqinov/EduTrack.git
cd EduTrack
cp .env.example .env
nano .env
```

Required production values:

- `ENVIRONMENT=production`
- `DEBUG=false`
- `FRONTEND_URL=https://edutrack.systems`
- `BACKEND_URL=https://edutrack.systems`
- `CORS_ORIGINS=https://edutrack.systems,https://www.edutrack.systems`
- strong `SECRET_KEY`
- strong `JWT_SECRET_KEY`
- strong `POSTGRES_PASSWORD`
- matching `DATABASE_URL` and `DATABASE_URL_SYNC` password
- SMTP values if password reset email is needed

Generate secrets:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Do not use localhost URLs, wildcard CORS, or weak secrets in production. The backend rejects those settings on startup.

## Issue the first SSL certificate

The production Nginx container expects certificates at `/etc/letsencrypt/live/edutrack.systems`. Issue the first certificate before starting the stack:

```bash
certbot certonly --standalone \
  -d edutrack.systems \
  -d www.edutrack.systems \
  --agree-tos \
  --no-eff-email \
  -m admin@edutrack.systems
```

If port 80 is already in use, stop the service using it and retry.

## Start production

Validate the compose file:

```bash
docker compose -f docker-compose.prod.yml config
```

Run migrations explicitly:

```bash
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
```

Start the stack:

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
```

Only the frontend Nginx container publishes ports `80` and `443`. PostgreSQL, Redis, the API, Celery worker, and Celery beat stay on the internal Docker network.

## Verify

```bash
curl -I http://edutrack.systems
curl -I https://edutrack.systems
curl https://edutrack.systems/health
curl https://edutrack.systems/health/live
curl https://edutrack.systems/health/ready
curl -i https://edutrack.systems/api/v1/auth/me
```

Expected:

- HTTP redirects to `https://edutrack.systems`.
- `www.edutrack.systems` redirects to `https://edutrack.systems`.
- `/health/live` returns `{"status":"alive"}`.
- unauthenticated `/api/v1/auth/me` returns `401`.

Check logs:

```bash
docker compose -f docker-compose.prod.yml logs -f frontend
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f celery_worker
```

## Certificate renewal

After the stack is running, switch the certificate renewal method to webroot so renewals do not need to stop Nginx:

```bash
mkdir -p /var/www/certbot
certbot certonly --webroot \
  -w /var/www/certbot \
  -d edutrack.systems \
  -d www.edutrack.systems \
  --keep-until-expiring
```

Test renewal:

```bash
certbot renew --dry-run
```

Reload Nginx after successful renewals:

```bash
cat >/etc/letsencrypt/renewal-hooks/deploy/reload-edutrack-nginx.sh <<'EOF'
#!/usr/bin/env bash
set -e
cd /opt/EduTrack
docker compose -f docker-compose.prod.yml exec -T frontend nginx -s reload || docker compose -f docker-compose.prod.yml restart frontend
EOF
chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-edutrack-nginx.sh
```

## Redeploy

```bash
cd /opt/EduTrack
git pull
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
```

## Rollback

```bash
cd /opt/EduTrack
git log --oneline -5
git checkout <previous_commit>
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
docker compose -f docker-compose.prod.yml up -d --build
```

If a migration changed the database irreversibly, restore from a PostgreSQL backup instead of relying only on Git rollback.

## Backups

Create PostgreSQL backups before deployments:

```bash
docker compose -f docker-compose.prod.yml exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "backup-$(date +%F-%H%M).sql"
```

Restore only after stopping API/Celery writers and confirming the target database.

## Troubleshooting

- `docker compose ... config` fails: `.env` is missing a required variable.
- Nginx fails to start: certificate files are missing under `/etc/letsencrypt/live/edutrack.systems`.
- `/health/ready` is degraded: check PostgreSQL and Redis logs.
- Browser cannot connect to proctoring: verify `wss://edutrack.systems/ws/attempt/...` reaches the Nginx `/ws` proxy.
- Login CORS errors: verify `CORS_ORIGINS` exactly matches the public frontend origins.
