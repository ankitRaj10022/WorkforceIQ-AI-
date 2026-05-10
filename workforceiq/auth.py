from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from flask import current_app
from flask_jwt_extended import get_jwt

from workforceiq.errors import AccessDeniedError, ValidationError


class RoleName(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    HR_MANAGER = "HR_MANAGER"
    DEPT_HEAD = "DEPT_HEAD"
    RECRUITER = "RECRUITER"
    EMPLOYEE = "EMPLOYEE"
    AUDITOR = "AUDITOR"


@dataclass(slots=True)
class RequestContext:
    user_id: str
    role: RoleName
    organization_id: str
    department_id: int | None = None
    employee_id: str | None = None


def parse_role(role_name: str | None) -> RoleName:
    if not role_name:
        raise ValidationError("A role value is required.")
    try:
        return RoleName(role_name)
    except ValueError as exc:
        allowed_roles = ", ".join(role.value for role in RoleName)
        raise ValidationError(
            f"Role `{role_name}` is invalid. Allowed roles: {allowed_roles}."
        ) from exc


def build_request_context() -> RequestContext:
    claims = get_jwt()
    role = parse_role(claims.get("role"))
    return RequestContext(
        user_id=str(claims.get("user_id") or claims.get("sub") or ""),
        role=role,
        organization_id=str(claims.get("organization_id") or current_app.config["DEFAULT_ORGANIZATION_ID"]),
        department_id=claims.get("department_id"),
        employee_id=claims.get("employee_id"),
    )


def resolve_dev_identity(
    *,
    user_id: str | None,
    requested_role: str | None = None,
    requested_department_id: int | None = None,
    requested_employee_id: str | None = None,
) -> dict:
    if not user_id:
        raise ValidationError("`user_id` is required to issue a development token.")

    identities = current_app.config.get("DEV_AUTH_IDENTITIES", {})
    identity = identities.get(user_id)
    if identity is None:
        raise AccessDeniedError(
            f"Access denied. Your role `UNKNOWN` does not have permission to request a dev token for `{user_id}`. "
            "Contact your system administrator."
        )

    role = parse_role(identity.get("role"))
    if requested_role is not None and parse_role(requested_role) != role:
        raise ValidationError(f"Requested role `{requested_role}` does not match the registered dev identity for `{user_id}`.")
    if requested_department_id is not None and requested_department_id != identity.get("department_id"):
        raise ValidationError(
            f"Requested department_id `{requested_department_id}` does not match the registered dev identity for `{user_id}`."
        )
    if requested_employee_id is not None and requested_employee_id != identity.get("employee_id"):
        raise ValidationError(
            f"Requested employee_id `{requested_employee_id}` does not match the registered dev identity for `{user_id}`."
        )

    return {
        "user_id": user_id,
        "role": role,
        "organization_id": identity.get("organization_id") or current_app.config["DEFAULT_ORGANIZATION_ID"],
        "department_id": identity.get("department_id"),
        "employee_id": identity.get("employee_id"),
    }


def authorize_employee_read(context: RequestContext, employee_department_id: int, employee_id: str) -> None:
    if context.role in {RoleName.SUPER_ADMIN, RoleName.HR_MANAGER}:
        return
    if context.role == RoleName.DEPT_HEAD and context.department_id == employee_department_id:
        return
    if context.role == RoleName.EMPLOYEE and context.employee_id == employee_id:
        return
    _deny(context.role, "READ", "employee profile")


def authorize_employee_write(
    context: RequestContext,
    employee_department_id: int,
    employee_id: str,
    fields: set[str],
) -> None:
    if context.role in {RoleName.SUPER_ADMIN, RoleName.HR_MANAGER}:
        return
    if context.role == RoleName.EMPLOYEE and context.employee_id == employee_id and fields.issubset({"name", "email"}):
        return
    if context.role == RoleName.DEPT_HEAD and context.department_id == employee_department_id:
        _deny(context.role, "WRITE", "employee record")
    _deny(context.role, "WRITE", "employee record")


def authorize_department_report_read(context: RequestContext, department_id: int) -> None:
    if context.role in {RoleName.SUPER_ADMIN, RoleName.HR_MANAGER, RoleName.AUDITOR}:
        return
    if context.role == RoleName.DEPT_HEAD and context.department_id == department_id:
        return
    _deny(context.role, "READ", "department report")


def authorize_attrition_report_read(context: RequestContext, department_id: int | None) -> int | None:
    if context.role in {RoleName.SUPER_ADMIN, RoleName.HR_MANAGER, RoleName.AUDITOR}:
        return department_id
    if context.role == RoleName.DEPT_HEAD:
        if context.department_id is None:
            _deny(context.role, "READ", "attrition report")
        if department_id is not None and department_id != context.department_id:
            _deny(context.role, "READ", "attrition report outside your department")
        return context.department_id
    _deny(context.role, "READ", "attrition report")


def authorize_audit_log_read(context: RequestContext) -> None:
    if context.role in {RoleName.SUPER_ADMIN, RoleName.AUDITOR}:
        return
    _deny(context.role, "READ", "audit logs")


def authorize_compliance_request(context: RequestContext, subject_employee_id: str) -> None:
    if context.role in {RoleName.SUPER_ADMIN, RoleName.HR_MANAGER, RoleName.AUDITOR}:
        return
    if context.role == RoleName.EMPLOYEE and context.employee_id == subject_employee_id:
        return
    _deny(context.role, "CREATE", "compliance request")


def _deny(role: RoleName, action: str, resource: str) -> None:
    raise AccessDeniedError(
        f"Access denied. Your role `{role.value}` does not have permission to {action} on {resource}. "
        "Contact your system administrator."
    )
