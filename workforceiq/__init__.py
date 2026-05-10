from __future__ import annotations

import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, g, jsonify, request
from flask_jwt_extended.exceptions import JWTExtendedException
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from workforceiq.api.routes import api_bp
from workforceiq.config import apply_runtime_settings, config_by_name, resolve_config_name, validate_runtime_config
from workforceiq.errors import ApiError
from workforceiq.extensions import db, jwt, migrate
from workforceiq.logging_config import configure_logging, register_request_logging
from workforceiq.maintenance import export_database_backup
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
