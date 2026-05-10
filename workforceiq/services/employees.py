from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from flask import current_app
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from workforceiq.audit import record_audit_log
from workforceiq.auth import RequestContext, RoleName, authorize_employee_read, authorize_employee_write
from workforceiq.errors import NotFoundError, ValidationError
from workforceiq.extensions import db
from workforceiq.models import Department, Employee, MlPrediction, PerformanceReview, Role
from workforceiq.utils.time import ensure_utc_datetime, to_utc_iso, utc_now


def fetch_employee_profile(employee_id: str, context: RequestContext) -> dict:
    employee = db.session.execute(
        select(Employee)
        .options(joinedload(Employee.department), joinedload(Employee.role), joinedload(Employee.manager))
        .where(Employee.id == employee_id, Employee.organization_id == context.organization_id)
        .limit(1)
    ).scalar_one_or_none()

    if employee is None:
        raise NotFoundError(f"No employee record found for `{employee_id}`. Try searching by ID or checking the spelling.")

    authorize_employee_read(context, employee.department_id, employee.id)

    reviews = db.session.execute(
        select(PerformanceReview)
        .where(
            PerformanceReview.employee_id == employee_id,
            PerformanceReview.organization_id == context.organization_id,
        )
        .order_by(PerformanceReview.created_at.desc(), PerformanceReview.id.desc())
        .limit(3)
    ).scalars().all()
    predictions = db.session.execute(
        select(MlPrediction)
        .where(
            MlPrediction.employee_id == employee_id,
            MlPrediction.organization_id == context.organization_id,
            MlPrediction.model_type.in_(["attrition", "performance_forecast", "promotion_readiness"]),
        )
        .order_by(MlPrediction.model_type.asc(), MlPrediction.run_at.desc(), MlPrediction.id.desc())
    ).scalars().all()

    latest_predictions: dict[str, MlPrediction] = {}
    for prediction in predictions:
        latest_predictions.setdefault(prediction.model_type, prediction)

    performance_section = _build_performance_section(reviews)
    prediction_section = {
        "attrition_risk": _serialize_prediction(latest_predictions.get("attrition"), "AttritionRiskModel"),
        "performance_forecast": _serialize_prediction(
            latest_predictions.get("performance_forecast"), "PerformanceForecastModel"
        ),
        "promotion_readiness": _serialize_prediction(
            latest_predictions.get("promotion_readiness"), "PromotionReadinessModel"
        ),
    }
    if context.role == RoleName.EMPLOYEE:
        prediction_section = {
            "restricted": True,
            "reason": "Prediction scores are not available through employee self-service.",
        }

    profile = {
        "employee_profile": {
            "name": employee.name,
            "id": employee.id,
            "email": employee.email,
            "role": {
                "title": employee.role.title,
                "level": employee.role.level,
                "source": "roles.title, roles.level",
            },
            "department": {
                "id": employee.department.id,
                "name": employee.department.name,
                "source": "departments.id, departments.name",
            },
            "status": {
                "value": employee.status,
                "source": "employees.status",
            },
            "tenure": {
                "years": _calculate_tenure_years(employee.hire_date),
                "hire_date": employee.hire_date.isoformat(),
                "source": "employees.hire_date",
            },
            "manager": {
                "id": employee.manager.id if employee.manager else None,
                "name": employee.manager.name if employee.manager else None,
                "source": "employees.manager_id -> employees.id",
            },
        },
        "performance": performance_section,
        "ml_predictions": prediction_section,
        "join_logic": [
            "employees.department_id = departments.id",
            "employees.role_id = roles.id",
            "performance_reviews.employee_id = employees.id",
            "ml_predictions.employee_id = employees.id",
        ],
        "formatted_summary": _format_profile_summary(employee, performance_section, prediction_section),
    }
    return profile


