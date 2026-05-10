from __future__ import annotations

import time

from tests.conftest import auth_header
from workforceiq.extensions import db
from workforceiq.maintenance import export_database_backup
from workforceiq.models import AuditLog, MlPrediction, UserAccount, UserSession
from workforceiq.rate_limit import RateLimiter, rate_limit_key_from_request
from workforceiq.security import mfa
from workforceiq.tasks import index_employee_search_documents, run_attrition_predictions, send_scheduled_reports


def test_real_login_creates_session_and_audit_log(client, app):
    response = client.post(
        "/api/auth/login",
        json={
            "organization_id": "org-demo",
            "email": "hr@example.com",
            "password": "CorrectHorseBatteryStaple!23",
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["user"]["role"] == "HR_MANAGER"
    assert body["access_token"]
    with app.app_context():
        assert UserSession.query.count() == 1
        assert AuditLog.query.filter_by(action="LOGIN", target_entity="user_accounts").count() == 1


def test_real_login_locks_account_after_repeated_failures(client, app):
    for _attempt in range(5):
        response = client.post(
            "/api/auth/login",
            json={"organization_id": "org-demo", "email": "hr@example.com", "password": "wrong"},
        )
        assert response.status_code == 403

    response = client.post(
        "/api/auth/login",
        json={
            "organization_id": "org-demo",
            "email": "hr@example.com",
            "password": "CorrectHorseBatteryStaple!23",
        },
    )

    assert response.status_code == 403
    assert "locked" in response.get_json()["error"]
    with app.app_context():
        assert db.session.get(UserAccount, 1).locked_until is not None


def test_mfa_setup_and_verify_flow(client):
    login = client.post(
        "/api/auth/login",
        json={
            "organization_id": "org-demo",
            "email": "hr@example.com",
            "password": "CorrectHorseBatteryStaple!23",
        },
    )
    token = login.get_json()["access_token"]

    setup = client.post("/api/auth/mfa/setup", headers=auth_header(token))
    assert setup.status_code == 200
    secret = setup.get_json()["mfa_secret"]
    code = mfa._totp(secret, int(time.time()))

    verify = client.post("/api/auth/mfa/verify", headers=auth_header(token), json={"code": code})

    assert verify.status_code == 200
    assert verify.get_json()["mfa_enabled"] is True
    missing_code_login = client.post(
        "/api/auth/login",
        json={
            "organization_id": "org-demo",
            "email": "hr@example.com",
            "password": "CorrectHorseBatteryStaple!23",
        },
    )
    assert missing_code_login.status_code == 403
    with_code_login = client.post(
        "/api/auth/login",
        json={
            "organization_id": "org-demo",
            "email": "hr@example.com",
            "password": "CorrectHorseBatteryStaple!23",
            "mfa_code": mfa._totp(secret, int(time.time())),
        },
    )
    assert with_code_login.status_code == 200


def test_employee_search_is_tenant_and_role_scoped(client, token_for):
    hr_token = token_for("hr-manager-1")
    employee_token = token_for("employee-priya")

    hr_response = client.get("/api/search/employees?q=engineering", headers=auth_header(hr_token))
    employee_response = client.get("/api/search/employees?q=ravi", headers=auth_header(employee_token))

    assert hr_response.status_code == 200
    assert hr_response.get_json()["results"][0]["department"] == "Engineering"
    assert employee_response.status_code == 200
    assert employee_response.get_json()["results"] == []


def test_compliance_export_request_and_audit_listing(client, token_for):
    hr_token = token_for("hr-manager-1")
    auditor_token = token_for("auditor-1")

    created = client.post(
        "/api/compliance/requests",
        headers=auth_header(hr_token),
        json={"request_type": "DATA_EXPORT", "employee_id": "EMP-0841", "reason": "employee request"},
    )
    listed = client.get("/api/compliance/requests", headers=auth_header(auditor_token))
    logs = client.get("/api/audit-logs", headers=auth_header(auditor_token))

    assert created.status_code == 201
    assert created.get_json()["export"]["employee"]["id"] == "EMP-0841"
    assert listed.status_code == 200
    assert listed.get_json()["requests"][0]["request_type"] == "DATA_EXPORT"
    assert logs.status_code == 200
    assert logs.get_json()["audit_logs"][0]["target_entity"] == "compliance_requests"


def test_rate_limiter_memory_backend_and_jwt_claim_key(app, client):
    token = client.post("/api/auth/token", json={"user_id": "hr-manager-1"}).get_json()["access_token"]
    key, claims = rate_limit_key_from_request(
        authorization_header=f"Bearer {token}",
        remote_addr="127.0.0.1",
        organization_hint="fallback-org",
    )
    limiter = RateLimiter(app)

    first = limiter.hit(key, limit=1)
    second = limiter.hit(key, limit=1)

    assert claims["organization_id"] == "org-demo"
    assert first.allowed is True
    assert second.allowed is False
    assert second.backend in {"memory", "redis_unavailable"}


def test_backup_export_redacts_account_secrets(app, tmp_path):
    output = tmp_path / "backup.json"
    with app.app_context():
        result = export_database_backup(output)

    content = output.read_text(encoding="utf-8")
    assert result["tables"]["employees"] == 3
    assert "[REDACTED]" in content
    assert "CorrectHorseBatteryStaple" not in content


def test_celery_task_functions_run_inside_app_context(app):
    with app.app_context():
        before = MlPrediction.query.filter_by(model_type="attrition").count()
        ml_result = run_attrition_predictions.run("org-demo")
        search_result = index_employee_search_documents.run("org-demo")
        report_result = send_scheduled_reports.run("org-demo")
        after = MlPrediction.query.filter_by(model_type="attrition").count()

    assert ml_result["predictions_created"] == 3
    assert after == before + 3
    assert search_result["documents_prepared"] == 3
    assert report_result["status"] == "queued"
