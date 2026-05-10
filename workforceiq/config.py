from __future__ import annotations

import json
import os
from datetime import timedelta

DEFAULT_DEV_AUTH_IDENTITIES = {
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
}


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    return int(raw)


def _load_dev_auth_identities(default: dict) -> dict:
    raw = os.getenv("DEV_AUTH_IDENTITIES_JSON")
    if not raw:
        return default

    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("DEV_AUTH_IDENTITIES_JSON must be a JSON object keyed by user_id.")
    return parsed


class BaseConfig:
    ENV_NAME = "base"
    APP_VERSION = "3.0.0"
    COMPANY_NAME = "WorkforceIQ"
    DEFAULT_ORGANIZATION_ID = "org-demo"
    DEBUG = False
    TESTING = False
    # Development fallback only; production validation rejects placeholder secrets.
    SECRET_KEY = "dev-secret-key-change-me-please-123456"  # nosec B105
    SQLALCHEMY_DATABASE_URI = "sqlite:///workforceiq.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Development fallback only; production validation rejects placeholder secrets.
    JWT_SECRET_KEY = "dev-jwt-secret-key-change-me-please-123456"  # nosec B105
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    REDIS_URL = "redis://localhost:6379/0"
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    ENABLE_DEV_AUTH = False
    DEV_AUTH_IDENTITIES: dict[str, dict] = {}
    MAX_EXPORT_ROWS = 500
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    RATE_LIMIT_PER_MINUTE = 100
    RATE_LIMIT_BACKEND = "auto"
    AUTH_LOCKOUT_THRESHOLD = 5
    AUTH_LOCKOUT_MINUTES = 15
    ML_STALE_DAYS = 30
    ELASTICSEARCH_URL = ""
    BACKUP_DIRECTORY = "backups"
    CORS_ORIGINS: list[str] = []
    LOG_LEVEL = "INFO"
    STRUCTURED_LOGS = True
    JSON_SORT_KEYS = False


class DevelopmentConfig(BaseConfig):
    ENV_NAME = "development"
    DEBUG = True
    ENABLE_DEV_AUTH = True
    DEV_AUTH_IDENTITIES = DEFAULT_DEV_AUTH_IDENTITIES
    LOG_LEVEL = "DEBUG"


class TestingConfig(BaseConfig):
    ENV_NAME = "testing"
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite+pysqlite:///:memory:"
    ENABLE_DEV_AUTH = True
    DEV_AUTH_IDENTITIES = DEFAULT_DEV_AUTH_IDENTITIES
    RATE_LIMIT_BACKEND = "memory"


class ProductionConfig(BaseConfig):
    ENV_NAME = "production"
    DEBUG = False
    ENABLE_DEV_AUTH = False
    DEV_AUTH_IDENTITIES = {}


