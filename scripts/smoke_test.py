from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse


def request_json(url: str, *, method: str = "GET", payload: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return 400, {"error": f"Unsupported URL scheme `{parsed.scheme}`."}

    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        # urlopen is safe here because request_json rejects non-http(s) schemes.
        with urllib.request.urlopen(request, timeout=10) as response:  # nosec B310
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            error_body = json.loads(exc.read().decode("utf-8"))
        except json.JSONDecodeError:
            error_body = {"error": str(exc)}
        return exc.code, error_body


@dataclass(frozen=True)
class AuthResult:
    mode: str
    status: int
    body: dict


def acquire_access_token(
    base_url: str,
    *,
    dev_user: str | None,
    organization_id: str,
    login_email: str | None,
    login_password: str | None,
    mfa_code: str | None,
) -> AuthResult:
    if login_email or login_password or mfa_code:
        if not login_email or not login_password:
            return AuthResult(
                mode="login",
                status=400,
                body={"error": "Both --login-email and --login-password are required for login-based smoke tests."},
            )

        payload = {
            "organization_id": organization_id,
            "email": login_email,
            "password": login_password,
        }
        if mfa_code:
            payload["mfa_code"] = mfa_code
        status, body = request_json(f"{base_url}/api/auth/login", method="POST", payload=payload)
        return AuthResult(mode="login", status=status, body=body)

    if not dev_user:
        return AuthResult(
            mode="auth",
            status=400,
            body={"error": "Provide --dev-user or real login credentials when --require-auth is enabled."},
        )

    status, body = request_json(
        f"{base_url}/api/auth/token",
        method="POST",
        payload={"user_id": dev_user},
    )
    return AuthResult(mode="dev_token", status=status, body=body)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run WorkforceIQ API smoke checks.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--dev-user", default="hr-manager-1")
    parser.add_argument("--organization-id", default="org-demo")
    parser.add_argument("--login-email")
    parser.add_argument("--login-password")
    parser.add_argument("--mfa-code")
    parser.add_argument("--employee-id", default="EMP-0841")
    parser.add_argument("--require-auth", action="store_true")
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args()

    checks: list[str] = []
    status, health = request_json(f"{args.base_url}/api/health")
    checks.append(f"health={status}")
    if status != 200 or health.get("status") != "ok":
        print("\n".join(checks))
        return 1

    if args.require_ready:
        status, readiness = request_json(f"{args.base_url}/api/health/ready")
        checks.append(f"ready={status}")
        if status != 200 or readiness.get("status") != "ready":
            print("\n".join(checks))
            print(json.dumps(readiness, indent=2))
            return 1

    if args.require_auth:
        auth_result = acquire_access_token(
            args.base_url,
            dev_user=args.dev_user,
            organization_id=args.organization_id,
            login_email=args.login_email,
            login_password=args.login_password,
            mfa_code=args.mfa_code,
        )
        checks.append(f"{auth_result.mode}={auth_result.status}")
        if auth_result.status != 200:
            print("\n".join(checks))
            print(json.dumps(auth_result.body, indent=2))
            return 1

        token = auth_result.body["access_token"]
        status, profile = request_json(f"{args.base_url}/api/employees/{args.employee_id}", token=token)
        checks.append(f"employee_profile={status}")
        if status != 200 or profile.get("employee_profile", {}).get("id") != args.employee_id:
            print("\n".join(checks))
            print(json.dumps(profile, indent=2))
            return 1

    print("\n".join(checks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
