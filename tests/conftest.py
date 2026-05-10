from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta

import pytest
from werkzeug.security import generate_password_hash

from workforceiq import create_app
from workforceiq.extensions import db
from workforceiq.models import (
    Department,
    Employee,
    MlPrediction,
    Organization,
    PerformanceReview,
    RbacRole,
    Role,
    UserAccount,
)
from workforceiq.utils.time import utc_now


@pytest.fixture()
def app() -> Iterator:
    flask_app = create_app("testing")
    flask_app.config.update(
        ENABLE_DEV_AUTH=True,
        DEV_AUTH_IDENTITIES={
            "super-admin-1": {"role": "SUPER_ADMIN", "organization_id": "org-demo"},
            "hr-manager-1": {"role": "HR_MANAGER", "department_id": 2, "organization_id": "org-demo"},
            "dept-head-eng-1": {
                "role": "DEPT_HEAD",
                "department_id": 1,
                "employee_id": "EMP-0112",
                "organization_id": "org-demo",
            },
            "employee-priya": {
                "role": "EMPLOYEE",
                "department_id": 1,
                "employee_id": "EMP-0841",
                "organization_id": "org-demo",
            },
            "auditor-1": {"role": "AUDITOR", "organization_id": "org-demo"},
        },
    )

    with flask_app.app_context():
        db.create_all()
        seed_test_data()

    yield flask_app

    with flask_app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def token_for(client):
    def issue(user_id: str) -> str:
        response = client.post("/api/auth/token", json={"user_id": user_id})
        assert response.status_code == 200
        return response.get_json()["access_token"]

    return issue


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def seed_test_data() -> None:
    db.session.add(Organization(id="org-demo", name="Demo Company", status="active"))
    engineering = Department(id=1, organization_id="org-demo", name="Engineering", headcount_target=12, budget=1800000)
    people_ops = Department(id=2, organization_id="org-demo", name="People Ops", headcount_target=4, budget=500000)
    db.session.add_all([engineering, people_ops])

    roles = [
        Role(
            id=1,
            organization_id="org-demo",
            title="Senior Software Engineer",
            level="L5",
            department_id=1,
            salary_band_min=160000,
            salary_band_max=210000,
        ),
        Role(
            id=2,
            organization_id="org-demo",
            title="Engineering Manager",
            level="M1",
            department_id=1,
            salary_band_min=190000,
            salary_band_max=240000,
        ),
        Role(
            id=3,
            organization_id="org-demo",
            title="HR Manager",
            level="M1",
            department_id=2,
            salary_band_min=120000,
            salary_band_max=155000,
        ),
    ]
    db.session.add_all(roles)

    employees = [
        Employee(
            id="EMP-0112",
            organization_id="org-demo",
            name="Ravi Patel",
            email="ravi.patel@example.com",
            department_id=1,
            role_id=2,
            hire_date=date(2021, 3, 14),
            status="Active",
        ),
        Employee(
            id="EMP-0841",
            organization_id="org-demo",
            name="Priya Sharma",
            email="priya.sharma@example.com",
            department_id=1,
            role_id=1,
            hire_date=date(2022, 1, 10),
            status="Active",
            manager_id="EMP-0112",
        ),
        Employee(
            id="EMP-1001",
            organization_id="org-demo",
            name="Anika Rao",
            email="anika.rao@example.com",
            department_id=2,
            role_id=3,
            hire_date=date(2020, 9, 1),
            status="Active",
        ),
    ]
    db.session.add_all(employees)
    db.session.flush()
    engineering.head_id = "EMP-0112"
    people_ops.head_id = "EMP-1001"

    db.session.add_all(
        [
            PerformanceReview(
                employee_id="EMP-0841",
                organization_id="org-demo",
                period="Q3 2025",
                score=90,
                reviewer_id="EMP-0112",
                comments="Expanded project ownership.",
            ),
            PerformanceReview(
                employee_id="EMP-0841",
                organization_id="org-demo",
                period="Q4 2025",
                score=92,
                reviewer_id="EMP-0112",
                comments="Consistent technical leadership.",
            ),
            PerformanceReview(
                employee_id="EMP-0112",
                organization_id="org-demo",
                period="Q4 2025",
                score=87,
                reviewer_id="EMP-1001",
                comments="Stable team execution.",
            ),
            PerformanceReview(
                employee_id="EMP-1001",
                organization_id="org-demo",
                period="Q4 2025",
                score=89,
                reviewer_id="EMP-0112",
                comments="Strong HR operations leadership.",
            ),
        ]
    )

    stale_run_at = utc_now() - timedelta(days=31)
    db.session.add_all(
        [
            MlPrediction(
                employee_id="EMP-0841",
                organization_id="org-demo",
                model_type="attrition",
                prediction=0.12,
                confidence=0.88,
                run_at=stale_run_at,
                features_snapshot={"top_features": ["High review scores", "Low overtime ratio", "Active project lead"]},
            ),
            MlPrediction(
                employee_id="EMP-0841",
                organization_id="org-demo",
                model_type="performance_forecast",
                prediction=94,
                confidence=0.79,
                run_at=utc_now(),
                features_snapshot={"top_features": ["Recent review trend", "Project velocity", "Mentorship load"]},
            ),
            MlPrediction(
                employee_id="EMP-0841",
                organization_id="org-demo",
                model_type="promotion_readiness",
                prediction=1,
                confidence=0.91,
                run_at=utc_now(),
                features_snapshot={"top_features": ["Leadership feedback", "Review consistency", "Project ownership"]},
            ),
            MlPrediction(
                employee_id="EMP-0112",
                organization_id="org-demo",
                model_type="attrition",
                prediction=0.74,
                confidence=0.83,
                run_at=utc_now(),
                features_snapshot={"top_features": ["High overtime ratio", "Promotion stagnation", "Compensation gap"]},
            ),
            MlPrediction(
                employee_id="EMP-1001",
                organization_id="org-demo",
                model_type="attrition",
                prediction=0.28,
                confidence=0.8,
                run_at=utc_now(),
                features_snapshot={"top_features": ["Manager engagement", "Tenure stability", "Role fit"]},
            ),
        ]
    )

    db.session.add_all(
        [
            UserAccount(
                id=1,
                organization_id="org-demo",
                email="hr@example.com",
                password_hash=generate_password_hash("CorrectHorseBatteryStaple!23"),
                role="HR_MANAGER",
                department_id=2,
                employee_id="EMP-1001",
            ),
            RbacRole(
                id=1,
                name="SUPER_ADMIN",
                permissions={"read": "all", "write": "all", "delete": "all"},
                scope="Global",
            ),
            RbacRole(
                id=2,
                name="HR_MANAGER",
                permissions={"read": "all", "write": ["employees", "reviews"]},
                scope="Global",
            ),
            RbacRole(
                id=3,
                name="DEPT_HEAD",
                permissions={"read": "department", "write": ["department_reviews"]},
                scope="Department",
            ),
            RbacRole(
                id=4,
                name="EMPLOYEE",
                permissions={"read": "self", "write": ["self_limited"]},
                scope="Self",
            ),
            RbacRole(
                id=5,
                name="AUDITOR",
                permissions={"read": ["audit_logs", "reports"]},
                scope="Read-only",
            ),
        ]
    )

    db.session.commit()
