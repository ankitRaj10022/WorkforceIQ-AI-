from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote


def generate_mfa_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def provisioning_uri(*, issuer: str, account_name: str, secret: str) -> str:
    label = quote(f"{issuer}:{account_name}")
    issuer_param = quote(issuer)
    return f"otpauth://totp/{label}?secret={secret}&issuer={issuer_param}&algorithm=SHA1&digits=6&period=30"


def verify_totp(secret: str, code: str, *, at_time: int | None = None, window: int = 1) -> bool:
    normalized = str(code).strip()
    if not normalized.isdigit() or len(normalized) != 6:
        return False

    timestamp = int(time.time() if at_time is None else at_time)
    for offset in range(-window, window + 1):
        expected = _totp(secret, timestamp + (offset * 30))
        if hmac.compare_digest(expected, normalized):
            return True
    return False


def _totp(secret: str, timestamp: int) -> str:
    key = _decode_secret(secret)
    counter = int(timestamp // 30)
    message = struct.pack(">Q", counter)
    digest = hmac.new(key, message, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(code % 1_000_000).zfill(6)


def _decode_secret(secret: str) -> bytes:
    padding = "=" * ((8 - len(secret) % 8) % 8)
    return base64.b32decode((secret + padding).upper())
