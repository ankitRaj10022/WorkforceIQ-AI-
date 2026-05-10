"""initial industry schema

Revision ID: 0001_industry_schema
Revises:
Create Date: 2026-05-10
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_industry_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_organizations_status", "organizations", ["status"])

    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("head_id", sa.String(length=32), nullable=True),
        sa.Column("headcount_target", sa.Integer(), nullable=True),
        sa.Column("budget", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "name", name="uq_departments_org_name"),
    )
    op.create_index("ix_departments_name", "departments", ["name"])
    op.create_index("ix_departments_organization_id", "departments", ["organization_id"])

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("level", sa.String(length=32), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("salary_band_min", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("salary_band_max", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_roles_department_id", "roles", ["department_id"])
    op.create_index("ix_roles_level", "roles", ["level"])
    op.create_index("ix_roles_organization_id", "roles", ["organization_id"])
    op.create_index("ix_roles_title", "roles", ["title"])

    op.create_table(
        "employees",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("hire_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("manager_id", sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.ForeignKeyConstraint(["manager_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "email", name="uq_employees_org_email"),
    )
    op.create_foreign_key(
        "fk_departments_head_id_employees",
        "departments",
        "employees",
        ["head_id"],
        ["id"],
    )
    op.create_index("idx_emp_dept_status", "employees", ["department_id", "status"])
    op.create_index("ix_employees_department_id", "employees", ["department_id"])
    op.create_index("ix_employees_email", "employees", ["email"])
    op.create_index("ix_employees_name", "employees", ["name"])
    op.create_index("ix_employees_organization_id", "employees", ["organization_id"])
    op.create_index("ix_employees_role_id", "employees", ["role_id"])
    op.create_index("ix_employees_status", "employees", ["status"])

    op.create_table(
        "performance_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("employee_id", sa.String(length=32), nullable=False),
        sa.Column("period", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("reviewer_id", sa.String(length=32), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["reviewer_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_perf_emp_period", "performance_reviews", ["employee_id", "period"])
    op.create_index("ix_performance_reviews_created_at", "performance_reviews", ["created_at"])
    op.create_index("ix_performance_reviews_employee_id", "performance_reviews", ["employee_id"])
    op.create_index("ix_performance_reviews_organization_id", "performance_reviews", ["organization_id"])
    op.create_index("ix_performance_reviews_period", "performance_reviews", ["period"])

    op.create_table(
        "rbac_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("scope", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_rbac_roles_name", "rbac_roles", ["name"])

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("login_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_active", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["rbac_roles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_sessions_organization_id", "user_sessions", ["organization_id"])
    op.create_index("ix_user_sessions_role_id", "user_sessions", ["role_id"])
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("target_entity", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_organization_id", "audit_logs", ["organization_id"])
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])
    op.create_index("ix_audit_logs_target_entity", "audit_logs", ["target_entity"])
    op.create_index("ix_audit_logs_target_id", "audit_logs", ["target_id"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])

    op.create_table(
        "ml_predictions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("employee_id", sa.String(length=32), nullable=False),
        sa.Column("model_type", sa.String(length=64), nullable=False),
        sa.Column("prediction", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("features_snapshot", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_ml_emp_type", "ml_predictions", ["employee_id", "model_type", "run_at"])
    op.create_index("ix_ml_predictions_employee_id", "ml_predictions", ["employee_id"])
    op.create_index("ix_ml_predictions_model_type", "ml_predictions", ["model_type"])
    op.create_index("ix_ml_predictions_organization_id", "ml_predictions", ["organization_id"])
    op.create_index("ix_ml_predictions_run_at", "ml_predictions", ["run_at"])

    op.create_table(
        "user_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("employee_id", sa.String(length=32), nullable=True),
        sa.Column("mfa_secret", sa.String(length=64), nullable=True),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("failed_login_count", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "email", name="uq_user_accounts_org_email"),
    )
    op.create_index("ix_user_accounts_department_id", "user_accounts", ["department_id"])
    op.create_index("ix_user_accounts_email", "user_accounts", ["email"])
    op.create_index("ix_user_accounts_employee_id", "user_accounts", ["employee_id"])
    op.create_index("ix_user_accounts_is_active", "user_accounts", ["is_active"])
    op.create_index("ix_user_accounts_organization_id", "user_accounts", ["organization_id"])
    op.create_index("ix_user_accounts_role", "user_accounts", ["role"])

    op.create_table(
        "compliance_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("request_type", sa.String(length=32), nullable=False),
        sa.Column("subject_employee_id", sa.String(length=32), nullable=False),
        sa.Column("requested_by", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["subject_employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_compliance_requests_organization_id", "compliance_requests", ["organization_id"])
    op.create_index("ix_compliance_requests_requested_by", "compliance_requests", ["requested_by"])
    op.create_index("ix_compliance_requests_request_type", "compliance_requests", ["request_type"])
    op.create_index("ix_compliance_requests_status", "compliance_requests", ["status"])
    op.create_index("ix_compliance_requests_subject_employee_id", "compliance_requests", ["subject_employee_id"])


def downgrade() -> None:
    op.drop_table("compliance_requests")
    op.drop_table("user_accounts")
    op.drop_table("ml_predictions")
    op.drop_table("audit_logs")
    op.drop_table("user_sessions")
    op.drop_table("rbac_roles")
    op.drop_table("performance_reviews")
    op.drop_constraint("fk_departments_head_id_employees", "departments", type_="foreignkey")
    op.drop_table("employees")
    op.drop_table("roles")
    op.drop_table("departments")
    op.drop_table("organizations")
