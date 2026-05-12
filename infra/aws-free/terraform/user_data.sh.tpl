#!/bin/bash
set -euxo pipefail

APP_DIR="/opt/workforceiq"
mkdir -p "$APP_DIR/backups"
chmod 0777 "$APP_DIR/backups"

dnf update -y
dnf install -y awscli docker jq python3 cronie
systemctl enable --now docker
systemctl enable --now crond
usermod -aG docker ec2-user || true

if ! docker compose version >/dev/null 2>&1; then
  mkdir -p /usr/local/lib/docker/cli-plugins
  curl -fsSL "https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-x86_64" \
    -o /usr/local/lib/docker/cli-plugins/docker-compose
  chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
fi

cat > "$APP_DIR/docker-compose.free.yml.b64" <<'EOF'
${docker_compose_b64}
EOF
base64 -d "$APP_DIR/docker-compose.free.yml.b64" > "$APP_DIR/docker-compose.free.yml"
rm -f "$APP_DIR/docker-compose.free.yml.b64"

cat > "$APP_DIR/nginx.conf.b64" <<'EOF'
${nginx_conf_b64}
EOF
base64 -d "$APP_DIR/nginx.conf.b64" > "$APP_DIR/nginx.conf"
rm -f "$APP_DIR/nginx.conf.b64"

cat > "$APP_DIR/.env.free.b64" <<'EOF'
${env_file_b64}
EOF
base64 -d "$APP_DIR/.env.free.b64" > "$APP_DIR/.env.free"
rm -f "$APP_DIR/.env.free.b64"
chmod 0600 "$APP_DIR/.env.free"

aws ecr get-login-password --region "${aws_region}" \
  | docker login --username AWS --password-stdin "${ecr_registry}"

cd "$APP_DIR"
if docker compose -f docker-compose.free.yml --env-file .env.free pull; then
  docker compose -f docker-compose.free.yml --env-file .env.free up -d
else
  echo "WorkforceIQ image is not available yet. Push the image to ECR and restart with SSM."
fi

cat > /usr/local/bin/workforceiq-free-backup <<'EOF'
#!/bin/bash
set -euo pipefail
cd /opt/workforceiq
mkdir -p backups
docker compose -f docker-compose.free.yml --env-file .env.free exec -T app python scripts/backup_database.py
find backups -name "workforceiq-backup-*.json" -type f -mtime +${backup_retention_days} -delete
EOF
chmod +x /usr/local/bin/workforceiq-free-backup

cat > /etc/cron.d/workforceiq-free-backup <<'EOF'
SHELL=/bin/bash
15 2 * * * root /usr/local/bin/workforceiq-free-backup >> /var/log/workforceiq-free-backup.log 2>&1
EOF
