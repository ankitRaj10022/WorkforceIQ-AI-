from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Run WorkforceIQ API smoke checks.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--dev-user", default="hr-manager-1")
    parser.add_argument("--require-auth", action="store_true")
    args = parser.parse_args()

    checks: list[str] = []
    status, health = request_json(f"{args.base_url}/api/health")
    checks.append(f"health={status}")
    if status != 200 or health.get("status") != "ok":
        print("\n".join(checks))
        return 1

    if args.require_auth:
        status, token_response = request_json(
            f"{args.base_url}/api/auth/token",
            method="POST",
            payload={"user_id": args.dev_user},
        )
        checks.append(f"token={status}")
        if status != 200:
            print("\n".join(checks))
            print(json.dumps(token_response, indent=2))
            return 1

        token = token_response["access_token"]
        status, profile = request_json(f"{args.base_url}/api/employees/EMP-0841", token=token)
        checks.append(f"employee_profile={status}")
        if status != 200 or profile.get("employee_profile", {}).get("id") != "EMP-0841":
            print("\n".join(checks))
            print(json.dumps(profile, indent=2))
            return 1

    print("\n".join(checks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
