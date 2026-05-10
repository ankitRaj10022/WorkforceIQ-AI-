# WorkforceIQ Cloud Compose

This folder deploys WorkforceIQ on one Linux cloud VM with Docker Compose.

Included services:
- Flask API through Gunicorn
- Celery worker
- MySQL 8
- Redis
- Caddy reverse proxy with automatic HTTPS

This is the fastest cloud path for a startup demo or private beta. For enterprise scale, move MySQL and Redis to managed cloud services later.

## Files To Copy To The Server

- `docker-compose.cloud.yml`
- `Caddyfile`
- `.env.cloud`, created from `env.cloud.example`

## First Deploy

```bash
cp env.cloud.example .env.cloud
python3 - <<'PY'
import secrets
print("SECRET_KEY=" + secrets.token_hex(32))
print("JWT_SECRET_KEY=" + secrets.token_hex(32))
print("MYSQL_ROOT_PASSWORD=" + secrets.token_urlsafe(32))
print("MYSQL_PASSWORD=" + secrets.token_urlsafe(32))
PY
```

Add the generated values to `.env.cloud`. Also set:

```bash
APP_DOMAIN=your-api-domain.example.com
ACME_EMAIL=you@example.com
WORKFORCEIQ_IMAGE=ghcr.io/<owner>/<repo>/workforceiq-api:latest
```

Then run:

```bash
docker compose -f docker-compose.cloud.yml --env-file .env.cloud up -d
docker compose -f docker-compose.cloud.yml --env-file .env.cloud ps
```

## Smoke Test

```bash
curl -fsS https://your-api-domain.example.com/api/health
```

## Backup

```bash
docker compose -f docker-compose.cloud.yml --env-file .env.cloud exec db \
  sh -lc 'mysqldump --single-transaction --routines --triggers --events -uroot -p"$MYSQL_ROOT_PASSWORD" workforceiq > /backups/workforceiq-$(date -u +%Y%m%dT%H%M%SZ).sql'
```
