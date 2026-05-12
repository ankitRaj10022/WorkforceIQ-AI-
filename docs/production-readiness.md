# Production Readiness

This repo is now organized around three gates.

## Testing Gate

Required before merge:
- `python -m ruff check .`
- `python -m bandit -c pyproject.toml -r workforceiq scripts`
- `python -m pytest`
- Coverage must stay at or above 80%.

## Deployment Gate

Required before staging:
- Build Docker image successfully.
- Run `/api/health` smoke check.
- Run `/api/health/ready` and confirm dependency readiness is green.
- Confirm `WORKFORCEIQ_CONFIG=production`.
- Confirm production secrets are set and not placeholders.
- Confirm `DATABASE_URL` points to MySQL, not SQLite.
- Confirm `ENABLE_DEV_AUTH=false`.

## Production Gate

Required before real customer data:
- Run Alembic migrations with `flask db upgrade`; never use `db.create_all()` against production.
- Use `/api/auth/login`, `/api/auth/sso/exchange`, `/api/auth/refresh`, and `/api/auth/logout` with persisted `user_accounts`, MFA, account lockout, and session revocation; keep `/api/auth/token` disabled in production.
- Use Redis-backed rate limiting with tenant-aware keys; memory fallback is development-only.
- Use tenant-scoped employee search; set `ELASTICSEARCH_URL` to enable the Elasticsearch backend.
- Run Celery workers for ML prediction refresh, search indexing, and scheduled report hooks.
- Keep structured JSON logs and audit logs in centralized retention.
- Run `python scripts/backup_database.py` and complete a restore drill before onboarding customer data.
- Run `python scripts/verify_backup.py <backup_path>` against the latest redacted audit export before operational sign-off.
- Use `/api/compliance/requests` for data export, deletion, and rectification workflows.

Remaining hardening before a paid enterprise launch:
- Add SAML, SCIM provisioning, and IdP group-to-role mapping on top of the current OIDC exchange flow.
- Add real ML model artifacts and SHAP explanations instead of deterministic task placeholders.
- Add full restore automation, immutable backup storage, and disaster recovery RTO/RPO targets.
- Add organization provisioning, billing, and tenant admin screens.
