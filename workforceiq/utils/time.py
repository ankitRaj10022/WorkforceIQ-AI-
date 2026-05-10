from __future__ import annotations

from datetime import UTC, date, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def to_utc_iso(value: datetime | date | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        value = ensure_utc_datetime(value)
        return value.isoformat().replace("+00:00", "Z")
    return value.isoformat()
