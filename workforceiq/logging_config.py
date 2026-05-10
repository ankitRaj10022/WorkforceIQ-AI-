from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any

from flask import Flask, g, request


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key in ("request_id", "method", "path", "status_code", "duration_ms", "organization_id", "user_id"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, separators=(",", ":"), default=str)


def configure_logging(app: Flask) -> None:
    level = getattr(logging, app.config["LOG_LEVEL"].upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(JsonFormatter() if app.config["STRUCTURED_LOGS"] else logging.Formatter("%(levelname)s %(message)s"))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    app.logger.setLevel(level)


def register_request_logging(app: Flask) -> None:
    @app.before_request
    def start_request_timer():
        g.request_started_at = time.perf_counter()

    @app.after_request
    def log_request(response):
        duration_ms = round((time.perf_counter() - getattr(g, "request_started_at", time.perf_counter())) * 1000, 2)
        claims = getattr(g, "rate_limit_claims", {})
        app.logger.info(
            "request.completed",
            extra={
                "request_id": getattr(g, "request_id", None),
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "organization_id": claims.get("organization_id"),
                "user_id": claims.get("user_id"),
            },
        )
        return response
