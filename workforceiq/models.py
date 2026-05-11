from __future__ import annotations

from decimal import Decimal

from workforceiq.extensions import db
from workforceiq.utils.time import utc_now


class Department(db.Model):
    __tablename__ = "departments"
    __table_args__ = (
        db.UniqueConstraint("organization_id", "name", name="uq_departments_org_name"),
    )

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.String(64), db.ForeignKey("organizations.id"), nullable=False, default="org-demo", index=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    head_id = db.Column(
        db.String(32),
        db.ForeignKey("employees.id", use_alter=True, name="fk_departments_head_id_employees"),
        nullable=True,
    )
    headcount_target = db.Column(db.Integer, nullable=True)
    budget = db.Column(db.Numeric(12, 2), nullable=True)

    organization = db.relationship("Organization", back_populates="departments")
    employees = db.relationship("Employee", back_populates="department", foreign_keys="Employee.department_id")
    roles = db.relationship("Role", back_populates="department")


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.String(64), db.ForeignKey("organizations.id"), nullable=False, default="org-demo", index=True)
    title = db.Column(db.String(150), nullable=False, index=True)
    level = db.Column(db.String(32), nullable=False, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False, index=True)
    salary_band_min = db.Column(db.Numeric(12, 2), nullable=True)
    salary_band_max = db.Column(db.Numeric(12, 2), nullable=True)

    organization = db.relationship("Organization", back_populates="roles")
    department = db.relationship("Department", back_populates="roles")
    employees = db.relationship("Employee", back_populates="role")


class Employee(db.Model):
    __tablename__ = "employees"
    __table_args__ = (
        db.Index("idx_emp_dept_status", "department_id", "status"),
        db.UniqueConstraint("organization_id", "email", name="uq_employees_org_email"),
    )

    id = db.Column(db.String(32), primary_key=True)
    organization_id = db.Column(db.String(64), db.ForeignKey("organizations.id"), nullable=False, default="org-demo", index=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False, index=True)
    hire_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), nullable=False, default="Active", index=True)
    manager_id = db.Column(db.String(32), db.ForeignKey("employees.id"), nullable=True)

    organization = db.relationship("Organization", back_populates="employees")
    department = db.relationship("Department", back_populates="employees", foreign_keys=[department_id])
    role = db.relationship("Role", back_populates="employees")
    manager = db.relationship("Employee", remote_side=[id], backref="direct_reports", foreign_keys=[manager_id])


class PerformanceReview(db.Model):
    __tablename__ = "performance_reviews"
    __table_args__ = (
        db.Index("idx_perf_emp_period", "employee_id", "period"),
    )

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.String(64), db.ForeignKey("organizations.id"), nullable=False, default="org-demo", index=True)
    employee_id = db.Column(db.String(32), db.ForeignKey("employees.id"), nullable=False, index=True)
    period = db.Column(db.String(32), nullable=False, index=True)
    score = db.Column(db.Float, nullable=False)
    reviewer_id = db.Column(db.String(32), db.ForeignKey("employees.id"), nullable=True)
    comments = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, index=True)

    organization = db.relationship("Organization", back_populates="performance_reviews")
    employee = db.relationship("Employee", foreign_keys=[employee_id])
    reviewer = db.relationship("Employee", foreign_keys=[reviewer_id])


class RbacRole(db.Model):
    __tablename__ = "rbac_roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True, index=True)
    permissions = db.Column(db.JSON, nullable=False, default=dict)
    scope = db.Column(db.String(50), nullable=False)


