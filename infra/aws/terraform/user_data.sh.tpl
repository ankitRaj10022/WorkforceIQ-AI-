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

cat > "$APP_DIR/docker-compose.aws.yml.b64" <<'EOF'
${docker_compose_b64}
EOF
base64 -d "$APP_DIR/docker-compose.aws.yml.b64" > "$APP_DIR/docker-compose.aws.yml"
rm -f "$APP_DIR/docker-compose.aws.yml.b64"

cat > "$APP_DIR/nginx.conf.b64" <<'EOF'
${nginx_conf_b64}
EOF
base64 -d "$APP_DIR/nginx.conf.b64" > "$APP_DIR/nginx.conf"
rm -f "$APP_DIR/nginx.conf.b64"

curl -fsSL "https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem" \
  -o "$APP_DIR/global-bundle.pem"

aws secretsmanager get-secret-value \
  --region "${aws_region}" \
  --secret-id "${secret_arn}" \
  --query SecretString \
  --output text > "$APP_DIR/secret.json"

python3 - <<'PY' > "$APP_DIR/.env.aws"
import json
from pathlib import Path

secret = json.loads(Path("/opt/workforceiq/secret.json").read_text(encoding="utf-8"))
for key, value in sorted(secret.items()):
    print(f"{key}={value}")
PY
chmod 0600 "$APP_DIR/.env.aws"
rm -f "$APP_DIR/secret.json"

aws ecr get-login-password --region "${aws_region}" \
  | docker login --username AWS --password-stdin "${ecr_registry}"

cd "$APP_DIR"
if docker compose -f docker-compose.aws.yml --env-file .env.aws pull; then
  docker compose -f docker-compose.aws.yml --env-file .env.aws up -d
else
  echo "WorkforceIQ image is not available yet. Push the image to ECR and redeploy through SSM."
fi

cat > /usr/local/bin/workforceiq-backup <<'EOF'
#!/bin/bash
set -euo pipefail
cd /opt/workforceiq
set -a
source .env.aws
set +a
mkdir -p backups
docker compose -f docker-compose.aws.yml --env-file .env.aws exec -T app python scripts/backup_database.py
latest="$(ls -t backups/workforceiq-backup-*.json | head -n1)"
aws s3 cp "$latest" "s3://$${BACKUP_BUCKET}/json/$(basename "$latest")" --region "$${AWS_REGION}"
EOF
chmod +x /usr/local/bin/workforceiq-backup

cat > /etc/cron.d/workforceiq-backup <<'EOF'
SHELL=/bin/bash
15 2 * * * root /usr/local/bin/workforceiq-backup >> /var/log/workforceiq-backup.log 2>&1
EOF
