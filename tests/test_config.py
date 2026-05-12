from __future__ import annotations

import pytest

from workforceiq import create_app
from workforceiq.config import resolve_config_name


def test_resolve_config_name_rejects_unknown_value(monkeypatch):
    monkeypatch.setenv("WORKFORCEIQ_CONFIG", "qa")

    with pytest.raises(ValueError, match="Invalid config"):
        resolve_config_name(None)


def test_testing_config_ignores_development_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///should-not-be-used.db")

    app = create_app("testing")

    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite+pysqlite:///:memory:"


def test_production_rejects_sqlite_database(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "a" * 64)
    monkeypatch.setenv("JWT_SECRET_KEY", "b" * 64)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///prod.db")

    with pytest.raises(RuntimeError, match="Production must use MySQL"):
        create_app("production")


def test_production_accepts_strong_runtime_config(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "a" * 64)
    monkeypatch.setenv("JWT_SECRET_KEY", "b" * 64)
    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://user:pass@localhost:3306/workforceiq")
    monkeypatch.setenv("ENABLE_DEV_AUTH", "true")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")

    app = create_app("production")

    assert app.config["ENABLE_DEV_AUTH"] is False
    assert app.config["SQLALCHEMY_DATABASE_URI"].startswith("mysql+pymysql://")


def test_production_rejects_shorter_refresh_token_lifetime(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "a" * 64)
    monkeypatch.setenv("JWT_SECRET_KEY", "b" * 64)
    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://user:pass@localhost:3306/workforceiq")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRES", "3600")
    monkeypatch.setenv("JWT_REFRESH_TOKEN_EXPIRES", "300")

    with pytest.raises(RuntimeError, match="refresh tokens must live longer"):
        create_app("production")


def test_production_rejects_incomplete_oidc_configuration(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "a" * 64)
    monkeypatch.setenv("JWT_SECRET_KEY", "b" * 64)
    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://user:pass@localhost:3306/workforceiq")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("OIDC_ENABLED", "true")
    monkeypatch.delenv("OIDC_ISSUER", raising=False)
    monkeypatch.delenv("OIDC_AUDIENCE", raising=False)
    monkeypatch.delenv("OIDC_JWKS_URI", raising=False)
    monkeypatch.delenv("OIDC_JWKS_JSON", raising=False)

    with pytest.raises(RuntimeError, match="OIDC_ISSUER"):
        create_app("production")
