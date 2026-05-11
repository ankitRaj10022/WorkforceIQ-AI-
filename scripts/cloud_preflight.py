from __future__ import annotations

import os
import sys
from pathlib import Path

REQUIRED_KEYS = {
    "WORKFORCEIQ_CONFIG",
    "SECRET_KEY",
    "JWT_SECRET_KEY",
    "DATABASE_URL",
    "REDIS_URL",
    "CELERY_BROKER_URL",
    "CELERY_RESULT_BACKEND",
    "CORS_ORIGINS",
    "APP_DOMAIN",
    "ACME_EMAIL",
    "MYSQL_ROOT_PASSWORD",
    "MYSQL_PASSWORD",
}
DEFAULT_ENV_CANDIDATES = (
    Path(".env.cloud"),
    Path("cloud/compose/.env.cloud"),
    Path("cloud/compose/env.cloud.example"),
)


def main() -> int:
    env_path = _resolve_env_path(sys.argv[1] if len(sys.argv) > 1 else None)
    if env_path is None:
        tried = ", ".join(str(path) for path in DEFAULT_ENV_CANDIDATES)
        print(f"Missing env file. Tried: {tried}")
        return 1

    values = _load_env(env_path)
    missing = sorted(key for key in REQUIRED_KEYS if not values.get(key))
    if missing:
        print(f"Missing required keys: {', '.join(missing)}")
        return 1

    errors = validate_values(values)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("cloud-preflight-ok")
    return 0


def validate_values(values: dict[str, str]) -> list[str]:
    errors = []
    if values["WORKFORCEIQ_CONFIG"] != "production":
        errors.append("WORKFORCEIQ_CONFIG must be production.")
    if values.get("ENABLE_DEV_AUTH", "false").lower() != "false":
        errors.append("ENABLE_DEV_AUTH must be false.")
    if values["DATABASE_URL"].startswith("sqlite"):
        errors.append("DATABASE_URL must not use SQLite.")
    if not values["DATABASE_URL"].startswith("mysql"):
        errors.append("DATABASE_URL must use a MySQL driver and host.")
    if len(values["SECRET_KEY"]) < 32 or len(values["JWT_SECRET_KEY"]) < 32:
        errors.append("SECRET_KEY and JWT_SECRET_KEY must each be at least 32 characters.")
    if values["SECRET_KEY"] == values["JWT_SECRET_KEY"]:
        errors.append("SECRET_KEY and JWT_SECRET_KEY must be different.")
    if len(values["MYSQL_ROOT_PASSWORD"]) < 16 or len(values["MYSQL_PASSWORD"]) < 16:
        errors.append("MYSQL_ROOT_PASSWORD and MYSQL_PASSWORD must each be at least 16 characters.")
    if not values["APP_DOMAIN"] or _looks_placeholder(values["APP_DOMAIN"]) or "localhost" in values["APP_DOMAIN"].lower():
        errors.append("APP_DOMAIN must be set to the real cloud DNS name, not a placeholder or localhost.")
    if not values["ACME_EMAIL"] or values["ACME_EMAIL"].lower().endswith("@example.com"):
        errors.append("ACME_EMAIL must be a real mailbox for certificate and operational notices.")
    if any(host in values["CORS_ORIGINS"].lower() for host in ("localhost", "127.0.0.1", "example.com")):
        errors.append("CORS_ORIGINS must point to the real frontend origin, not localhost or example.com.")
    if not values["REDIS_URL"].startswith(("redis://", "rediss://")):
        errors.append("REDIS_URL must use redis:// or rediss://.")
    if values["CELERY_BROKER_URL"] != values["REDIS_URL"]:
        errors.append("CELERY_BROKER_URL must match REDIS_URL for the single-host cloud deployment.")
    if values["CELERY_RESULT_BACKEND"] != values["REDIS_URL"]:
        errors.append("CELERY_RESULT_BACKEND must match REDIS_URL for the single-host cloud deployment.")

    for key in ("SECRET_KEY", "JWT_SECRET_KEY", "MYSQL_ROOT_PASSWORD", "MYSQL_PASSWORD", "DATABASE_URL"):
        if _looks_placeholder(values[key]):
            errors.append(f"{key} still contains a placeholder value.")
    return errors


def _resolve_env_path(argument: str | None) -> Path | None:
    if argument:
        path = Path(argument)
        return path if path.exists() else None
    for candidate in DEFAULT_ENV_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def _looks_placeholder(value: str) -> bool:
    lowered = value.lower()
    return any(
        marker in lowered
        for marker in (
            "replace-",
            "change-me",
            "example.com",
            "your-api-domain",
            "admin@example.com",
        )
    )


def _load_env(path: Path) -> dict[str, str]:
    values = dict(os.environ)
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


if __name__ == "__main__":
    raise SystemExit(main())
