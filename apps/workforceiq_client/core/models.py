from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class WorkforceTokens:
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"

    def to_payload(self) -> dict[str, str]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> WorkforceTokens:
        return cls(
            access_token=str(payload["access_token"]),
            refresh_token=str(payload["refresh_token"]),
            token_type=str(payload.get("token_type", "Bearer")),
        )


@dataclass(frozen=True, slots=True)
class SessionSnapshot:
    provider: str
    tokens: WorkforceTokens
    user: dict[str, Any]
    server_session: dict[str, Any]
    provider_refresh_token: str | None = None
    provider_access_token: str | None = None
    provider_username: str | None = None
    updated_at: str = field(default_factory=utc_now_iso)

    def to_payload(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "tokens": self.tokens.to_payload(),
            "user": self.user,
            "server_session": self.server_session,
            "provider_refresh_token": self.provider_refresh_token,
            "provider_access_token": self.provider_access_token,
            "provider_username": self.provider_username,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> SessionSnapshot:
        return cls(
            provider=str(payload["provider"]),
            tokens=WorkforceTokens.from_payload(payload["tokens"]),
            user=dict(payload["user"]),
            server_session=dict(payload["server_session"]),
            provider_refresh_token=_optional_str(payload.get("provider_refresh_token")),
            provider_access_token=_optional_str(payload.get("provider_access_token")),
            provider_username=_optional_str(payload.get("provider_username")),
            updated_at=str(payload.get("updated_at") or utc_now_iso()),
        )


@dataclass(frozen=True, slots=True)
class QueuedMutation:
    mutation_id: int
    mutation_type: str
    method: str
    resource_path: str
    body: dict[str, Any]
    status: str
    attempts: int
    created_at: str
    updated_at: str
    last_error: str | None = None


@dataclass(frozen=True, slots=True)
class CachedDocument:
    namespace: str
    resource_id: str
    payload: dict[str, Any]
    updated_at: str


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
