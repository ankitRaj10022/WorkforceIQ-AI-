#!/bin/bash
set -euxo pipefail

APP_DIR=/opt/workforceiq
ECR_REGISTRY=187528943333.dkr.ecr.us-east-1.amazonaws.com
IMAGE_URI=187528943333.dkr.ecr.us-east-1.amazonaws.com/workforceiq-free:latest

SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
JWT_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
MYSQL_ROOT_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
MYSQL_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_hex(16))')"

dnf install -y docker cronie python3
systemctl enable --now docker
systemctl enable --now crond

if ! docker compose version >/dev/null 2>&1; then
  mkdir -p /usr/local/lib/docker/cli-plugins
  curl -fsSL https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-x86_64 \
    -o /usr/local/lib/docker/cli-plugins/docker-compose
  chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
fi

mkdir -p "$APP_DIR/backups"
chmod 0777 "$APP_DIR/backups"

cat > "$APP_DIR/.env.free" <<ENVEOF
WORKFORCEIQ_CONFIG=production
FLASK_APP=run.py
APP_VERSION=3.0.0
COMPANY_NAME=WorkforceIQ
DEFAULT_ORGANIZATION_ID=org-demo
SECRET_KEY=$SECRET_KEY
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ACCESS_TOKEN_EXPIRES=900
JWT_REFRESH_TOKEN_EXPIRES=2592000
DATABASE_URL=mysql+pymysql://workforceiq:$MYSQL_PASSWORD@mysql:3306/workforceiq
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
WEB_CONCURRENCY=2
GUNICORN_THREADS=2
CELERY_CONCURRENCY=1
ENABLE_DEV_AUTH=false
RATE_LIMIT_BACKEND=redis
RATE_LIMIT_PER_MINUTE=100
AUTH_LOCKOUT_THRESHOLD=5
AUTH_LOCKOUT_MINUTES=15
OIDC_ENABLED=false
OIDC_ISSUER=
OIDC_AUDIENCE=
OIDC_JWKS_URI=
OIDC_JWKS_JSON=
OIDC_CLOCK_SKEW_SECONDS=60
OIDC_REQUIRE_VERIFIED_EMAIL=true
MAX_EXPORT_ROWS=500
ML_STALE_DAYS=30
CORS_ORIGINS=http://localhost:3000
LOG_LEVEL=INFO
STRUCTURED_LOGS=true
BACKUP_DIRECTORY=backups
WORKFORCEIQ_IMAGE=$IMAGE_URI
MYSQL_ROOT_PASSWORD=$MYSQL_ROOT_PASSWORD
MYSQL_PASSWORD=$MYSQL_PASSWORD
ENVEOF

cat > "$APP_DIR/docker-compose.free.yml" <<'COMPOSEEOF'
services:
  nginx:
    image: nginx:1.27-alpine
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      app:
        condition: service_healthy

  app:
    image: ${WORKFORCEIQ_IMAGE}
    restart: unless-stopped
    env_file:
      - .env.free
    volumes:
      - ./backups:/app/backups
    command: sh -c "flask db upgrade && gunicorn -c gunicorn.conf.py run:app"
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/api/health', timeout=3).read()\""]
      interval: 30s
      timeout: 5s
      retries: 5
      start_period: 45s

  celery_worker:
    image: ${WORKFORCEIQ_IMAGE}
    restart: unless-stopped
    env_file:
      - .env.free
    command: sh -c "celery -A workforceiq.celery_app.celery worker --loglevel=info --concurrency=${CELERY_CONCURRENCY:-1}"
    depends_on:
      app:
        condition: service_healthy

  mysql:
    image: mysql:8.0
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: workforceiq
      MYSQL_USER: workforceiq
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD-SHELL", "mysqladmin ping -h localhost -uroot -p$${MYSQL_ROOT_PASSWORD}"]
      interval: 10s
      timeout: 5s
      retries: 10

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 10

volumes:
  mysql_data:
  redis_data:
COMPOSEEOF

cat > "$APP_DIR/nginx.conf" <<'NGINXEOF'
server {
    listen 80;
    server_tokens off;
    client_max_body_size 10m;

    location /api/health {
        proxy_pass http://app:5000/api/health;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://app:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Request-ID $request_id;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
NGINXEOF

aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin "$ECR_REGISTRY"

cd "$APP_DIR"
docker compose -f docker-compose.free.yml --env-file .env.free pull
docker compose -f docker-compose.free.yml --env-file .env.free up -d

cat > /usr/local/bin/workforceiq-free-backup <<'BACKEOF'
#!/bin/bash
set -euo pipefail
cd /opt/workforceiq
mkdir -p backups
docker compose -f docker-compose.free.yml --env-file .env.free exec -T app python scripts/backup_database.py
find backups -name "workforceiq-backup-*.json" -type f -mtime +7 -delete
BACKEOF

chmod +x /usr/local/bin/workforceiq-free-backup
printf 'SHELL=/bin/bash\n15 2 * * * root /usr/local/bin/workforceiq-free-backup >> /var/log/workforceiq-free-backup.log 2>&1\n' > /etc/cron.d/workforceiq-free-backup

docker compose -f docker-compose.free.yml --env-file .env.free ps
