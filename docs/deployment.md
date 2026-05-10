# Deployment

WorkforceIQ now has three supported local/deployment paths.

## Local Python

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python scripts\seed_demo_data.py
python run.py
```

## Development Containers

Use this when you want parity with the v3 architecture: Flask, MySQL, Redis, Elasticsearch, Celery, and Flower.

```powershell
docker compose -f docker-compose.dev.yml up --build
```

The API runs on `http://127.0.0.1:5000` and Flower runs on `http://127.0.0.1:5555`.

Elasticsearch is optional because the API has a SQL search fallback. To enable it:

```powershell
docker compose -f docker-compose.dev.yml --profile search up --build
```

## Production Container Shape

`Dockerfile` runs the app through Gunicorn and expects production-grade environment variables.

Required production settings:
- `WORKFORCEIQ_CONFIG=production`
- Strong `SECRET_KEY` and `JWT_SECRET_KEY`
- MySQL `DATABASE_URL`
- `ENABLE_DEV_AUTH=false`
- Redis URL for Celery and rate limiting
- `CORS_ORIGINS` set to approved frontend origins
- Optional `ELASTICSEARCH_URL` for indexed employee search

```powershell
docker build -t workforceiq-api:local .
docker compose -f docker-compose.prod.yml up -d
```

For config-only validation without real secrets:

```powershell
$env:WORKFORCEIQ_ENV_FILE=".env.production.example"
docker compose -f docker-compose.prod.yml config
```

Production database, Redis, search, object storage, TLS, and backups should be managed services in a real company deployment. The production compose file is a deployable shape, not a substitute for managed infrastructure.

For recovery operations, follow `docs/backup-restore-runbook.md`.

## Database Migrations

Use Alembic through Flask-Migrate for every production schema change:

```powershell
flask db upgrade
flask db migrate -m "describe change"
```

`flask init-db` is only for local throwaway databases.

## Operational Jobs

```powershell
celery -A workforceiq.celery_app.celery worker --loglevel=info
python scripts\backup_database.py
```

## Smoke Checks

```powershell
python scripts\smoke_test.py --base-url http://127.0.0.1:5000
python scripts\smoke_test.py --base-url http://127.0.0.1:5000 --require-auth
```
