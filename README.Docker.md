# Docker Usage

This repository supports three Docker-driven workflows.

## Default local stack

Use the root [compose.yaml](compose.yaml) when you want the fastest local developer setup with:

- Flask API
- MySQL 8
- Redis
- Celery worker
- Flower
- optional Elasticsearch profile

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Endpoints:

- API: `http://127.0.0.1:5000`
- Flower: `http://127.0.0.1:5555`

Optional search stack:

```powershell
docker compose --profile search up --build
```

## Explicit development compose

If you want to call the named development file directly:

```powershell
docker compose -f docker-compose.dev.yml up --build
```

For config-only validation without a local `.env`:

```powershell
$env:WORKFORCEIQ_ENV_FILE=".env.example"
docker compose -f docker-compose.dev.yml config
```

## Production-shaped compose

Use [docker-compose.prod.yml](docker-compose.prod.yml) only for production-shape validation or controlled staging. It expects real production secrets and a production-safe environment file.

```powershell
Copy-Item .env.production.example .env.production
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

Config-only validation:

```powershell
$env:WORKFORCEIQ_ENV_FILE=".env.production.example"
docker compose -f docker-compose.prod.yml config
```

## Provider-neutral cloud VM stack

For a single Linux VM deployment with HTTPS termination through Caddy, use the files under [cloud/compose](cloud/compose).

Primary references:

- [docs/cloud-deployment.md](docs/cloud-deployment.md)
- [cloud/compose/README.md](cloud/compose/README.md)

## Notes

- The default compose stack is for developer productivity, not enterprise production.
- Real production should use managed data services, centralized logs, monitored backups, and hardened DNS/TLS.
- For backup and restore procedures, follow [docs/backup-restore-runbook.md](docs/backup-restore-runbook.md).
