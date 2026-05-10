from __future__ import annotations


class ApiError(Exception):
    status_code = 400

    def __init__(self, message: str, status_code: int | None = None, payload: dict | None = None):
        super().__init__(message)
        self.message = message
        self.payload = payload or {}
        if status_code is not None:
            self.status_code = status_code


class AccessDeniedError(ApiError):
    status_code = 403


class NotFoundError(ApiError):
    status_code = 404


class ValidationError(ApiError):
    status_code = 400
