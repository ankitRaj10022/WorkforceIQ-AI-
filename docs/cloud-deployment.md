# Cloud Deployment

This project now supports a provider-neutral cloud VM deployment. Use any Linux VM where you can install Docker and point a domain to the server.

## Architecture

- Caddy terminates HTTPS on ports `80` and `443`.
- Flask/Gunicorn runs the API internally on port `5000`.
- MySQL 8 stores the workforce system of record.
- Redis backs Celery and production rate limiting.
- Celery worker runs async ML/search/report jobs.

## Server Setup

On the cloud VM:

```bash
mkdir -p /opt/workforceiq/backups
cd /opt/workforceiq
```

Copy these files to `/opt/workforceiq`:

- `cloud/compose/docker-compose.cloud.yml`
- `cloud/compose/Caddyfile`

Create `/opt/workforceiq/.env.cloud` from `cloud/compose/env.cloud.example`. Generate secrets locally:

```bash
python3 - <<'PY'
import secrets
print("SECRET_KEY=" + secrets.token_hex(32))
print("JWT_SECRET_KEY=" + secrets.token_hex(32))
print("MYSQL_ROOT_PASSWORD=" + secrets.token_urlsafe(32))
print("MYSQL_PASSWORD=" + secrets.token_urlsafe(32))
PY
```

Set these values in `.env.cloud`:

- `APP_DOMAIN`: your API domain, for example `api.example.com`.
- `ACME_EMAIL`: email for TLS certificate registration.
- `CORS_ORIGINS`: your frontend origin.
- `WORKFORCEIQ_IMAGE`: image name, for example `ghcr.io/<owner>/<repo>/workforceiq-api:latest`.
- If using enterprise OIDC SSO: `OIDC_ENABLED=true`, plus `OIDC_ISSUER`, `OIDC_AUDIENCE`, and either `OIDC_JWKS_URI` or inline `OIDC_JWKS_JSON`.

Preflight against the real cloud env file before first deploy:

```bash
python scripts/cloud_preflight.py /opt/workforceiq/.env.cloud
```

## Manual Deploy

```bash
docker compose -f docker-compose.cloud.yml --env-file .env.cloud up -d
docker compose -f docker-compose.cloud.yml --env-file .env.cloud ps
curl -fsS https://$APP_DOMAIN/api/health
curl -fsS https://$APP_DOMAIN/api/health/ready
```

For an authenticated smoke test in a production-like environment where dev auth is disabled:

```bash
python scripts/smoke_test.py \
  --base-url https://$APP_DOMAIN \
  --require-ready \
  --require-auth \
  --organization-id org-demo \
  --login-email hr@example.com \
  --login-password 'replace-with-real-password'
```

For config validation from the repo without creating `.env.cloud`:

```bash
WORKFORCEIQ_CONTAINER_ENV_FILE=env.cloud.example \
  docker compose -f cloud/compose/docker-compose.cloud.yml \
  --env-file cloud/compose/env.cloud.example config
```

## GitHub Actions Deploy

The workflow is `.github/workflows/cloud-deploy.yml`. Add these repository secrets:

- `CLOUD_HOST`: server IP or hostname.
- `CLOUD_USER`: SSH username.
- `CLOUD_SSH_KEY`: private SSH key with access to the server.
- `CLOUD_APP_DIR`: server path, for example `/opt/workforceiq`.

On the server, create `.env.cloud` manually before the first deploy. Then run the workflow manually and type `DEPLOY` in the confirmation input.

## Backups

Use `docs/backup-restore-runbook.md` for MySQL backups and restore drills. The cloud compose file mounts `./backups` into the MySQL container at `/backups`.

## Production Notes

This is good for a private beta or early startup deployment. For enterprise scale, move MySQL, Redis, backups, logs, and secrets to managed cloud services.
