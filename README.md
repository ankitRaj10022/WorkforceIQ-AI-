# WorkforceIQ AI

WorkforceIQ AI is a workforce intelligence backend designed for companies that want to move beyond fragmented HR tools, spreadsheet reporting, and manual review cycles. It brings employee records, role-based access, search, reporting, auditability, and ML-assisted insight into one operational platform.

This repository contains the backend foundation: a Flask API, relational data model, authentication layer, reporting services, async task hooks, and AWS deployment paths for pilot and pre-production environments.

## Why WorkforceIQ

Most organizations do not struggle because they lack employee data. They struggle because their data is spread across too many systems, the reporting is delayed, and access control is inconsistent.

WorkforceIQ is built to solve that operational gap.

- One profile view for workforce records, performance history, and ML outputs.
- Role-aware access so HR, managers, auditors, and employees do not see the same surface.
- Search designed for real operating teams, not just raw database lookup.
- Audit-ready change tracking for sensitive updates.
- Department and attrition reporting that turns data into an action list.
- A backend architecture that can start lean and grow into a full production stack.

## What The Platform Does

### Workforce records

- Maintains employee, department, role, session, and review data in a structured relational model.
- Supports manager relationships, department ownership, role hierarchy, and organization scoping.
- Returns joined employee profiles instead of forcing consumers to assemble them manually.

### Secure access control

- JWT-based authentication for API access.
- Role-aware authorization across employee data, reports, and audit logs.
- MFA enrollment and verification for persisted user accounts.
- Login lockout handling to reduce repeated password attack risk.

### Workforce analytics

- Employee profile summaries with latest performance data and recent ML predictions.
- Department health checks covering headcount alignment, performance benchmark, and attrition concentration.
- Attrition risk reports grouped by department with estimated financial exposure.
- Stale model output detection so old predictions are not treated as current truth.

### Search and retrieval

- Employee search by employee ID, name, email, department, role, and level.
- SQL fallback search built into the core app.
- Elasticsearch adapter available for stronger relevance scoring and scale-out search.

### Governance and operations

- Audit logging for write operations and authentication events.
- Compliance request workflow for traceable administrative actions.
- Celery hooks for asynchronous indexing, reporting, and ML tasks.
- Backup tooling for JSON export of database contents.

## Client-Facing Value

WorkforceIQ is intended for companies that are evaluating a shift from disconnected HR operations to a more unified workforce platform.

Typical use cases:

- HR leaders who need department-level workforce visibility without waiting on manual reports.
- Business units that want manager access without exposing global HR data.
- Founders or operations teams building internal systems before committing to large HR suites.
- Organizations piloting workforce analytics before a broader digital transformation effort.

In practical terms, WorkforceIQ helps clients:

- reduce reporting lag,
- tighten access boundaries,
- make attrition and performance risk visible earlier,
- centralize workforce records behind an API,
- create a cleaner path from pilot to production.

## Product Capabilities In This Repository

| Area | Current capability |
|---|---|
| Employee profiles | Joined employee profile response with department, role, manager, recent reviews, and ML predictions |
| Authentication | JWT login, development token flow, MFA setup and verification |
| Authorization | Role-aware access control for employee data, reports, and audit logs |
| Reporting | Attrition risk report and department health check endpoints |
| Search | SQL search with Elasticsearch integration path |
| Auditability | Structured audit log writes for update and login events |
| Data model | Multi-entity workforce schema with organization-aware scoping |
| Migrations | Alembic migration scaffold with initial industry schema |
| Async hooks | Celery worker wiring for search and reporting tasks |
| Deployment | AWS single-host deployment path and managed-stack infrastructure path |

## Architecture

### Application stack

- Python 3.11+ compatible Flask backend
- SQLAlchemy ORM
- Alembic migrations
- JWT auth
- Redis-backed rate limiting and task queue support
- Celery worker integration
- Optional Elasticsearch search backend

### Core data model

The schema includes these primary business entities:

- `organizations`
- `employees`
- `departments`
- `roles`
- `performance_reviews`
- `ml_predictions`
- `rbac_roles`
- `user_accounts`
- `user_sessions`
- `audit_logs`
- `compliance_requests`

### Deployment shapes

Two deployment directions are already represented in the repo:

1. Low-cost single-host AWS deployment for pilot or pre-production use.
2. Managed AWS infrastructure path for a more formal production architecture.

The low-cost AWS path has been validated on EC2 with:

- Nginx
- Flask app
- MySQL
- Redis
- Celery worker

## API Surface

Main endpoints currently exposed by the backend:

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

## Local Evaluation

The project is easy to run locally for client demos, internal review, or developer onboarding.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python scripts\seed_demo_data.py
python run.py
```

By default, local evaluation can use SQLite for zero-friction setup. Production and serious staging should use MySQL.

## Demo Access

For local development, the repository includes a development token flow and seeded demo identities such as:

- `super-admin-1`
- `hr-manager-1`
- `dept-head-eng-1`
- `employee-priya`
- `auditor-1`

That is useful for evaluation and QA. It is not intended for production use.

## Deployment Notes

For low-cost AWS rollout and redeploy instructions, see:

- [docs/aws-free-tier-deployment.md](docs/aws-free-tier-deployment.md)
- [scripts/deploy_active_aws_free.ps1](scripts/deploy_active_aws_free.ps1)

For the broader managed AWS infrastructure path, see:

- [docs/aws-deployment.md](docs/aws-deployment.md)

## Current Delivery Status

WorkforceIQ is strongest today as:

- a serious client demo environment,
- an internal pilot platform,
- a pre-production backend foundation,
- a customizable workforce operations core for further productization.

It is already beyond a throwaway prototype. The application includes real authorization, migrations, audit logging, search, reporting, and deployment automation.

For a full enterprise production rollout, the next layer would typically include:

- managed database and cache services,
- company SSO and identity federation,
- finalized compliance and retention workflows,
- managed observability and backup policies,
- hardened HTTPS and domain routing,
- scale testing under production traffic patterns.

## Repository Layout

```text
workforceiq/                 Core Flask application
workforceiq/api/             API routes
workforceiq/services/        Business logic and reporting services
workforceiq/security/        MFA support
migrations/                  Alembic migration history
scripts/                     Seed, backup, bootstrap, and deployment helpers
infra/aws/                   Managed AWS infrastructure path
infra/aws-free/              Low-cost AWS single-host deployment path
docs/                        Deployment and operations notes
tests/                       Test suite
```

## For Prospective Clients

If you are reviewing this project as a potential internal platform or as the base for a client deployment, the main point is straightforward:

WorkforceIQ is not just an employee directory. It is a backend platform for workforce operations, governed access, searchable records, and decision support.

It is designed to give organizations a practical path away from disconnected HR tooling and toward a more controlled, analytics-ready operating model.