def update_employee(employee_id: str, context: RequestContext, payload: dict) -> dict:
    employee = db.session.execute(
        select(Employee)
        .where(Employee.id == employee_id, Employee.organization_id == context.organization_id)
        .limit(1)
    ).scalar_one_or_none()
    if employee is None:
        raise NotFoundError(f"No employee record found for `{employee_id}`. Try searching by ID or checking the spelling.")

    requested_fields = set(payload.keys())
    if not requested_fields:
        raise ValidationError("Request body is empty. Provide at least one field to update.")

    authorize_employee_write(context, employee.department_id, employee.id, requested_fields)

    allowed_fields = {"name", "email", "department_id", "role_id", "hire_date", "status", "manager_id"}
    unknown_fields = requested_fields - allowed_fields
    if unknown_fields:
        unknown = ", ".join(sorted(unknown_fields))
        raise ValidationError(f"Unsupported fields: {unknown}.")

    _validate_employee_update_payload(employee, payload, organization_id=context.organization_id)

    old_values: dict[str, str | int | None] = {}
    new_values: dict[str, str | int | None] = {}

    for field in allowed_fields & requested_fields:
        incoming_value = payload[field]
        if field == "hire_date" and incoming_value is not None:
            incoming_value = _parse_date(incoming_value)
        current_value = getattr(employee, field)
        if current_value != incoming_value:
            old_values[field] = _serialize_scalar(current_value)
            new_values[field] = _serialize_scalar(incoming_value)
            setattr(employee, field, incoming_value)

    if not new_values:
        raise ValidationError("No changes detected in the provided payload.")

    record_audit_log(
        user_id=context.user_id,
        organization_id=context.organization_id,
        action="UPDATE",
        target_entity="employees",
        target_id=employee.id,
        fields_changed=sorted(new_values.keys()),
        old_values=old_values,
        new_values=new_values,
    )
    db.session.commit()

    return {
        "message": "Employee updated successfully.",
        "employee_id": employee.id,
        "changed_fields": sorted(new_values.keys()),
        "audit_log_written": True,
    }


def _build_performance_section(reviews: list[PerformanceReview]) -> dict:
    latest_review = reviews[0] if reviews else None
    trend = _compute_trend(reviews)
    return {
        "latest_review": {
            "score": latest_review.score if latest_review else None,
            "period": latest_review.period if latest_review else None,
            "reviewer_id": latest_review.reviewer_id if latest_review else None,
            "created_at": to_utc_iso(latest_review.created_at) if latest_review else None,
            "source": "performance_reviews.score, performance_reviews.period, performance_reviews.reviewer_id",
        },
        "trend": trend,
    }


def _serialize_prediction(prediction: MlPrediction | None, model_name: str) -> dict | None:
    if prediction is None:
        return None

    stale = ensure_utc_datetime(prediction.run_at) < utc_now() - timedelta(days=current_app.config["ML_STALE_DAYS"])
    features = _top_features(prediction.features_snapshot)
    return {
        "model": model_name,
        "prediction": prediction.prediction,
        "confidence": prediction.confidence,
        "prediction_probability": round(prediction.prediction, 4) if model_name == "AttritionRiskModel" else None,
        "top_features": features,
        "recommended_action": _recommended_action(model_name, features),
        "run_at": to_utc_iso(prediction.run_at),
        "stale": stale,
        "warning": "[STALE - rerun recommended]" if stale else None,
        "source": "ml_predictions.prediction, ml_predictions.confidence, ml_predictions.run_at, ml_predictions.features_snapshot",
    }


def _top_features(snapshot: dict | list | None) -> list[str]:
    if not snapshot:
        return []
    if isinstance(snapshot, list):
        return [str(item) for item in snapshot[:3]]
    if "top_features" in snapshot and isinstance(snapshot["top_features"], list):
        return [str(item) for item in snapshot["top_features"][:3]]
    ranked_items = [
        (feature, weight)
        for feature, weight in snapshot.items()
        if isinstance(weight, (int, float))
    ]
    ranked_items.sort(key=lambda item: abs(item[1]), reverse=True)
    if ranked_items:
        return [str(name) for name, _weight in ranked_items[:3]]
    return [str(key) for key in list(snapshot.keys())[:3]]


def _recommended_action(model_name: str, features: list[str]) -> str:
    feature_text = " ".join(features).lower()
    if model_name == "AttritionRiskModel":
        if any(token in feature_text for token in ["salary", "compensation", "market"]):
            return "Review compensation positioning and schedule a retention conversation."
        if any(token in feature_text for token in ["promotion", "career", "growth"]):
            return "Schedule a career path discussion with the employee and manager."
        if any(token in feature_text for token in ["overtime", "workload", "burnout"]):
            return "Rebalance workload and add a manager check-in within the current sprint."
        return "Review engagement signals with HR and schedule a manager 1:1."
    if model_name == "PerformanceForecastModel":
        return "Use the forecast as a coaching input, then confirm it during the next review cycle."
    return "Validate readiness with a human calibration discussion before acting on the prediction."


