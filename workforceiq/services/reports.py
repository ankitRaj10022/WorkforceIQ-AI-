from __future__ import annotations

import statistics
from decimal import Decimal

from flask import current_app
from sqlalchemy import and_, func, select

from workforceiq.auth import RequestContext, authorize_attrition_report_read, authorize_department_report_read
from workforceiq.errors import NotFoundError, ValidationError
from workforceiq.extensions import db
from workforceiq.models import Department, Employee, MlPrediction, PerformanceReview, Role, salary_band_midpoint
from workforceiq.services.employees import _recommended_action, _top_features
from workforceiq.utils.time import ensure_utc_datetime, to_utc_iso, utc_now


def generate_attrition_risk_report(
    context: RequestContext,
    *,
    department_id: int | None = None,
    limit: int | None = None,
) -> dict:
    scoped_department_id = authorize_attrition_report_read(context, department_id)
    row_limit = _validated_row_limit(limit)

    latest_runs = (
        select(
            MlPrediction.employee_id.label("employee_id"),
            func.max(MlPrediction.run_at).label("latest_run_at"),
        )
        .where(MlPrediction.model_type == "attrition")
        .where(MlPrediction.organization_id == context.organization_id)
        .group_by(MlPrediction.employee_id)
        .subquery()
    )

    query = (
        select(MlPrediction, Employee, Department, Role)
        .join(
            latest_runs,
            and_(
                latest_runs.c.employee_id == MlPrediction.employee_id,
                latest_runs.c.latest_run_at == MlPrediction.run_at,
            ),
        )
        .join(Employee, Employee.id == MlPrediction.employee_id)
        .join(Department, Department.id == Employee.department_id)
        .join(Role, Role.id == Employee.role_id)
        .where(
            MlPrediction.model_type == "attrition",
            MlPrediction.organization_id == context.organization_id,
            Employee.organization_id == context.organization_id,
            Department.organization_id == context.organization_id,
            Role.organization_id == context.organization_id,
        )
        .order_by(MlPrediction.prediction.desc(), MlPrediction.confidence.desc())
        .limit(row_limit)
    )
    if scoped_department_id is not None:
        query = query.where(Employee.department_id == scoped_department_id)

    rows = db.session.execute(query).all()

    grouped: dict[str, dict[str, int]] = {}
    high_risk_employees = []
    total_financial_exposure = Decimal("0")

    for prediction, employee, department, role in rows:
        tier = _risk_tier(prediction.prediction)
        grouped.setdefault(department.name, {"HIGH": 0, "MEDIUM": 0, "LOW": 0})
        grouped[department.name][tier] += 1

        if tier == "HIGH":
            features = _top_features(prediction.features_snapshot)
            midpoint = salary_band_midpoint(role)
            replacement_cost = (midpoint * Decimal("1.5")) if midpoint is not None else None
            if replacement_cost is not None:
                total_financial_exposure += replacement_cost
            high_risk_employees.append(
                {
                    "employee_id": employee.id,
                    "employee_name": employee.name,
                    "department": department.name,
                    "role": role.title,
                    "predicted_attrition_probability": round(prediction.prediction, 4),
                    "confidence": round(prediction.confidence, 4),
                    "top_features": features,
                    "recommended_action": _recommended_action("AttritionRiskModel", features),
                    "run_at": to_utc_iso(prediction.run_at),
                    "stale": _is_stale(prediction.run_at),
                    "estimated_replacement_cost": float(replacement_cost) if replacement_cost is not None else None,
                }
            )

    return {
        "executive_summary": [
            f"Departments covered: {len(grouped)}",
            f"High-risk employees flagged: {len(high_risk_employees)}",
            f"Estimated financial exposure: {float(total_financial_exposure):.2f}",
        ],
        "grouped_by_department": grouped,
        "high_risk_employees": high_risk_employees,
        "financial_exposure": {
            "replacement_cost_formula": "1.5 x estimated annual salary midpoint from roles.salary_band_min and roles.salary_band_max",
            "total_estimated_cost": float(total_financial_exposure),
            "source_fields": [
                "ml_predictions.prediction",
                "roles.salary_band_min",
                "roles.salary_band_max",
            ],
        },
        "generated_at": to_utc_iso(utc_now()),
    }


