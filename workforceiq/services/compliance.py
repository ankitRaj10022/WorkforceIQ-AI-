from __future__ import annotations

from sqlalchemy import select

from workforceiq.audit import record_audit_log
from workforceiq.auth import RequestContext, RoleName, authorize_audit_log_read, authorize_compliance_request
from workforceiq.errors import NotFoundError, ValidationError
from workforceiq.extensions import db
from workforceiq.models import AuditLog, ComplianceRequest, Employee, MlPrediction, PerformanceReview
from workforceiq.utils.time import to_utc_iso

ALLOWED_REQUEST_TYPES = {"DATA_EXPORT", "DATA_DELETION", "RECTIFICATION"}


def create_compliance_request(context: RequestContext, payload: dict) -> dict:
    request_type = str(payload.get("request_type") or "").upper()
    employee_id = str(payload.get("employee_id") or context.employee_id or "")
    if request_type not in ALLOWED_REQUEST_TYPES:
        allowed = ", ".join(sorted(ALLOWED_REQUEST_TYPES))
        raise ValidationError(f"`request_type` is invalid. Allowed values: {allowed}.")
    if not employee_id:
        raise ValidationError("`employee_id` is required.")

    employee = _employee_for_context(context, employee_id)
    authorize_compliance_request(context, employee.id)

    compliance_request = ComplianceRequest(
        organization_id=context.organization_id,
        request_type=request_type,
        subject_employee_id=employee.id,
        requested_by=context.user_id,
        reason=payload.get("reason"),
        metadata_json={"source": "api"},
    )
    db.session.add(compliance_request)
    record_audit_log(
        user_id=context.user_id,
        organization_id=context.organization_id,
        action="CREATE",
        target_entity="compliance_requests",
        target_id=employee.id,
        fields_changed=["request_type", "subject_employee_id"],
        old_values={},
        new_values={"request_type": request_type, "subject_employee_id": employee.id},
    )
    db.session.commit()

    response = _serialize_compliance_request(compliance_request)
    if request_type == "DATA_EXPORT":
        response["export"] = build_employee_data_export(context, employee.id)
    return response


def list_compliance_requests(context: RequestContext, limit: int) -> dict:
    authorize_audit_log_read(context)
    row_limit = min(max(limit, 1), 500)
    rows = db.session.execute(
        select(ComplianceRequest)
        .where(ComplianceRequest.organization_id == context.organization_id)
        .order_by(ComplianceRequest.created_at.desc())
        .limit(row_limit)
    ).scalars().all()
    return {
        "requests": [_serialize_compliance_request(row) for row in rows],
        "limit": row_limit,
    }


def build_employee_data_export(context: RequestContext, employee_id: str) -> dict:
    employee = _employee_for_context(context, employee_id)
    authorize_compliance_request(context, employee.id)
    reviews = db.session.execute(
        select(PerformanceReview)
        .where(
            PerformanceReview.organization_id == context.organization_id,
            PerformanceReview.employee_id == employee.id,
        )
        .order_by(PerformanceReview.created_at.desc())
        .limit(500)
    ).scalars().all()
    predictions = db.session.execute(
        select(MlPrediction)
        .where(
            MlPrediction.organization_id == context.organization_id,
            MlPrediction.employee_id == employee.id,
        )
        .order_by(MlPrediction.run_at.desc())
        .limit(500)
    ).scalars().all()
    audit_logs = []
    if context.role in {RoleName.SUPER_ADMIN, RoleName.AUDITOR, RoleName.HR_MANAGER}:
        audit_logs = db.session.execute(
            select(AuditLog)
            .where(
                AuditLog.organization_id == context.organization_id,
                AuditLog.target_entity == "employees",
                AuditLog.target_id == employee.id,
            )
            .order_by(AuditLog.timestamp.desc())
            .limit(500)
        ).scalars().all()

    return {
        "employee": {
            "id": employee.id,
            "name": employee.name,
            "email": employee.email,
            "department_id": employee.department_id,
            "role_id": employee.role_id,
            "hire_date": employee.hire_date.isoformat(),
            "status": employee.status,
            "source": "employees",
        },
        "performance_reviews": [
            {
                "period": review.period,
                "score": review.score,
                "reviewer_id": review.reviewer_id,
                "created_at": to_utc_iso(review.created_at),
                "source": "performance_reviews",
            }
            for review in reviews
        ],
        "ml_predictions": [
            {
                "model_type": prediction.model_type,
                "prediction": prediction.prediction,
                "confidence": prediction.confidence,
                "run_at": to_utc_iso(prediction.run_at),
                "source": "ml_predictions",
            }
            for prediction in predictions
        ],
        "audit_logs": [
            {
                "action": audit.action,
                "target_entity": audit.target_entity,
                "target_id": audit.target_id,
                "timestamp": to_utc_iso(audit.timestamp),
                "metadata": audit.metadata_json,
                "source": "audit_logs",
            }
            for audit in audit_logs
        ],
    }


def _employee_for_context(context: RequestContext, employee_id: str) -> Employee:
    employee = db.session.execute(
        select(Employee)
        .where(Employee.id == employee_id, Employee.organization_id == context.organization_id)
        .limit(1)
    ).scalar_one_or_none()
    if employee is None:
        raise NotFoundError(f"No employee record found for `{employee_id}`. Try searching by ID or checking the spelling.")
    return employee


def _serialize_compliance_request(row: ComplianceRequest) -> dict:
    return {
        "id": row.id,
        "organization_id": row.organization_id,
        "request_type": row.request_type,
        "subject_employee_id": row.subject_employee_id,
        "requested_by": row.requested_by,
        "status": row.status,
        "created_at": to_utc_iso(row.created_at),
        "completed_at": to_utc_iso(row.completed_at) if row.completed_at else None,
    }
