# WorkforceIQ AI

Starter Flask backend scaffold for the WorkforceIQ AI system prompt. The project encodes the prompt's core operational rules into code: RBAC-aware employee access, structured profile assembly, attrition reporting, department health checks, and audit-log-ready write operations.

## What is included

- Flask app factory with environment-based configuration
- SQLAlchemy models for the core workforce schema
- JWT-based request context with explicit role enforcement
- Employee profile lookup with joins to departments, roles, performance reviews, and ML predictions
- Attrition risk reporting with stale-prediction flags and financial exposure estimates
- Department health checks with traffic-light scoring
- Write-ready employee update endpoint that records audit logs
- Dev token endpoint and demo seed script for local testing
- Persisted account login with MFA setup/verification and lockout
- Tenant-aware schema and Alembic migration scaffold
- Employee search endpoint with Elasticsearch adapter and SQL fallback
- Compliance request/export workflow
- Celery task hooks and redacted JSON backup tooling

## Quick start

1. Create a virtual environment and install dependencies.
2. Copy `.env.example` to `.env` and adjust settings.
3. Seed demo data.
4. Run the Flask server.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python scripts\seed_demo_data.py
python run.py
```

The app defaults to `sqlite:///workforceiq.db` if `DATABASE_URL` is not set, which makes local evaluation easier. Production should use MySQL 8.x through `DATABASE_URL`.

The example `.env` is set up for local SQLite development. For production, switch `WORKFORCEIQ_CONFIG=production`, disable dev auth, and point `DATABASE_URL` to MySQL.

## Dev auth flow

Request a local JWT token from one of the registered development identities:

```http
POST /api/auth/token
Content-Type: application/json

{
  "user_id": "hr-manager-1",
  "role": "HR_MANAGER"
}
```

Use the returned token on protected routes:

```http
Authorization: Bearer <token>
```

Registered local dev identities currently include `super-admin-1`, `hr-manager-1`, `dept-head-eng-1`, `employee-priya`, and `auditor-1`.

For persisted auth testing after seeding demo data:

```http
POST /api/auth/login
Content-Type: application/json

{
  "organization_id": "org-demo",
  "email": "hr@example.com",
  "password": "CorrectHorseBatteryStaple!23"
}
```

## Core endpoints

- `GET /api/health`
- `POST /api/auth/token`
- `POST /api/auth/login`
- `POST /api/auth/mfa/setup`
- `POST /api/auth/mfa/verify`
- `GET /api/employees/<employee_id>`
- `PATCH /api/employees/<employee_id>`
- `GET /api/search/employees`
- `GET /api/departments/<department_id>/health`
- `GET /api/reports/attrition-risk`
- `GET /api/audit-logs`
- `POST /api/compliance/requests`
- `GET /api/compliance/requests`

## Manual verification

1. Seed the demo data and request a `HR_MANAGER` token.
2. Call `GET /api/employees/EMP-0841` and verify department, role, latest review, and model predictions are returned.
3. Call `GET /api/reports/attrition-risk` and verify the report groups employees into `HIGH`, `MEDIUM`, and `LOW`.
4. Call `PATCH /api/employees/EMP-0841` with a changed email and verify an `audit_logs` row is written.
5. Request an `EMPLOYEE` token for a different employee and confirm cross-profile access is denied.

## Schema gaps called out by the scaffold

The prompt requests open requisition counts and salary-band compliance checks, but the provided schema does not include a requisitions table or actual employee compensation fields. The department health endpoint returns these as unavailable rather than guessing.
=======
# -WorkforceIQ-AI-
WorkforceIQ AI is an intelligent employee data management system using Flask, MySQL, and ML to organize workforce data, analyse performance trends, enable fast search, and ensure secure RBAC-based access.
