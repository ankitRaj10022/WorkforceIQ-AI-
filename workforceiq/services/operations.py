from __future__ import annotations

import os
from pathlib import Path

from flask import current_app
from sqlalchemy import text

from workforceiq.extensions import db
from workforceiq.utils.time import to_utc_iso, utc_now


def generate_liveness_report() -> dict:
    return {
        "service": "WorkforceIQ AI",
        "status": "ok",
        "kind": "liveness",
        "timestamp": to_utc_iso(utc_now()),
        "version": current_app.config["APP_VERSION"],
        "environment": current_app.config["ENV_NAME"],
    }


def generate_readiness_report() -> tuple[dict, int]:
    checks = {
        "database": _database_check(),
        "redis": _redis_check(),
        "backup_storage": _backup_storage_check(),
        "search": _search_check(),
    }
    ready = all(result["status"] == "ready" for result in checks.values() if result["required"])
    payload = {
        "service": "WorkforceIQ AI",
        "status": "ready" if ready else "not_ready",
        "kind": "readiness",
        "timestamp": to_utc_iso(utc_now()),
        "version": current_app.config["APP_VERSION"],
        "environment": current_app.config["ENV_NAME"],
        "checks": checks,
    }
    return payload, 200 if ready else 503


def _database_check() -> dict:
    try:
        result = db.session.execute(text("SELECT 1")).scalar_one()
        return {
            "required": True,
            "status": "ready",
            "details": {"probe": "SELECT 1", "result": result},
        }
    except Exception as exc:  # pragma: no cover - depends on live database failures
        return {
            "required": True,
            "status": "failed",
            "details": {"error": str(exc)},
        }


def _redis_check() -> dict:
    required = current_app.config["RATE_LIMIT_BACKEND"] != "memory"
    if not required:
        return {
            "required": False,
            "status": "skipped",
            "details": {"reason": "RATE_LIMIT_BACKEND=memory"},
        }

    try:
        from redis import Redis

        client = Redis.from_url(current_app.config["REDIS_URL"], decode_responses=True)
        result = client.ping()
        return {
            "required": True,
            "status": "ready" if result else "failed",
            "details": {
                "url_scheme": current_app.config["REDIS_URL"].split("://", 1)[0],
                "ping": bool(result),
            },
        }
    except Exception as exc:  # pragma: no cover - depends on live redis failures
        return {
            "required": True,
            "status": "failed",
            "details": {"error": str(exc)},
        }


def _backup_storage_check() -> dict:
    backup_path = Path(current_app.config["BACKUP_DIRECTORY"])
    try:
        resolved = backup_path.resolve(strict=False)
    except OSError:
        resolved = backup_path

    if backup_path.exists():
        writable = os.access(backup_path, os.W_OK)
        return {
            "required": current_app.config["ENV_NAME"] == "production",
            "status": "ready" if writable else "failed",
            "details": {"path": str(resolved), "exists": True, "writable": writable},
        }

    parent = backup_path.parent if backup_path.parent != Path("") else Path(".")
    parent_exists = parent.exists()
    parent_writable = os.access(parent, os.W_OK) if parent_exists else False
    return {
        "required": current_app.config["ENV_NAME"] == "production",
        "status": "ready" if parent_exists and parent_writable else "failed",
        "details": {
            "path": str(resolved),
            "exists": False,
            "parent": str(parent.resolve(strict=False)),
            "parent_writable": parent_writable,
            "reason": "backup directory will be created on first export" if parent_writable else "parent directory is not writable",
        },
    }


def _search_check() -> dict:
    if not current_app.config.get("ELASTICSEARCH_URL"):
        return {
            "required": False,
            "status": "skipped",
            "details": {"backend": "sql_fallback", "reason": "ELASTICSEARCH_URL is not configured"},
        }

    try:
        from elasticsearch import Elasticsearch

        client = Elasticsearch(current_app.config["ELASTICSEARCH_URL"])
        ping = client.ping()
        return {
            "required": False,
            "status": "ready" if ping else "failed",
            "details": {"backend": "elasticsearch", "ping": bool(ping)},
        }
    except Exception as exc:  # pragma: no cover - depends on external search availability
        return {
            "required": False,
            "status": "failed",
            "details": {"backend": "elasticsearch", "error": str(exc)},
        }