def _validate_employee_update_payload(employee: Employee, payload: dict, *, organization_id: str) -> None:
    target_department_id = payload.get("department_id", employee.department_id)
    target_role_id = payload.get("role_id", employee.role_id)
    target_manager_id = payload.get("manager_id", employee.manager_id)

    if "name" in payload:
        name = _normalize_non_empty_string(payload["name"], field_name="name")
        payload["name"] = name

    if "status" in payload:
        payload["status"] = _normalize_non_empty_string(payload["status"], field_name="status")

    if "email" in payload:
        email = _normalize_email(payload["email"])
        existing_email_owner = db.session.execute(
            select(Employee)
            .where(
                Employee.email == email,
                Employee.id != employee.id,
                Employee.organization_id == organization_id,
            )
            .limit(1)
        ).scalar_one_or_none()
        if existing_email_owner is not None:
            raise ValidationError(f"Email `{email}` is already assigned to another employee.")
        payload["email"] = email

    target_department = db.session.execute(
        select(Department)
        .where(Department.id == target_department_id, Department.organization_id == organization_id)
        .limit(1)
    ).scalar_one_or_none()
    if target_department is None:
        raise ValidationError(f"Department `{target_department_id}` does not exist.")

    target_role = db.session.execute(
        select(Role)
        .where(Role.id == target_role_id, Role.organization_id == organization_id)
        .limit(1)
    ).scalar_one_or_none()
    if target_role is None:
        raise ValidationError(f"Role `{target_role_id}` does not exist.")
    if target_role.department_id != target_department_id:
        raise ValidationError(
            f"Role `{target_role_id}` belongs to department `{target_role.department_id}`, not `{target_department_id}`."
        )

    if target_manager_id is not None:
        if target_manager_id == employee.id:
            raise ValidationError("An employee cannot be their own manager.")
        manager = db.session.execute(
            select(Employee)
            .where(Employee.id == target_manager_id, Employee.organization_id == organization_id)
            .limit(1)
        ).scalar_one_or_none()
        if manager is None:
            raise ValidationError(f"Manager `{target_manager_id}` does not exist.")


def _compute_trend(reviews: list[PerformanceReview]) -> dict:
    if len(reviews) < 2:
        return {"direction": "FLAT", "delta": 0}
    newest = reviews[0].score
    oldest = reviews[-1].score
    delta = round(newest - oldest, 2)
    if delta > 0:
        direction = "UP"
    elif delta < 0:
        direction = "DOWN"
    else:
        direction = "FLAT"
    return {"direction": direction, "delta": delta}


def _calculate_tenure_years(hire_date: date) -> float:
    days = (date.today() - hire_date).days
    return round(days / 365.25, 2)


def _format_profile_summary(employee: Employee, performance_section: dict, prediction_section: dict) -> str:
    latest_review = performance_section["latest_review"]
    attrition = prediction_section.get("attrition_risk") or {}
    performance_forecast = prediction_section.get("performance_forecast") or {}
    promotion = prediction_section.get("promotion_readiness") or {}
    if prediction_section.get("restricted"):
        attrition = {"prediction": "Restricted", "confidence": "Restricted"}
        performance_forecast = {"prediction": "Restricted", "confidence": "Restricted"}
        promotion = {"prediction": "Restricted", "confidence": "Restricted"}

    lines = [
        "Employee Profile",
        f"Name: {employee.name}",
        f"ID: {employee.id}",
        f"Role: {employee.role.title} ({employee.role.level})",
        f"Department: {employee.department.name}",
        f"Status: {employee.status}",
        f"Tenure: {_calculate_tenure_years(employee.hire_date)} years (Hired: {employee.hire_date.isoformat()})",
        f"Manager: {employee.manager.name if employee.manager else 'Unassigned'}",
        "",
        "Performance",
        f"Latest Score: {latest_review['score']} ({latest_review['period']})",
        f"Trend: {performance_section['trend']['direction']} {performance_section['trend']['delta']}",
        "",
        "ML Predictions",
        f"Attrition Risk: {attrition.get('prediction')} [Confidence: {attrition.get('confidence')}]",
        f"Performance Forecast: {performance_forecast.get('prediction')} [Confidence: {performance_forecast.get('confidence')}]",
        f"Promotion Ready: {promotion.get('prediction')} [Confidence: {promotion.get('confidence')}]",
    ]
    return "\n".join(lines)


def _parse_date(value: str) -> date:
    try:
        return datetime.fromisoformat(value).date()
    except ValueError as exc:
        raise ValidationError(f"Invalid date value `{value}`. Use YYYY-MM-DD.") from exc


def _normalize_non_empty_string(value: object, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"Field `{field_name}` must be a string.")
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"Field `{field_name}` cannot be empty.")
    return normalized


def _normalize_email(value: object) -> str:
    email = _normalize_non_empty_string(value, field_name="email").lower()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValidationError(f"Email `{email}` is invalid.")
    return email


def _serialize_scalar(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    return value
