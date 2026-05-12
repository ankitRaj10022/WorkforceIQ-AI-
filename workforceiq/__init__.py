from __future__ import annotations

import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, g, jsonify, request
from flask_jwt_extended.exceptions import JWTExtendedException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from workforceiq.api.routes import api_bp
from workforceiq.config import apply_runtime_settings, config_by_name, resolve_config_name, validate_runtime_config
from workforceiq.errors import ApiError
from workforceiq.extensions import db, jwt, migrate
from workforceiq.logging_config import configure_logging, register_request_logging
from workforceiq.maintenance import export_database_backup, verify_database_backup
from workforceiq.models import UserSession
from workforceiq.rate_limit import RateLimiter, rate_limit_key_from_request

load_dotenv()


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    selected_config = resolve_config_name(config_name)
    app.config.from_object(config_by_name[selected_config])
    apply_runtime_settings(app)
    validate_runtime_config(app)
    configure_logging(app)

    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    app.register_blueprint(api_bp)

    register_error_handlers(app)
    register_request_guards(app)
    register_jwt_callbacks(app)
    register_security_headers(app)
    register_request_logging(app)
    register_cli_commands(app)

    return app


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError):
        response = {"error": error.message}
        if error.payload:
            response["details"] = error.payload
        return jsonify(response), error.status_code

    @app.errorhandler(JWTExtendedException)
    def handle_jwt_error(error: JWTExtendedException):
        return jsonify({"error": str(error)}), 401

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(_error: IntegrityError):
        db.session.rollback()
        return jsonify({"error": "The requested change violates a data integrity constraint."}), 400

    @app.errorhandler(OperationalError)
    def handle_operational_error(_error: OperationalError):
        db.session.rollback()
        if _is_uninitialized_local_database_error(app, _error):
            return (
                jsonify(
                    {
                        "error": (
                            "Local development database is not initialized. "
                            "Run `python scripts/seed_demo_data.py` to create the demo schema and records, "
                            "then retry the request."
                        )
                    }
                ),
                503,
            )
        return (
            jsonify(
                {
                    "error": "Unable to connect to the workforce database. Check your MySQL connection or contact your admin."
                }
            ),
            503,
        )

    @app.errorhandler(SQLAlchemyError)
    def handle_sqlalchemy_error(_error: SQLAlchemyError):
        db.session.rollback()
        return jsonify({"error": "Unable to process the workforce database request."}), 500

    @app.errorhandler(404)
    def handle_not_found(_error):
        return jsonify({"error": "Resource not found."}), 404

    @app.errorhandler(500)
    def handle_internal_error(_error):
        return jsonify({"error": "Unable to process the request."}), 500


def register_request_guards(app: Flask) -> None:
    app.extensions["rate_limiter"] = RateLimiter(app)

    @app.before_request
    def apply_request_guards():
        g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        if app.config["TESTING"]:
            return None

        limit = app.config["RATE_LIMIT_PER_MINUTE"]
        key, claims = rate_limit_key_from_request(
            authorization_header=request.headers.get("Authorization"),
            remote_addr=request.remote_addr,
            organization_hint=request.headers.get("X-Organization-ID") or app.config["DEFAULT_ORGANIZATION_ID"],
        )
        g.rate_limit_claims = claims
        result = app.extensions["rate_limiter"].hit(key, limit=limit)
        if not result.allowed:
            response = jsonify({"error": "Rate limit exceeded. Retry after 60 seconds."})
            response.status_code = 429
            response.headers["X-RateLimit-Backend"] = result.backend
            response.headers["X-RateLimit-Remaining"] = str(result.remaining)
            return response
        return None


def register_jwt_callbacks(app: Flask) -> None:
    @jwt.token_in_blocklist_loader
    def is_token_revoked(_jwt_header, jwt_payload: dict) -> bool:
        session_id = jwt_payload.get("session_id")
        if not session_id:
            return False

        session = db.session.execute(
            select(UserSession)
            .where(UserSession.session_uuid == session_id)
            .limit(1)
        ).scalar_one_or_none()
        if session is None or session.revoked_at is not None:
            return True

        if jwt_payload.get("type") == "refresh":
            return session.refresh_token_jti != jwt_payload.get("jti")
        return False

    @jwt.revoked_token_loader
    def revoked_token_response(_jwt_header, _jwt_payload):
        return jsonify({"error": "Token has been revoked."}), 401

    @jwt.invalid_token_loader
    def invalid_token_response(message: str):
        return jsonify({"error": message}), 401

    @jwt.unauthorized_loader
    def unauthorized_token_response(message: str):
        return jsonify({"error": message}), 401


def register_security_headers(app: Flask) -> None:
    @app.after_request
    def apply_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'",
        )
        if app.config["ENV_NAME"] == "production":
            response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")
        response.headers.setdefault("X-Request-ID", getattr(g, "request_id", str(uuid.uuid4())))

        origin = request.headers.get("Origin")
        if origin and origin in app.config["CORS_ORIGINS"]:
            response.headers.setdefault("Access-Control-Allow-Origin", origin)
            response.headers.setdefault("Access-Control-Allow-Credentials", "true")
            response.headers.setdefault("Vary", "Origin")
        return response


def register_cli_commands(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db_command():
        with app.app_context():
            db.create_all()
        print("Database tables created.")

    @app.cli.command("backup-db")
    def backup_db_command():
        output = Path(app.config["BACKUP_DIRECTORY"]) / "workforceiq-backup.json"
        with app.app_context():
            result = export_database_backup(output)
        print(result)

    @app.cli.command("verify-backup")
    def verify_backup_command():
        backup_path = Path(app.config["BACKUP_DIRECTORY"]) / "workforceiq-backup.json"
        result = verify_database_backup(backup_path)
        print(result)


def _is_uninitialized_local_database_error(app: Flask, error: OperationalError) -> bool:
    if app.config["ENV_NAME"] == "production":
        return False
    database_uri = str(app.config.get("SQLALCHEMY_DATABASE_URI", "")).lower()
    if not database_uri.startswith("sqlite"):
        return False
    message = str(getattr(error, "orig", error)).lower()
    return "no such table" in message
