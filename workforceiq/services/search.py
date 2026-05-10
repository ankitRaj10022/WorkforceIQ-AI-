from __future__ import annotations

from flask import current_app
from sqlalchemy import func, or_, select

from workforceiq.auth import RequestContext, RoleName
from workforceiq.errors import ValidationError
from workforceiq.extensions import db
from workforceiq.models import Department, Employee, PerformanceReview, Role


def search_employees(context: RequestContext, *, query: str, limit: int | None = None) -> dict:
    normalized = query.strip()
    if len(normalized) < 2:
        raise ValidationError("Search query must contain at least 2 characters.")

    row_limit = min(limit or 20, current_app.config["MAX_EXPORT_ROWS"])
    elasticsearch_results = _search_with_elasticsearch(context, normalized, row_limit)
    if elasticsearch_results is not None:
        return {
            "query": normalized,
            "backend": "elasticsearch",
            "ranking": "Elasticsearch multi_match relevance score",
            "results": elasticsearch_results,
            "suggestion": None if elasticsearch_results else "Try a broader name, department, role, or employee ID filter.",
        }

    results = _search_with_sql(context, normalized, row_limit)
    return {
        "query": normalized,
        "backend": "sql_fallback",
        "ranking": "weighted fuzzy SQL match; Elasticsearch adapter can replace this when ELASTICSEARCH_URL is active",
        "results": results,
        "suggestion": None if results else "Try a broader name, department, role, or employee ID filter.",
    }


def index_employee_documents(context: RequestContext) -> dict:
    documents = employee_search_documents(context)
    client = _elasticsearch_client()
    if client is None:
        return {"backend": "sql_fallback", "documents_prepared": len(documents), "documents_indexed": 0}

    try:
        from elasticsearch import helpers

        index_name = _employee_index_name(context.organization_id)
        actions = [
            {
                "_index": index_name,
                "_id": document["id"],
                "_source": document,
            }
            for document in documents
        ]
        indexed, _errors = helpers.bulk(client, actions, raise_on_error=False)
        return {"backend": "elasticsearch", "documents_prepared": len(documents), "documents_indexed": indexed}
    except Exception:  # pragma: no cover - depends on Elasticsearch availability
        current_app.logger.error("search.elasticsearch_index_failed", exc_info=True)
        return {"backend": "sql_fallback", "documents_prepared": len(documents), "documents_indexed": 0}


def employee_search_documents(context: RequestContext) -> list[dict]:
    rows = db.session.execute(
        select(Employee, Department, Role)
        .join(Department, Department.id == Employee.department_id)
        .join(Role, Role.id == Employee.role_id)
        .where(Employee.organization_id == context.organization_id)
        .limit(current_app.config["MAX_EXPORT_ROWS"])
    ).all()
    return [
        {
            "id": employee.id,
            "organization_id": employee.organization_id,
            "name": employee.name,
            "email": employee.email,
            "department_id": employee.department_id,
            "department": department.name,
            "role": role.title,
            "performance_score": None,
            "status": employee.status,
        }
        for employee, department, role in rows
    ]


def _search_with_elasticsearch(context: RequestContext, query: str, limit: int) -> list[dict] | None:
    client = _elasticsearch_client()
    if client is None:
        return None
    filters: list[dict] = [{"term": {"organization_id": context.organization_id}}]
    if context.role == RoleName.DEPT_HEAD:
        filters.append({"term": {"department_id": context.department_id}})
    elif context.role == RoleName.EMPLOYEE:
        filters.append({"term": {"id": context.employee_id}})
    elif context.role not in {RoleName.SUPER_ADMIN, RoleName.HR_MANAGER, RoleName.AUDITOR}:
        raise ValidationError("This role cannot search employee records.")

    try:
        response = client.search(
            index=_employee_index_name(context.organization_id),
            size=limit,
            query={
                "bool": {
                    "filter": filters,
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["id^4", "name^3", "email", "department^2", "role^2", "status"],
                                "fuzziness": "AUTO",
                            }
                        }
                    ],
                }
            },
        )
    except Exception:  # pragma: no cover - depends on Elasticsearch availability
        current_app.logger.warning("search.elasticsearch_unavailable", exc_info=True)
        return None

    hits = response.get("hits", {}).get("hits", [])
    return [
        {
            "employee_id": hit["_source"]["id"],
            "name": hit["_source"]["name"],
            "department": hit["_source"]["department"],
            "role": hit["_source"]["role"],
            "performance_score": hit["_source"].get("performance_score"),
            "status": hit["_source"]["status"],
            "tenure_source": "employees.hire_date",
            "relevance_score": hit.get("_score", 0),
        }
        for hit in hits
    ]


