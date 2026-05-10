from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required
from sqlalchemy import select

from workforceiq.auth import authorize_audit_log_read, build_request_context, resolve_dev_identity
from workforceiq.errors import ValidationError
from workforceiq.extensions import db
from workforceiq.models import AuditLog
from workforceiq.services import (
    fetch_employee_profile,
    generate_attrition_risk_report,
    generate_department_health_check,
    update_employee,
)
from workforceiq.services.authentication import login_user, setup_mfa, verify_mfa_setup
from workforceiq.services.compliance import create_compliance_request, list_compliance_requests
from workforceiq.services.search import search_employees
from workforceiq.utils.time import to_utc_iso, utc_now

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.get("/health")
def health_check():
    return jsonify(
        {
            "service": "WorkforceIQ AI",
            "status": "ok",
            "timestamp": to_utc_iso(utc_now()),
            "auth_mode": "JWT",
            "version": current_app.config["APP_VERSION"],
            "environment": current_app.config["ENV_NAME"],
        }
    )


@api_bp.post("/auth/token")
def issue_dev_token():
    if not current_app.config["ENABLE_DEV_AUTH"]:
        raise ValidationError("Dev auth is disabled in this environment.")

    payload = request.get_json(silent=True) or {}
    identity = resolve_dev_identity(
        user_id=payload.get("user_id"),
        requested_role=payload.get("role"),
        requested_department_id=payload.get("department_id"),
        requested_employee_id=payload.get("employee_id"),
    )
    current_app.logger.warning(
        "[DEV_AUTH_BYPASS] %s requested dev token for %s at %s",
        identity["role"].value,
        identity["user_id"],
        to_utc_iso(utc_now()),
    )

    token = create_access_token(
        identity=identity["user_id"],
        additional_claims={
            "user_id": identity["user_id"],
            "organization_id": identity["organization_id"],
            "role": identity["role"].value,
            "department_id": identity["department_id"],
            "employee_id": identity["employee_id"],
        },
    )
    return jsonify(
        {
            "access_token": token,
            "role": identity["role"].value,
            "user_id": identity["user_id"],
            "organization_id": identity["organization_id"],
        }
    )


@api_bp.post("/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    return jsonify(login_user(payload))


@api_bp.post("/auth/mfa/setup")
@jwt_required()
def mfa_setup():
    context = build_request_context()
    return jsonify(setup_mfa(context))


@api_bp.post("/auth/mfa/verify")
@jwt_required()
def mfa_verify():
    context = build_request_context()
    payload = request.get_json(silent=True) or {}
    return jsonify(verify_mfa_setup(context, payload))


@api_bp.get("/employees/<employee_id>")
@jwt_required()
def get_employee(employee_id: str):
    context = build_request_context()
    return jsonify(fetch_employee_profile(employee_id, context))


@api_bp.patch("/employees/<employee_id>")
@jwt_required()
def patch_employee(employee_id: str):
    context = build_request_context()
    payload = request.get_json(silent=True) or {}
    return jsonify(update_employee(employee_id, context, payload))


@api_bp.get("/departments/<int:department_id>/health")
@jwt_required()
def department_health_check(department_id: int):
    context = build_request_context()
    return jsonify(generate_department_health_check(context, department_id))


@api_bp.get("/reports/attrition-risk")
@jwt_required()
def attrition_risk_report():
    context = build_request_context()
    department_id = request.args.get("department_id", type=int)
    limit = request.args.get("limit", type=int)
    return jsonify(generate_attrition_risk_report(context, department_id=department_id, limit=limit))


@api_bp.get("/search/employees")
@jwt_required()
def employee_search():
    context = build_request_context()
    query = request.args.get("q", "")
    limit = request.args.get("limit", type=int)
    return jsonify(search_employees(context, query=query, limit=limit))


@api_bp.get("/audit-logs")
@jwt_required()
def audit_logs():
    context = build_request_context()
    authorize_audit_log_read(context)
    limit = min(request.args.get("limit", default=100, type=int), current_app.config["MAX_EXPORT_ROWS"])
    rows = db.session.execute(
        select(AuditLog)
        .where(AuditLog.organization_id == context.organization_id)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
    ).scalars().all()
    return jsonify(
        {
            "audit_logs": [
                {
                    "id": row.id,
                    "action": row.action,
                    "target_entity": row.target_entity,
                    "target_id": row.target_id,
                    "timestamp": to_utc_iso(row.timestamp),
                    "metadata": row.metadata_json,
                    "request_id": row.request_id,
                }
                for row in rows
            ],
            "limit": limit,
        }
    )


@api_bp.post("/compliance/requests")
@jwt_required()
def compliance_request_create():
    context = build_request_context()
    payload = request.get_json(silent=True) or {}
    return jsonify(create_compliance_request(context, payload)), 201


@api_bp.get("/compliance/requests")
@jwt_required()
def compliance_request_list():
    context = build_request_context()
    limit = request.args.get("limit", default=100, type=int)
    return jsonify(list_compliance_requests(context, limit))
