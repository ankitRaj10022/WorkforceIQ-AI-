from __future__ import annotations

import base64
import binascii
import json
import time
from dataclasses import dataclass

from flask import Flask


@dataclass(slots=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    backend: str


class RateLimiter:
    def __init__(self, app: Flask):
        self.app = app
        self.memory_buckets: dict[tuple[str, int], int] = {}
        self.redis_client = self._build_redis_client(app)

    def hit(self, key: str, *, limit: int, window_seconds: int = 60) -> RateLimitResult:
        if self.redis_client is not None:
            try:
                return self._redis_hit(key, limit=limit, window_seconds=window_seconds)
            except Exception:  # pragma: no cover - network-dependent guardrail
                self.app.logger.error("rate_limit.redis_unavailable", exc_info=True)
                if self.app.config["ENV_NAME"] == "production" and self.app.config["RATE_LIMIT_BACKEND"] == "redis":
                    return RateLimitResult(allowed=False, remaining=0, backend="redis_unavailable")
        return self._memory_hit(key, limit=limit)

    def _redis_hit(self, key: str, *, limit: int, window_seconds: int) -> RateLimitResult:
        bucket_key = f"workforceiq:rate:{int(time.time() // window_seconds)}:{key}"
        count = int(self.redis_client.incr(bucket_key))
        if count == 1:
            self.redis_client.expire(bucket_key, window_seconds + 5)
        return RateLimitResult(allowed=count <= limit, remaining=max(limit - count, 0), backend="redis")

    def _memory_hit(self, key: str, *, limit: int) -> RateLimitResult:
        window = int(time.time() // 60)
        bucket_key = (key, window)
        self.memory_buckets[bucket_key] = self.memory_buckets.get(bucket_key, 0) + 1
        for existing_key in list(self.memory_buckets):
            if existing_key[1] < window - 1:
                self.memory_buckets.pop(existing_key, None)
        count = self.memory_buckets[bucket_key]
        return RateLimitResult(allowed=count <= limit, remaining=max(limit - count, 0), backend="memory")

    @staticmethod
    def _build_redis_client(app: Flask):
        if app.config["RATE_LIMIT_BACKEND"] == "memory":
            return None
        try:
            from redis import Redis

            return Redis.from_url(app.config["REDIS_URL"], decode_responses=True)
        except Exception:  # pragma: no cover - dependency/config fallback
            return None


def rate_limit_key_from_request(*, authorization_header: str | None, remote_addr: str | None, organization_hint: str) -> tuple[str, dict]:
    claims = _unverified_jwt_claims(authorization_header)
    organization_id = str(claims.get("organization_id") or organization_hint)
    user_id = str(claims.get("user_id") or claims.get("sub") or remote_addr or "anonymous")
    return f"{organization_id}:{user_id}", {"organization_id": organization_id, "user_id": user_id}


def _unverified_jwt_claims(authorization_header: str | None) -> dict:
    if not authorization_header or not authorization_header.startswith("Bearer "):
        return {}
    token = authorization_header.removeprefix("Bearer ").strip()
    parts = token.split(".")
    if len(parts) != 3:
        return {}
    try:
        payload = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
        decoded = base64.urlsafe_b64decode(payload.encode("ascii"))
        data = json.loads(decoded)
        return data if isinstance(data, dict) else {}
    except (ValueError, json.JSONDecodeError, binascii.Error):
        return {}