def _search_with_sql(context: RequestContext, query: str, limit: int) -> list[dict]:
    pattern = f"%{query.lower()}%"
    latest_reviews = (
        select(
            PerformanceReview.employee_id.label("employee_id"),
            func.max(PerformanceReview.created_at).label("latest_created_at"),
        )
        .where(PerformanceReview.organization_id == context.organization_id)
        .group_by(PerformanceReview.employee_id)
        .subquery()
    )

    statement = (
        select(Employee, Department, Role, PerformanceReview.score)
        .join(Department, Department.id == Employee.department_id)
        .join(Role, Role.id == Employee.role_id)
        .outerjoin(
            latest_reviews,
            latest_reviews.c.employee_id == Employee.id,
        )
        .outerjoin(
            PerformanceReview,
            (PerformanceReview.employee_id == Employee.id)
            & (PerformanceReview.created_at == latest_reviews.c.latest_created_at),
        )
        .where(
            Employee.organization_id == context.organization_id,
            Department.organization_id == context.organization_id,
            Role.organization_id == context.organization_id,
            or_(
                func.lower(Employee.id).like(pattern),
                func.lower(Employee.name).like(pattern),
                func.lower(Employee.email).like(pattern),
                func.lower(Department.name).like(pattern),
                func.lower(Role.title).like(pattern),
                func.lower(Role.level).like(pattern),
            ),
        )
        .limit(limit)
    )

    if context.role == RoleName.DEPT_HEAD:
        statement = statement.where(Employee.department_id == context.department_id)
    elif context.role == RoleName.EMPLOYEE:
        statement = statement.where(Employee.id == context.employee_id)
    elif context.role not in {RoleName.SUPER_ADMIN, RoleName.HR_MANAGER, RoleName.AUDITOR}:
        raise ValidationError("This role cannot search employee records.")

    rows = db.session.execute(statement).all()
    ranked = sorted(
        (_serialize_result(employee, department, role, score, query) for employee, department, role, score in rows),
        key=lambda item: item["relevance_score"],
        reverse=True,
    )
    return ranked


def _serialize_result(employee: Employee, department: Department, role: Role, score: float | None, query: str) -> dict:
    normalized = query.lower()
    relevance = 0.35
    if employee.id.lower() == normalized:
        relevance = 1.0
    elif employee.name.lower().startswith(normalized):
        relevance = 0.9
    elif normalized in employee.name.lower():
        relevance = 0.75
    elif normalized in role.title.lower():
        relevance = 0.6
    elif normalized in department.name.lower():
        relevance = 0.5

    return {
        "employee_id": employee.id,
        "name": employee.name,
        "department": department.name,
        "role": f"{role.title} ({role.level})",
        "performance_score": score,
        "status": employee.status,
        "tenure_source": "employees.hire_date",
        "relevance_score": relevance,
    }


def _elasticsearch_client():
    url = current_app.config.get("ELASTICSEARCH_URL")
    if not url:
        return None
    try:
        from elasticsearch import Elasticsearch

        return Elasticsearch(url)
    except Exception:  # pragma: no cover - import/config guard
        current_app.logger.warning("search.elasticsearch_client_unavailable", exc_info=True)
        return None


def _employee_index_name(organization_id: str) -> str:
    safe_org = organization_id.lower().replace("_", "-")
    return f"workforceiq-employees-{safe_org}"