config_by_name = {
    "default": ProductionConfig,
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def resolve_config_name(config_name: str | None) -> str:
    selected = (config_name or os.getenv("WORKFORCEIQ_CONFIG") or os.getenv("FLASK_ENV") or "production").lower()
    if selected not in config_by_name:
        allowed = ", ".join(sorted(config_by_name))
        raise ValueError(f"Invalid config name `{selected}`. Allowed values: {allowed}.")
    return selected


def apply_runtime_settings(app) -> None:
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", app.config["SECRET_KEY"])
    if app.config["TESTING"]:
        app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
            "TEST_DATABASE_URL",
            app.config["SQLALCHEMY_DATABASE_URI"],
        )
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", app.config["SQLALCHEMY_DATABASE_URI"])
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", app.config["JWT_SECRET_KEY"])
    jwt_exp_seconds = os.getenv("JWT_ACCESS_TOKEN_EXPIRES")
    if jwt_exp_seconds is not None:
        app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(seconds=int(jwt_exp_seconds))
    else:
        app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=_int_env("JWT_ACCESS_TOKEN_HOURS", 8))
    app.config["REDIS_URL"] = os.getenv("REDIS_URL", app.config["REDIS_URL"])
    app.config["CELERY_BROKER_URL"] = os.getenv("CELERY_BROKER_URL", app.config["CELERY_BROKER_URL"])
    app.config["CELERY_RESULT_BACKEND"] = os.getenv("CELERY_RESULT_BACKEND", app.config["CELERY_RESULT_BACKEND"])
    app.config["MAX_EXPORT_ROWS"] = min(max(_int_env("MAX_EXPORT_ROWS", app.config["MAX_EXPORT_ROWS"]), 1), 500)
    app.config["MAX_CONTENT_LENGTH"] = _int_env("MAX_CONTENT_LENGTH", app.config["MAX_CONTENT_LENGTH"])
    app.config["RATE_LIMIT_PER_MINUTE"] = max(_int_env("RATE_LIMIT_PER_MINUTE", app.config["RATE_LIMIT_PER_MINUTE"]), 1)
    app.config["ML_STALE_DAYS"] = max(_int_env("ML_STALE_DAYS", app.config["ML_STALE_DAYS"]), 1)
    app.config["ENABLE_DEV_AUTH"] = _bool_env("ENABLE_DEV_AUTH", app.config["ENABLE_DEV_AUTH"])
    app.config["DEV_AUTH_IDENTITIES"] = _load_dev_auth_identities(app.config.get("DEV_AUTH_IDENTITIES", {}))
    app.config["APP_VERSION"] = os.getenv("APP_VERSION", app.config["APP_VERSION"])
    app.config["COMPANY_NAME"] = os.getenv("COMPANY_NAME", app.config["COMPANY_NAME"])
    app.config["DEFAULT_ORGANIZATION_ID"] = os.getenv(
        "DEFAULT_ORGANIZATION_ID",
        app.config["DEFAULT_ORGANIZATION_ID"],
    )
    app.config["LOG_LEVEL"] = os.getenv("LOG_LEVEL", app.config["LOG_LEVEL"])
    app.config["RATE_LIMIT_BACKEND"] = os.getenv("RATE_LIMIT_BACKEND", app.config["RATE_LIMIT_BACKEND"]).lower()
    app.config["AUTH_LOCKOUT_THRESHOLD"] = max(
        _int_env("AUTH_LOCKOUT_THRESHOLD", app.config["AUTH_LOCKOUT_THRESHOLD"]),
        1,
    )
    app.config["AUTH_LOCKOUT_MINUTES"] = max(
        _int_env("AUTH_LOCKOUT_MINUTES", app.config["AUTH_LOCKOUT_MINUTES"]),
        1,
    )
    app.config["ELASTICSEARCH_URL"] = os.getenv("ELASTICSEARCH_URL", app.config["ELASTICSEARCH_URL"])
    app.config["BACKUP_DIRECTORY"] = os.getenv("BACKUP_DIRECTORY", app.config["BACKUP_DIRECTORY"])
    app.config["STRUCTURED_LOGS"] = _bool_env("STRUCTURED_LOGS", app.config["STRUCTURED_LOGS"])
    cors_origins = os.getenv("CORS_ORIGINS")
    if cors_origins:
        app.config["CORS_ORIGINS"] = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]

    if app.config["ENV_NAME"] == "production":
        app.config["ENABLE_DEV_AUTH"] = False
        app.config["DEV_AUTH_IDENTITIES"] = {}


def validate_runtime_config(app) -> None:
    if app.config["ENV_NAME"] != "production":
        return

    insecure_values = {
        "dev-secret-key-change-me-please-123456",
        "dev-jwt-secret-key-change-me-please-123456",
        "change-me-please-use-a-long-random-secret",
        "change-me-please-use-a-long-random-jwt-secret",
    }
    for key_name in ("SECRET_KEY", "JWT_SECRET_KEY"):
        value = app.config.get(key_name, "")
        if value in insecure_values or len(value) < 32:
            raise RuntimeError(f"{key_name} must be set to a strong random value in production.")

    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
        raise RuntimeError("Production must use MySQL through DATABASE_URL, not SQLite.")

    if not app.config["CORS_ORIGINS"]:
        raise RuntimeError("Production must set CORS_ORIGINS to the approved frontend origin list.")

    if app.config["RATE_LIMIT_BACKEND"] not in {"auto", "redis"}:
        raise RuntimeError("Production rate limiting must use Redis or auto Redis discovery.")
