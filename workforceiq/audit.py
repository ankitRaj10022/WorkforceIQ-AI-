from __future__ import annotations

from flask import g, request

from workforceiq.extensions import db
from workforceiq.models import AuditLog


def record_audit_log(
    *,
    user_id: str,
    organization_id: str,
    action: str,
    target_entity: str,
    target_id: str,
    fields_changed: list[str],
    old_values: dict,
    new_values: dict,
    extra_metadata: dict | None = None,
) -> AuditLog:
    metadata = {
        "fields_changed": fields_changed,
        "old_values": old_values,
        "new_values": new_values,
    }
    if extra_metadata:
        metadata.update(extra_metadata)

    audit_log = AuditLog(
        organization_id=organization_id,
        user_id=user_id,
        action=action,
        target_entity=target_entity,
        target_id=target_id,
        metadata_json=metadata,
        request_id=getattr(g, "request_id", None),
        ip_address=request.remote_addr,
    )
    db.session.add(audit_log)
    return audit_log
