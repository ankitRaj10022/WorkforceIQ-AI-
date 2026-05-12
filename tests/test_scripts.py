from __future__ import annotations

import json

from scripts import cloud_preflight, smoke_test
from workforceiq.maintenance import REDACTION_MARKER, export_database_backup, verify_database_backup


def test_cloud_preflight_accepts_realistic_cloud_values():
    values = {
        "WORKFORCEIQ_CONFIG": "production",
        "SECRET_KEY": "a" * 64,
        "JWT_SECRET_KEY": "b" * 64,
        "DATABASE_URL": "mysql+pymysql://workforceiq:supersecretpassword@db.internal:3306/workforceiq",
        "REDIS_URL": "redis://redis:6379/0",
        "CELERY_BROKER_URL": "redis://redis:6379/0",
        "CELERY_RESULT_BACKEND": "redis://redis:6379/0",
        "CORS_ORIGINS": "https://app.workforceiq.company",
        "APP_DOMAIN": "api.workforceiq.company",
        "ACME_EMAIL": "platform@workforceiq.company",
        "MYSQL_ROOT_PASSWORD": "root-password-strong",
        "MYSQL_PASSWORD": "user-password-strong",
        "ENABLE_DEV_AUTH": "false",
    }

    assert cloud_preflight.validate_values(values) == []


def test_cloud_preflight_rejects_placeholder_cloud_values():
    values = {
        "WORKFORCEIQ_CONFIG": "production",
        "SECRET_KEY": "change-me-please-use-a-long-random-secret",
        "JWT_SECRET_KEY": "change-me-please-use-a-long-random-secret",
        "DATABASE_URL": "sqlite:///workforceiq.db",
        "REDIS_URL": "redis://redis:6379/0",
        "CELERY_BROKER_URL": "redis://broker:6379/0",
        "CELERY_RESULT_BACKEND": "redis://backend:6379/0",
        "CORS_ORIGINS": "http://localhost:3000",
        "APP_DOMAIN": "workforceiq.example.com",
        "ACME_EMAIL": "admin@example.com",
        "MYSQL_ROOT_PASSWORD": "replace-root-password",
        "MYSQL_PASSWORD": "replace-mysql-password",
        "ENABLE_DEV_AUTH": "true",
    }

    errors = cloud_preflight.validate_values(values)

    assert any("ENABLE_DEV_AUTH must be false." in error for error in errors)
    assert any("DATABASE_URL must not use SQLite." in error for error in errors)
    assert any("APP_DOMAIN must be set to the real cloud DNS name" in error for error in errors)
    assert any("CORS_ORIGINS must point to the real frontend origin" in error for error in errors)


def test_smoke_test_uses_real_login_when_credentials_are_provided(monkeypatch):
    calls = []

    def fake_request_json(url, *, method="GET", payload=None, token=None):
        calls.append((url, method, payload, token))
        return 200, {"access_token": "jwt-token"}

    monkeypatch.setattr(smoke_test, "request_json", fake_request_json)

    result = smoke_test.acquire_access_token(
        "https://api.example.com",
        dev_user="hr-manager-1",
        organization_id="org-demo",
        login_email="hr@example.com",
        login_password="CorrectHorseBatteryStaple!23",
        mfa_code="123456",
    )

    assert result.mode == "login"
    assert result.status == 200
    assert calls == [
        (
            "https://api.example.com/api/auth/login",
            "POST",
            {
                "organization_id": "org-demo",
                "email": "hr@example.com",
                "password": "CorrectHorseBatteryStaple!23",
                "mfa_code": "123456",
            },
            None,
        )
    ]


def test_smoke_test_returns_validation_error_for_partial_login_credentials():
    result = smoke_test.acquire_access_token(
        "https://api.example.com",
        dev_user=None,
        organization_id="org-demo",
        login_email="hr@example.com",
        login_password=None,
        mfa_code=None,
    )

    assert result.mode == "login"
    assert result.status == 400
    assert "required" in result.body["error"]


def test_verify_database_backup_accepts_valid_redacted_export(app, tmp_path):
    output = tmp_path / "backup.json"
    with app.app_context():
        export_database_backup(output)

    result = verify_database_backup(output)

    assert result["format"] == "workforceiq-json-backup-v1"
    assert result["tables"]["user_accounts"] >= 1


def test_verify_database_backup_rejects_unredacted_password_hash(tmp_path):
    backup_path = tmp_path / "invalid-backup.json"
    payload = {
        "format": "workforceiq-json-backup-v1",
        "generated_at": "2026-05-11T00:00:00Z",
        "tables": {
            "organizations": [],
            "departments": [],
            "roles": [],
            "employees": [],
            "performance_reviews": [],
            "rbac_roles": [],
            "user_sessions": [{"refresh_token_jti": REDACTION_MARKER}],
            "audit_logs": [],
            "ml_predictions": [],
            "user_accounts": [{"password_hash": "plaintext", "mfa_secret": None}],
            "compliance_requests": [],
        },
    }
    backup_path.write_text(json.dumps(payload), encoding="utf-8")

    try:
        verify_database_backup(backup_path)
    except ValueError as exc:
        assert "password_hash" in str(exc)
    else:  # pragma: no cover - explicit failure branch
        raise AssertionError("verify_database_backup should reject unredacted password hashes")
