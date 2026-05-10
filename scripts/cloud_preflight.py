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


def main() -> int:
    env_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("cloud/compose/.env.cloud")
    if not env_path.exists():
        print(f"Missing env file: {env_path}")
        return 1

    values = _load_env(env_path)
    missing = sorted(key for key in REQUIRED_KEYS if not values.get(key))
    if missing:
        print(f"Missing required keys: {', '.join(missing)}")
        return 1

    errors = []
    if values["WORKFORCEIQ_CONFIG"] != "production":
        errors.append("WORKFORCEIQ_CONFIG must be production.")
    if values.get("ENABLE_DEV_AUTH", "false").lower() != "false":
        errors.append("ENABLE_DEV_AUTH must be false.")
    if values["DATABASE_URL"].startswith("sqlite"):
        errors.append("DATABASE_URL must not use SQLite.")
    if len(values["SECRET_KEY"]) < 32 or len(values["JWT_SECRET_KEY"]) < 32:
        errors.append("SECRET_KEY and JWT_SECRET_KEY must each be at least 32 characters.")
    if values["SECRET_KEY"] == values["JWT_SECRET_KEY"]:
        errors.append("SECRET_KEY and JWT_SECRET_KEY must be different.")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("cloud-preflight-ok")
    return 0


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
