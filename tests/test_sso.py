from __future__ import annotations

import json
from datetime import timedelta

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm
from werkzeug.security import generate_password_hash

from workforceiq.extensions import db
from workforceiq.models import UserAccount, UserSession
from workforceiq.utils.time import utc_now


def test_oidc_exchange_issues_local_session_tokens(client, app):
    private_key = _configure_oidc(app)
    token = _build_oidc_token(
        private_key,
        email="hr@example.com",
        subject="oidc-user-123",
        issuer=app.config["OIDC_ISSUER"],
        audience=app.config["OIDC_AUDIENCE"],
    )

    response = client.post("/api/auth/sso/exchange", json={"id_token": token})

    assert response.status_code == 200
    body = response.get_json()
    assert body["token_type"] == "Bearer"
    assert body["user"]["email"] == "hr@example.com"
    assert body["user"]["auth_provider"] == "hybrid"
    assert body["session"]["session_id"]

    with app.app_context():
        account = db.session.query(UserAccount).filter_by(email="hr@example.com").one()
        session = db.session.query(UserSession).filter_by(user_id=str(account.id)).one()
        assert account.auth_provider == "hybrid"
        assert account.external_subject == "oidc-user-123"
        assert session.refresh_token_jti is not None


def test_oidc_exchange_rejects_unverified_email_when_required(client, app):
    private_key = _configure_oidc(app)
    token = _build_oidc_token(
        private_key,
        email="hr@example.com",
        subject="oidc-user-456",
        issuer=app.config["OIDC_ISSUER"],
        audience=app.config["OIDC_AUDIENCE"],
        email_verified=False,
    )

    response = client.post("/api/auth/sso/exchange", json={"id_token": token})

    assert response.status_code == 403
    assert "email must be verified" in response.get_json()["error"]


def test_password_login_rejects_oidc_only_account(client, app):
    with app.app_context():
        db.session.add(
            UserAccount(
                id=2,
                organization_id="org-demo",
                email="sso-only@example.com",
                password_hash=generate_password_hash("CorrectHorseBatteryStaple!23"),
                auth_provider="oidc",
                external_subject="oidc-only-subject",
                role="HR_MANAGER",
                department_id=2,
                employee_id="EMP-1001",
            )
        )
        db.session.commit()

    response = client.post(
        "/api/auth/login",
        json={
            "email": "sso-only@example.com",
            "password": "CorrectHorseBatteryStaple!23",
            "organization_id": "org-demo",
        },
    )

    assert response.status_code == 403
    assert "enterprise SSO" in response.get_json()["error"]


def test_oidc_exchange_requires_feature_flag(client):
    response = client.post("/api/auth/sso/exchange", json={"id_token": "placeholder"})

    assert response.status_code == 400
    assert "disabled" in response.get_json()["error"]


def _configure_oidc(app):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    jwk = json.loads(RSAAlgorithm.to_jwk(public_key))
    jwk["kid"] = "test-key-1"
    app.config.update(
        OIDC_ENABLED=True,
        OIDC_ISSUER="https://example.okta.test/oauth2/default",
        OIDC_AUDIENCE="workforceiq-api",
        OIDC_JWKS_JSON=json.dumps({"keys": [jwk]}),
        OIDC_REQUIRE_VERIFIED_EMAIL=True,
    )
    return private_key


def _build_oidc_token(
    private_key,
    *,
    email: str,
    subject: str,
    issuer: str,
    audience: str,
    email_verified: bool = True,
) -> str:
    now = utc_now()
    claims = {
        "iss": issuer,
        "sub": subject,
        "aud": audience,
        "email": email,
        "email_verified": email_verified,
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test-key-1"})
