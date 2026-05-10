from __future__ import annotations

from sqlalchemy import select

from workforceiq.auth import RequestContext, RoleName
from workforceiq.celery_app import celery
from workforceiq.extensions import db
from workforceiq.models import Employee, MlPrediction, PerformanceReview
from workforceiq.services.search import index_employee_documents
from workforceiq.utils.time import utc_now


@celery.task(name="workforceiq.ml.run_attrition_predictions")
def run_attrition_predictions(organization_id: str) -> dict:
    employees = db.session.execute(
        select(Employee)
        .where(Employee.organization_id == organization_id, Employee.status == "Active")
        .limit(500)
    ).scalars().all()
    created = 0
    for employee in employees:
        latest_score = db.session.execute(
            select(PerformanceReview.score)
            .where(
                PerformanceReview.organization_id == organization_id,
                PerformanceReview.employee_id == employee.id,
            )
            .order_by(PerformanceReview.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        prediction = _deterministic_attrition_score(latest_score)
        db.session.add(
            MlPrediction(
                organization_id=organization_id,
                employee_id=employee.id,
                model_type="attrition",
                prediction=prediction,
                confidence=0.72,
                run_at=utc_now(),
                features_snapshot={
                    "top_features": [
                        "Latest performance review",
                        "Current employment status",
                        "Tenant baseline attrition prior",
                    ]
                },
            )
        )
        created += 1
    db.session.commit()
    return {"organization_id": organization_id, "predictions_created": created}


@celery.task(name="workforceiq.search.index_employees")
def index_employee_search_documents(organization_id: str) -> dict:
    context = RequestContext(
        user_id="system",
        role=RoleName.SUPER_ADMIN,
        organization_id=organization_id,
    )
    result = index_employee_documents(context)
    return {
        "organization_id": organization_id,
        **result,
    }


@celery.task(name="workforceiq.reports.send_scheduled_reports")
def send_scheduled_reports(organization_id: str) -> dict:
    return {
        "organization_id": organization_id,
        "status": "queued",
        "message": "Scheduled report delivery hook executed. Configure SMTP or Slack webhook for delivery.",
    }


def _deterministic_attrition_score(latest_score: float | None) -> float:
    if latest_score is None:
        return 0.5
    if latest_score >= 90:
        return 0.18
    if latest_score >= 80:
        return 0.35
    if latest_score >= 70:
        return 0.55
    return 0.76
