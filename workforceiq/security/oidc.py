from __future__ import annotations

import json
from functools import lru_cache
from urllib.request import urlopen

import jwt
from flask import current_app
from jwt import InvalidTokenError
from jwt.algorithms import get_default_algorithms

from workforceiq.errors import AccessDeniedError, ValidationError


def verify_oidc_token(id_token: object) -> dict:
    token = str(id_token or "").strip()
    if not token:
        raise ValidationError("`id_token` is required.")
    if not current_app.config["OIDC_ENABLED"]:
        raise ValidationError("OIDC SSO is disabled in this environment.")

    try:
        header = jwt.get_unverified_header(token)
    except InvalidTokenError as exc:
        raise AccessDeniedError("Access denied. OIDC token header is invalid.") from exc

    algorithm = str(header.get("alg") or "")
    if not algorithm or algorithm.lower() == "none":
        raise AccessDeniedError("Access denied. OIDC token algorithm is invalid.")

    jwk = _select_signing_key(_load_jwks(), header)
    key = _public_key_from_jwk(jwk, algorithm)
    try:
        claims = jwt.decode(
            token,
            key=key,
            algorithms=[algorithm],
            audience=current_app.config["OIDC_AUDIENCE"],
            issuer=current_app.config["OIDC_ISSUER"],
            leeway=current_app.config["OIDC_CLOCK_SKEW_SECONDS"],
            options={"require": ["exp", "iat", "iss", "sub"]},
        )
    except InvalidTokenError as exc:
        raise AccessDeniedError("Access denied. OIDC token validation failed.") from exc

    email = str(claims.get("email") or "").strip().lower()
    if not email:
        raise AccessDeniedError("Access denied. OIDC token is missing the required email claim.")
    if current_app.config["OIDC_REQUIRE_VERIFIED_EMAIL"] and not _is_verified_email(claims.get("email_verified")):
        raise AccessDeniedError("Access denied. OIDC email must be verified before sign-in.")

    claims["email"] = email
    return claims


def _load_jwks() -> dict:
    inline_document = current_app.config["OIDC_JWKS_JSON"]
    if inline_document:
        return _parse_jwks_document(inline_document)
    return _fetch_jwks_document(current_app.config["OIDC_JWKS_URI"])


@lru_cache(maxsize=8)
def _fetch_jwks_document(jwks_uri: str) -> dict:
    if not jwks_uri:
        raise ValidationError("OIDC_JWKS_URI is not configured.")

    with urlopen(jwks_uri, timeout=5) as response:  # nosec B310
        return _parse_jwks_document(response.read().decode("utf-8"))


def _parse_jwks_document(document: str) -> dict:
    try:
        payload = json.loads(document)
    except json.JSONDecodeError as exc:
        raise ValidationError("OIDC JWKS configuration is invalid JSON.") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("keys"), list):
        raise ValidationError("OIDC JWKS configuration must be a JSON object with a `keys` array.")
    return payload


def _select_signing_key(jwks: dict, header: dict) -> dict:
    kid = header.get("kid")
    keys = [key for key in jwks["keys"] if isinstance(key, dict)]
    if kid:
        for key in keys:
            if key.get("kid") == kid:
                return key
        raise AccessDeniedError("Access denied. No matching OIDC signing key was found.")
    if len(keys) == 1:
        return keys[0]
    raise AccessDeniedError("Access denied. OIDC token is missing a key identifier.")


def _public_key_from_jwk(jwk: dict, algorithm: str):
    algorithm_impl = get_default_algorithms().get(algorithm)
    if algorithm_impl is None or not hasattr(algorithm_impl, "from_jwk"):
        raise ValidationError(f"OIDC algorithm `{algorithm}` is not supported by this deployment.")
    return algorithm_impl.from_jwk(json.dumps(jwk))


def _is_verified_email(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return False
