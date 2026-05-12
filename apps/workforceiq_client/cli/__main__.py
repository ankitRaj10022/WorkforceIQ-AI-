from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from apps.workforceiq_client.core import (
    DesktopClientConfig,
    OfflineStore,
    WorkforceApiClient,
    WorkforceAuthenticator,
    WorkforceSyncEngine,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="WorkforceIQ desktop client CLI")
    parser.add_argument("--api-base-url")
    parser.add_argument("--organization-id")
    parser.add_argument("--data-dir")
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("health")
    subcommands.add_parser("ready")

    login_parser = subcommands.add_parser("login")
    login_parser.add_argument("--email", required=True)
    login_parser.add_argument("--password", required=True)
    login_parser.add_argument("--mfa-code")

    login_cognito_parser = subcommands.add_parser("login-cognito")
    login_cognito_parser.add_argument("--email", required=True)
    login_cognito_parser.add_argument("--password", required=True)

    signup_parser = subcommands.add_parser("signup-cognito")
    signup_parser.add_argument("--email", required=True)
    signup_parser.add_argument("--password", required=True)

    confirm_parser = subcommands.add_parser("confirm-cognito")
    confirm_parser.add_argument("--email", required=True)
    confirm_parser.add_argument("--code", required=True)

    subcommands.add_parser("whoami")
    subcommands.add_parser("logout")
    subcommands.add_parser("sync-flush")

    employee_get_parser = subcommands.add_parser("employee-get")
    employee_get_parser.add_argument("employee_id")
    employee_get_parser.add_argument("--prefer-offline", action="store_true")

    employee_update_parser = subcommands.add_parser("employee-update")
    employee_update_parser.add_argument("employee_id")
    employee_update_parser.add_argument("--set", dest="fields", action="append", required=True)
    employee_update_parser.add_argument("--offline", action="store_true")

    args = parser.parse_args()
    config = DesktopClientConfig.from_env().with_overrides(
        api_base_url=args.api_base_url,
        organization_id=args.organization_id,
        data_dir=Path(args.data_dir) if args.data_dir else None,
    )
    config.ensure_directories()
    store = OfflineStore(db_path=config.offline_db_path, token_key_path=config.token_key_path)
    api_client = WorkforceApiClient(
        base_url=config.api_base_url,
        request_timeout_seconds=config.request_timeout_seconds,
    )
    authenticator = WorkforceAuthenticator(config=config, store=store, api_client=api_client)
    sync_engine = WorkforceSyncEngine(authenticator=authenticator, store=store)

    try:
        result = dispatch_command(args, api_client, authenticator, sync_engine)
    except Exception as exc:  # pragma: no cover - CLI guard
        print(json.dumps({"error": str(exc)}, indent=2))
        return 1

    print(json.dumps(result, indent=2))
    return 0


def dispatch_command(
    args: argparse.Namespace,
    api_client: WorkforceApiClient,
    authenticator: WorkforceAuthenticator,
    sync_engine: WorkforceSyncEngine,
) -> dict[str, Any]:
    if args.command == "health":
        return api_client.health()
    if args.command == "ready":
        return api_client.ready()
    if args.command == "login":
        return authenticator.login_with_password(
            email=args.email,
            password=args.password,
            mfa_code=args.mfa_code,
        ).to_payload()
    if args.command == "login-cognito":
        return authenticator.login_with_cognito(email=args.email, password=args.password).to_payload()
    if args.command == "signup-cognito":
        return authenticator.sign_up_with_cognito(email=args.email, password=args.password)
    if args.command == "confirm-cognito":
        return authenticator.confirm_cognito_sign_up(email=args.email, confirmation_code=args.code)
    if args.command == "whoami":
        session = authenticator.current_session()
        if session is None:
            raise RuntimeError("No local WorkforceIQ session is available.")
        return session.to_payload()
    if args.command == "logout":
        authenticator.logout()
        return {"logged_out": True}
    if args.command == "sync-flush":
        return {"results": sync_engine.flush()}
    if args.command == "employee-get":
        return sync_engine.pull_employee(args.employee_id, prefer_cached=args.prefer_offline)
    if args.command == "employee-update":
        changes = _parse_changes(args.fields)
        if args.offline:
            mutation_id = sync_engine.queue_employee_update(args.employee_id, changes)
            return {"queued": True, "mutation_id": mutation_id}
        response = authenticator.build_authenticated_client().update_employee(args.employee_id, changes)
        sync_engine.store.cache_employee_profile(args.employee_id, response)
        return response
    raise RuntimeError(f"Unsupported command `{args.command}`.")


def _parse_changes(pairs: list[str]) -> dict[str, str]:
    changes: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise RuntimeError(f"Invalid field assignment `{pair}`. Use KEY=VALUE.")
        key, value = pair.split("=", 1)
        normalized_key = key.strip()
        if not normalized_key:
            raise RuntimeError("Field name cannot be empty.")
        changes[normalized_key] = value
    return changes


if __name__ == "__main__":
    sys.exit(main())
