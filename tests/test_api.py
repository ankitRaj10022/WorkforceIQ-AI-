from __future__ import annotations

from tests.conftest import auth_header
from workforceiq.extensions import db
from workforceiq.models import AuditLog, Employee


def test_health_endpoint_returns_security_headers(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json()["service"] == "WorkforceIQ AI"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Request-ID"]


def test_dev_token_rejects_role_escalation(client):
    response = client.post(
        "/api/auth/token",
        json={"user_id": "employee-priya", "role": "SUPER_ADMIN"},
    )

    assert response.status_code == 400
    assert "does not match" in response.get_json()["error"]


def test_protected_endpoint_requires_jwt(client):
    response = client.get("/api/employees/EMP-0841")

    assert response.status_code == 401


def test_hr_manager_can_read_employee_profile(client, token_for):
    token = token_for("hr-manager-1")

    response = client.get("/api/employees/EMP-0841", headers=auth_header(token))

    assert response.status_code == 200
    body = response.get_json()
    assert body["employee_profile"]["name"] == "Priya Sharma"
    assert body["employee_profile"]["department"]["source"] == "departments.id, departments.name"
    assert "employees.department_id = departments.id" in body["join_logic"]


def test_employee_cannot_read_other_profile(client, token_for):
    token = token_for("employee-priya")

    response = client.get("/api/employees/EMP-0112", headers=auth_header(token))

    assert response.status_code == 403


def test_employee_self_profile_hides_ml_predictions(client, token_for):
    token = token_for("employee-priya")

    response = client.get("/api/employees/EMP-0841", headers=auth_header(token))

    assert response.status_code == 200
    assert response.get_json()["ml_predictions"]["restricted"] is True


def test_update_employee_writes_audit_log(client, token_for, app):
    token = token_for("hr-manager-1")

    response = client.patch(
        "/api/employees/EMP-0841",
        headers=auth_header(token),
        json={"email": "priya.qa@example.com"},
    )

    assert response.status_code == 200
    assert response.get_json()["audit_log_written"] is True
    with app.app_context():
        employee = db.session.get(Employee, "EMP-0841")
        audit_log = AuditLog.query.one()
        assert employee.email == "priya.qa@example.com"
        assert audit_log.action == "UPDATE"
        assert audit_log.target_entity == "employees"
        assert audit_log.metadata_json["fields_changed"] == ["email"]


def test_update_employee_rejects_cross_department_role(client, token_for):
    token = token_for("super-admin-1")

    response = client.patch(
        "/api/employees/EMP-0841",
        headers=auth_header(token),
        json={"department_id": 2},
    )

    assert response.status_code == 400
    assert "belongs to department" in response.get_json()["error"]


def test_update_employee_rejects_duplicate_email(client, token_for):
    token = token_for("hr-manager-1")

    response = client.patch(
        "/api/employees/EMP-0841",
        headers=auth_header(token),
        json={"email": "ravi.patel@example.com"},
    )

    assert response.status_code == 400
    assert "already assigned" in response.get_json()["error"]


def test_update_employee_rejects_empty_name(client, token_for):
    token = token_for("hr-manager-1")

    response = client.patch(
        "/api/employees/EMP-0841",
        headers=auth_header(token),
        json={"name": "  "},
    )

    assert response.status_code == 400
    assert "cannot be empty" in response.get_json()["error"]


def test_update_employee_rejects_self_manager(client, token_for):
    token = token_for("super-admin-1")

    response = client.patch(
        "/api/employees/EMP-0841",
        headers=auth_header(token),
        json={"manager_id": "EMP-0841"},
    )

    assert response.status_code == 400
    assert "own manager" in response.get_json()["error"]


def test_employee_can_update_own_limited_profile(client, token_for, app):
    token = token_for("employee-priya")

    response = client.patch(
        "/api/employees/EMP-0841",
        headers=auth_header(token),
        json={"name": "Priya S."},
    )

    assert response.status_code == 200
    with app.app_context():
        employee = db.session.get(Employee, "EMP-0841")
        assert employee.name == "Priya S."


def test_employee_cannot_update_privileged_fields(client, token_for):
    token = token_for("employee-priya")

    response = client.patch(
        "/api/employees/EMP-0841",
        headers=auth_header(token),
        json={"status": "terminated"},
    )

    assert response.status_code == 403


def test_unknown_employee_returns_prompt_error_contract(client, token_for):
    token = token_for("hr-manager-1")

    response = client.get("/api/employees/EMP-404", headers=auth_header(token))

    assert response.status_code == 404
    assert "No employee record found" in response.get_json()["error"]


def test_attrition_report_rejects_invalid_limit(client, token_for):
    token = token_for("hr-manager-1")

    response = client.get("/api/reports/attrition-risk?limit=0", headers=auth_header(token))

    assert response.status_code == 400
    assert "invalid" in response.get_json()["error"]


def test_attrition_report_is_grouped_and_limited(client, token_for):
    token = token_for("hr-manager-1")

    response = client.get("/api/reports/attrition-risk?limit=2", headers=auth_header(token))

    assert response.status_code == 200
    body = response.get_json()
    assert "Engineering" in body["grouped_by_department"]
    assert body["financial_exposure"]["source_fields"] == [
        "ml_predictions.prediction",
        "roles.salary_band_min",
        "roles.salary_band_max",
    ]


def test_stale_prediction_flag_is_set(client, token_for):
    token = token_for("hr-manager-1")

    response = client.get("/api/employees/EMP-0841", headers=auth_header(token))

    assert response.status_code == 200
    attrition = response.get_json()["ml_predictions"]["attrition_risk"]
    assert attrition["stale"] is True
    assert attrition["warning"] == "[STALE - rerun recommended]"


def test_department_head_scope_is_enforced_for_reports(client, token_for):
    token = token_for("dept-head-eng-1")

    allowed = client.get("/api/departments/1/health", headers=auth_header(token))
    denied = client.get("/api/departments/2/health", headers=auth_header(token))

    assert allowed.status_code == 200
    assert denied.status_code == 403
