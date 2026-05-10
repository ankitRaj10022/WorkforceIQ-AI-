from __future__ import annotations

from datetime import timedelta

from flask import current_app, request
from flask_jwt_extended import create_access_token
from sqlalchemy import select
from werkzeug.security import check_password_hash

from workforceiq.audit import record_audit_log
from workforceiq.auth import RequestContext, RoleName, parse_role
from workforceiq.errors import AccessDeniedError, NotFoundError, ValidationError
from workforceiq.extensions import db
from workforceiq.models import RbacRole, UserAccount, UserSession
from workforceiq.security.mfa import generate_mfa_secret, provisioning_uri, verify_totp
from workforceiq.utils.time import ensure_utc_datetime, to_utc_iso, utc_now

TOKEN_TYPE_BEARER = "Bearer"  # nosec B105


def login_user(payload: dict) -> dict:
    email = _normalize_email(payload.get("email"))
    password = payload.get("password")
    organization_id = str(payload.get("organization_id") or current_app.config["DEFAULT_ORGANIZATION_ID"])
    if not isinstance(password, str) or not password:
        raise ValidationError("`password` is required.")

    account = db.session.execute(
        select(UserAccount)
        .where(
            UserAccount.email == email,
            UserAccount.organization_id == organization_id,
        )
        .limit(1)
    ).scalar_one_or_none()
    if account is None:
        raise AccessDeniedError("Access denied. Invalid email or password.")
    if not account.is_active:
        raise AccessDeniedError("Access denied. This account is inactive.")

    _reject_if_locked(account)
    if not check_password_hash(account.password_hash, password):
        _register_failed_login(account)
        raise AccessDeniedError("Access denied. Invalid email or password.")

    if account.mfa_enabled and not verify_totp(account.mfa_secret or "", str(payload.get("mfa_code") or "")):
        _register_failed_login(account)
        raise AccessDeniedError("Access denied. A valid MFA code is required.")

    account.failed_login_count = 0
    account.locked_until = None
    role = parse_role(account.role)
    session = UserSession(
        organization_id=organization_id,
        user_id=str(account.id),
        role_id=_role_id_for(role),
        ip_address=request.remote_addr,
    )
    db.session.add(session)
    record_audit_log(
        user_id=str(account.id),
        organization_id=organization_id,
        action="LOGIN",
        target_entity="user_accounts",
        target_id=str(account.id),
        fields_changed=[],
        old_values={},
        new_values={},
        extra_metadata={"auth_method": "password_mfa" if account.mfa_enabled else "password"},
    )
    db.session.commit()

    token = _create_token_for_account(account, role)
    return {
        "access_token": token,
        "token_type": TOKEN_TYPE_BEARER,
        "requires_mfa": account.mfa_enabled,
        "user": _serialize_account(account, role),
    }


def setup_mfa(context: RequestContext) -> dict:
    account = _account_for_context(context)
    secret = generate_mfa_secret()
    account.mfa_secret = secret
    account.mfa_enabled = False
    db.session.commit()
    return {
        "mfa_secret": secret,
        "provisioning_uri": provisioning_uri(
            issuer=current_app.config["COMPANY_NAME"],
            account_name=account.email,
            secret=secret,
        ),
        "message": "Scan the provisioning URI, then verify with /api/auth/mfa/verify.",
    }


def verify_mfa_setup(context: RequestContext, payload: dict) -> dict:
    account = _account_for_context(context)
    if not account.mfa_secret:
        raise ValidationError("MFA setup has not been started for this account.")
    if not verify_totp(account.mfa_secret, str(payload.get("code") or "")):
        raise AccessDeniedError("Access denied. MFA code is invalid.")

    account.mfa_enabled = True
    record_audit_log(
        user_id=context.user_id,
        organization_id=context.organization_id,
        action="UPDATE",
        target_entity="user_accounts",
        target_id=str(account.id),
        fields_changed=["mfa_enabled"],
        old_values={"mfa_enabled": False},
        new_values={"mfa_enabled": True},
    )
    db.session.commit()
    return {"message": "MFA enabled successfully.", "mfa_enabled": True}


def _create_token_for_account(account: UserAccount, role: RoleName) -> str:
    return create_access_token(
        identity=str(account.id),
        additional_claims={
            "user_id": str(account.id),
            "organization_id": account.organization_id,
            "role": role.value,
            "department_id": account.department_id,
            "employee_id": account.employee_id,
        },
    )


def _reject_if_locked(account: UserAccount) -> None:
    if account.locked_until and ensure_utc_datetime(account.locked_until) > utc_now():
        raise AccessDeniedError(
            f"Access denied. Account is locked until {to_utc_iso(account.locked_until)}."
        )


def _register_failed_login(account: UserAccount) -> None:
    account.failed_login_count += 1
    if account.failed_login_count >= current_app.config["AUTH_LOCKOUT_THRESHOLD"]:
        account.locked_until = utc_now() + timedelta(minutes=current_app.config["AUTH_LOCKOUT_MINUTES"])
    db.session.commit()


def _account_for_context(context: RequestContext) -> UserAccount:
    try:
        account_id = int(context.user_id)
    except ValueError as exc:
        raise NotFoundError(
            "MFA setup requires a persisted user account. Development bypass tokens are not eligible."
        ) from exc

    account = db.session.execute(
        select(UserAccount)
        .where(
            UserAccount.id == account_id,
            UserAccount.organization_id == context.organization_id,
        )
        .limit(1)
    ).scalar_one_or_none()
    if account is None:
        raise NotFoundError("MFA setup requires a persisted user account. Development bypass tokens are not eligible.")
    return account


def _serialize_account(account: UserAccount, role: RoleName) -> dict:
    return {
        "user_id": str(account.id),
        "organization_id": account.organization_id,
        "email": account.email,
        "role": role.value,
        "department_id": account.department_id,
        "employee_id": account.employee_id,
        "mfa_enabled": account.mfa_enabled,
    }


def _normalize_email(value: object) -> str:
    if not isinstance(value, str) or "@" not in value:
        raise ValidationError("`email` is required and must be valid.")
    return value.strip().lower()


def _role_id_for(role: RoleName) -> int:
    role_id = db.session.execute(
        select(RbacRole.id)
        .where(RbacRole.name == role.value)
        .limit(1)
    ).scalar_one_or_none()
    if role_id is None:
        raise ValidationError(f"RBAC role `{role.value}` is not configured.")
    return role_id
