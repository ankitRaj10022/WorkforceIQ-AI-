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
    return data