def generate_department_health_check(context: RequestContext, department_id: int) -> dict:
    authorize_department_report_read(context, department_id)

    department = db.session.execute(
        select(Department)
        .where(Department.id == department_id, Department.organization_id == context.organization_id)
        .limit(1)
    ).scalar_one_or_none()
    if department is None:
        raise NotFoundError(f"No department record found for `{department_id}`.")

    active_headcount = db.session.execute(
        select(func.count(Employee.id))
        .where(
            Employee.department_id == department_id,
            Employee.organization_id == context.organization_id,
            Employee.status == "Active",
        )
    ).scalar_one()

    latest_reviews_subquery = (
        select(
            PerformanceReview.employee_id.label("employee_id"),
            func.max(PerformanceReview.created_at).label("latest_created_at"),
        )
        .group_by(PerformanceReview.employee_id)
        .subquery()
    )

    dept_scores = db.session.execute(
        select(PerformanceReview.score)
        .join(
            latest_reviews_subquery,
            and_(
                latest_reviews_subquery.c.employee_id == PerformanceReview.employee_id,
                latest_reviews_subquery.c.latest_created_at == PerformanceReview.created_at,
            ),
        )
        .join(Employee, Employee.id == PerformanceReview.employee_id)
        .where(
            Employee.department_id == department_id,
            Employee.organization_id == context.organization_id,
            PerformanceReview.organization_id == context.organization_id,
        )
    ).scalars().all()

    company_scores = db.session.execute(
        select(PerformanceReview.score).join(
            latest_reviews_subquery,
            and_(
                latest_reviews_subquery.c.employee_id == PerformanceReview.employee_id,
                latest_reviews_subquery.c.latest_created_at == PerformanceReview.created_at,
            ),
        )
        .join(Employee, Employee.id == PerformanceReview.employee_id)
        .where(
            Employee.organization_id == context.organization_id,
            PerformanceReview.organization_id == context.organization_id,
        )
    ).scalars().all()

    attrition_report = generate_attrition_risk_report(context, department_id=department_id, limit=500)
    department_bucket = attrition_report["grouped_by_department"].get(department.name, {"HIGH": 0, "MEDIUM": 0, "LOW": 0})
    total_predictions = sum(department_bucket.values())
    high_risk_share = (department_bucket["HIGH"] / total_predictions) if total_predictions else 0

    headcount_target = department.headcount_target or 0
    ratio = round((active_headcount / headcount_target), 2) if headcount_target else None
    department_avg = round(statistics.mean(dept_scores), 2) if dept_scores else None
    company_avg = round(statistics.mean(company_scores), 2) if company_scores else None

    traffic_light = _health_score(
        headcount_ratio=ratio,
        department_average=department_avg,
        company_average=company_avg,
        high_risk_share=high_risk_share,
    )

    return {
        "executive_summary": [
            f"{department.name} headcount ratio: {ratio if ratio is not None else 'N/A'}",
            f"{department.name} average performance score: {department_avg if department_avg is not None else 'N/A'}",
            f"{department.name} health rating: {traffic_light['label']}",
        ],
        "department": {
            "id": department.id,
            "name": department.name,
            "headcount_target": department.headcount_target,
            "budget": float(department.budget) if department.budget is not None else None,
            "source": "departments.id, departments.name, departments.headcount_target, departments.budget",
        },
        "headcount": {
            "active_count": active_headcount,
            "target": department.headcount_target,
            "ratio": ratio,
            "source": "employees.status, employees.department_id, departments.headcount_target",
        },
        "performance": {
            "department_average": department_avg,
            "company_benchmark": company_avg,
            "median": round(statistics.median(dept_scores), 2) if dept_scores else None,
            "std_deviation": round(statistics.pstdev(dept_scores), 2) if len(dept_scores) > 1 else 0,
            "source": "performance_reviews.score",
        },
        "attrition_distribution": department_bucket,
        "open_requisitions": {
            "value": None,
            "status": "UNAVAILABLE",
            "reason": "No requisitions table is present in the provided schema.",
        },
        "salary_band_compliance": {
            "value": None,
            "status": "UNAVAILABLE",
            "reason": "No employee compensation field is present in the provided schema.",
        },
        "traffic_light_health": traffic_light,
        "generated_at": to_utc_iso(utc_now()),
    }


def _risk_tier(prediction: float) -> str:
    if prediction > 0.7:
        return "HIGH"
    if prediction >= 0.4:
        return "MEDIUM"
    return "LOW"


def _health_score(
    *,
    headcount_ratio: float | None,
    department_average: float | None,
    company_average: float | None,
    high_risk_share: float,
) -> dict:
    score = 100
    reasons = []

    if headcount_ratio is None:
        score -= 5
        reasons.append("Headcount target is not configured.")
    elif headcount_ratio < 0.8 or headcount_ratio > 1.2:
        score -= 25
        reasons.append("Headcount is materially off target.")

    if department_average is None or company_average is None:
        score -= 5
        reasons.append("Performance benchmark data is incomplete.")
    elif department_average < company_average - 10:
        score -= 25
        reasons.append("Department performance trails the company benchmark by more than 10 points.")

    if high_risk_share > 0.35:
        score -= 35
        reasons.append("High-risk attrition concentration is critical.")
    elif high_risk_share > 0.2:
        score -= 20
        reasons.append("High-risk attrition concentration is elevated.")

    if score >= 75:
        label = "Healthy"
        indicator = "GREEN"
    elif score >= 45:
        label = "At Risk"
        indicator = "YELLOW"
    else:
        label = "Critical"
        indicator = "RED"

    return {
        "score": score,
        "label": label,
        "indicator": indicator,
        "reasons": reasons,
    }


def _is_stale(run_at) -> bool:
    from datetime import timedelta

    return ensure_utc_datetime(run_at) < utc_now() - timedelta(days=current_app.config["ML_STALE_DAYS"])


def _validated_row_limit(limit: int | None) -> int:
    max_rows = current_app.config["MAX_EXPORT_ROWS"]
    if limit is None:
        return min(100, max_rows)
    if limit < 1:
        raise ValidationError(f"Query limit `{limit}` is invalid. Provide a value between 1 and {max_rows}.")
    return min(limit, max_rows)