class UserSession(db.Model):
    __tablename__ = "user_sessions"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.String(64), db.ForeignKey("organizations.id"), nullable=False, default="org-demo", index=True)
    session_uuid = db.Column(db.String(36), nullable=False, unique=True, index=True)
    user_id = db.Column(db.String(32), nullable=False, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey("rbac_roles.id"), nullable=False, index=True)
    ip_address = db.Column(db.String(64), nullable=True)
    refresh_token_jti = db.Column(db.String(36), nullable=True, unique=True, index=True)
    refresh_expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    revoked_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    revoked_reason = db.Column(db.String(128), nullable=True)
    login_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    last_active = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    role = db.relationship("RbacRole")
    organization = db.relationship("Organization", back_populates="user_sessions")


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.String(64), db.ForeignKey("organizations.id"), nullable=False, default="org-demo", index=True)
    user_id = db.Column(db.String(32), nullable=False, index=True)
    action = db.Column(db.String(32), nullable=False, index=True)
    target_entity = db.Column(db.String(64), nullable=False, index=True)
    target_id = db.Column(db.String(64), nullable=False, index=True)
    timestamp = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    metadata_json = db.Column("metadata", db.JSON, nullable=False, default=dict)
    request_id = db.Column(db.String(64), nullable=True, index=True)
    ip_address = db.Column(db.String(64), nullable=True)

    organization = db.relationship("Organization", back_populates="audit_logs")


class MlPrediction(db.Model):
    __tablename__ = "ml_predictions"
    __table_args__ = (
        db.Index("idx_ml_emp_type", "employee_id", "model_type", "run_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.String(64), db.ForeignKey("organizations.id"), nullable=False, default="org-demo", index=True)
    employee_id = db.Column(db.String(32), db.ForeignKey("employees.id"), nullable=False, index=True)
    model_type = db.Column(db.String(64), nullable=False, index=True)
    prediction = db.Column(db.Float, nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    run_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    features_snapshot = db.Column(db.JSON, nullable=False, default=dict)

    employee = db.relationship("Employee")
    organization = db.relationship("Organization", back_populates="ml_predictions")


class Organization(db.Model):
    __tablename__ = "organizations"

    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(32), nullable=False, default="active", index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    departments = db.relationship("Department", back_populates="organization")
    roles = db.relationship("Role", back_populates="organization")
    employees = db.relationship("Employee", back_populates="organization")
    performance_reviews = db.relationship("PerformanceReview", back_populates="organization")
    user_accounts = db.relationship("UserAccount", back_populates="organization")
    user_sessions = db.relationship("UserSession", back_populates="organization")
    audit_logs = db.relationship("AuditLog", back_populates="organization")
    ml_predictions = db.relationship("MlPrediction", back_populates="organization")
    compliance_requests = db.relationship("ComplianceRequest", back_populates="organization")


class UserAccount(db.Model):
    __tablename__ = "user_accounts"
    __table_args__ = (
        db.UniqueConstraint("organization_id", "email", name="uq_user_accounts_org_email"),
    )

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.String(64), db.ForeignKey("organizations.id"), nullable=False, default="org-demo", index=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True, index=True)
    employee_id = db.Column(db.String(32), db.ForeignKey("employees.id"), nullable=True, index=True)
    mfa_secret = db.Column(db.String(64), nullable=True)
    mfa_enabled = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    failed_login_count = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    organization = db.relationship("Organization", back_populates="user_accounts")
    department = db.relationship("Department")
    employee = db.relationship("Employee")


class ComplianceRequest(db.Model):
    __tablename__ = "compliance_requests"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.String(64), db.ForeignKey("organizations.id"), nullable=False, default="org-demo", index=True)
    request_type = db.Column(db.String(32), nullable=False, index=True)
    subject_employee_id = db.Column(db.String(32), db.ForeignKey("employees.id"), nullable=False, index=True)
    requested_by = db.Column(db.String(32), nullable=False, index=True)
    status = db.Column(db.String(32), nullable=False, default="PENDING", index=True)
    reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    metadata_json = db.Column("metadata", db.JSON, nullable=False, default=dict)

    organization = db.relationship("Organization", back_populates="compliance_requests")
    subject_employee = db.relationship("Employee")


def salary_band_midpoint(role: Role | None) -> Decimal | None:
    if role is None or role.salary_band_min is None or role.salary_band_max is None:
        return None
    return (role.salary_band_min + role.salary_band_max) / 2
