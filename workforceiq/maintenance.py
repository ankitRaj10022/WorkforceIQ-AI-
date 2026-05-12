from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select

from workforceiq.extensions import db
from workforceiq.models import (
    AuditLog,
    ComplianceRequest,
    Department,
    Employee,
    MlPrediction,
    Organization,
    PerformanceReview,
    RbacRole,
    Role,
    UserAccount,
    UserSession,
)
from workforceiq.utils.time import to_utc_iso, utc_now

BACKUP_MODELS = (
    Organization,
    Department,
    Role,
    Employee,
    PerformanceReview,
    RbacRole,
    UserSession,
    AuditLog,
    MlPrediction,
    UserAccount,
    ComplianceRequest,
)
REDACTION_MARKER = "[REDACTED]"


def export_database_backup(output_path: Path) -> dict:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": to_utc_iso(utc_now()),
        "format": "workforceiq-json-backup-v1",
        "tables": {
            model.__tablename__: [_serialize_model(row) for row in db.session.execute(select(model)).scalars().all()]
            for model in BACKUP_MODELS
        },
    }
    output_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return {
        "backup_path": str(output_path),
        "tables": {table: len(rows) for table, rows in payload["tables"].items()},
        "generated_at": payload["generated_at"],
    }


def verify_database_backup(backup_path: Path) -> dict:
    try:
        payload = json.loads(backup_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Backup file does not exist: {backup_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Backup file is not valid JSON: {backup_path}") from exc
    errors: list[str] = []

    if payload.get("format") != "workforceiq-json-backup-v1":
        errors.append("Backup format marker is invalid.")
    if not isinstance(payload.get("generated_at"), str) or not payload["generated_at"]:
        errors.append("Backup is missing generated_at.")

    tables = payload.get("tables")
    if not isinstance(tables, dict):
        errors.append("Backup tables payload is invalid.")
        tables = {}

    expected_tables = {model.__tablename__ for model in BACKUP_MODELS}
    missing_tables = sorted(expected_tables - set(tables))
    if missing_tables:
        errors.append(f"Backup is missing tables: {', '.join(missing_tables)}.")

    for account in tables.get("user_accounts", []):
        if account.get("password_hash") != REDACTION_MARKER:
            errors.append("user_accounts.password_hash is not redacted.")
            break
        if account.get("mfa_secret") not in {None, REDACTION_MARKER}:
            errors.append("user_accounts.mfa_secret is not redacted.")
            break

    for session in tables.get("user_sessions", []):
        if session.get("refresh_token_jti") not in {None, REDACTION_MARKER}:
            errors.append("user_sessions.refresh_token_jti is not redacted.")
            break

    if errors:
        raise ValueError(" ".join(errors))

    return {
        "backup_path": str(backup_path),
        "format": payload["format"],
        "generated_at": payload["generated_at"],
        "tables": {table: len(rows) for table, rows in tables.items()},
    }


def _serialize_model(row) -> dict:
    data = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        if hasattr(value, "isoformat"):
            value = to_utc_iso(value) if column.name.endswith("_at") or column.name.endswith("_until") else value.isoformat()
        data[column.name] = value
    if row.__tablename__ == "user_accounts":
        data["password_hash"] = REDACTION_MARKER
        data["mfa_secret"] = REDACTION_MARKER if data.get("mfa_secret") else None
    if row.__tablename__ == "user_sessions":
        data["refresh_token_jti"] = REDACTION_MARKER if data.get("refresh_token_jti") else None
    return data
