from __future__ import annotations

from pathlib import Path

from apps.workforceiq_client.core import (
    ApiClientError,
    DesktopClientConfig,
    OfflineStore,
    SessionSnapshot,
    WorkforceAuthenticator,
    WorkforceSyncEngine,
    WorkforceTokens,
)
from apps.workforceiq_client.gui.__main__ import build_action_error_payload


class FakeApiClient:
    def __init__(self) -> None:
        self.access_token = None
        self.refresh_attempts = 0
        self.logout_calls = 0

    def clone_with_token(self, access_token: str | None):
        cloned = FakeApiClient()
        cloned.access_token = access_token
        cloned.refresh_attempts = self.refresh_attempts
        cloned.logout_calls = self.logout_calls
        return cloned

    def login(self, *, email: str, password: str, organization_id: str, mfa_code: str | None = None):
        return _session_response(email=email, role="HR_MANAGER", access_token="access-1", refresh_token="refresh-1")

    def exchange_oidc(self, *, id_token: str, organization_id: str):
        return _session_response(email="hr@example.com", role="HR_MANAGER", access_token="access-oidc", refresh_token="refresh-oidc")

    def refresh(self, *, refresh_token: str):
        self.refresh_attempts += 1
        raise ApiClientError(status_code=401, body={"error": "Refresh expired"})

    def logout(self, *, access_token: str | None = None):
        self.logout_calls += 1
        return {"logged_out": True}

    def request_json(self, method: str, path: str, *, payload=None, query=None, access_token=None):
        if method == "PATCH" and path == "/api/employees/EMP-0841":
            return {
                "employee_profile": {"id": "EMP-0841", "email": payload["email"]},
                "audit_log_written": True,
            }
        raise ApiClientError(status_code=404, body={"error": "Not found"})

    def get_employee(self, employee_id: str):
        return {"employee_profile": {"id": employee_id, "email": "priya@example.com"}}

    def update_employee(self, employee_id: str, changes: dict[str, str]):
        return {
            "employee_profile": {"id": employee_id, **changes},
            "audit_log_written": True,
        }


class FakeCognitoClient:
    def refresh(self, *, refresh_token: str, username: str | None = None):
        return type(
            "Result",
            (),
            {
                "id_token": "new-id-token",
                "access_token": "new-cognito-access",
                "refresh_token": refresh_token,
            },
        )()

    def global_sign_out(self, *, access_token: str) -> None:
        return None


def test_offline_store_round_trips_session_cache_and_queue(tmp_path: Path):
    store = OfflineStore(db_path=tmp_path / "offline.db", token_key_path=tmp_path / "session.key")
    session = SessionSnapshot(
        provider="workforce_password",
        tokens=WorkforceTokens(access_token="access", refresh_token="refresh"),
        user={"email": "hr@example.com", "role": "HR_MANAGER"},
        server_session={"session_id": "session-1"},
    )

    store.save_session(session)
    store.cache_employee_profile("EMP-0841", {"employee_profile": {"id": "EMP-0841"}})
    mutation_id = store.enqueue_mutation(
        mutation_type="employee_update",
        method="PATCH",
        resource_path="/api/employees/EMP-0841",
        body={"email": "priya@example.com"},
    )

    loaded = store.load_session()
    cached = store.load_cached_employee_profile("EMP-0841")
    pending = store.list_pending_mutations()

    assert loaded is not None
    assert loaded.tokens.access_token == "access"
    assert cached is not None
    assert cached.payload["employee_profile"]["id"] == "EMP-0841"
    assert pending[0].mutation_id == mutation_id

    store.mark_mutation_failed(mutation_id, error_message="temporary outage")
    failed = store.list_pending_mutations()[0]
    assert failed.attempts == 1
    assert failed.last_error == "temporary outage"

    store.mark_mutation_synced(mutation_id)
    assert store.list_pending_mutations() == []


def test_authenticator_password_login_persists_local_session(tmp_path: Path):
    config = DesktopClientConfig(data_dir=tmp_path)
    store = OfflineStore(db_path=config.offline_db_path, token_key_path=config.token_key_path)
    authenticator = WorkforceAuthenticator(config=config, store=store, api_client=FakeApiClient(), cognito_client=FakeCognitoClient())

    session = authenticator.login_with_password(email="hr@example.com", password="secret")

    assert session.user["email"] == "hr@example.com"
    assert store.load_session() is not None


def test_authenticator_falls_back_to_cognito_refresh(tmp_path: Path):
    config = DesktopClientConfig(data_dir=tmp_path)
    store = OfflineStore(db_path=config.offline_db_path, token_key_path=config.token_key_path)
    api_client = FakeApiClient()
    authenticator = WorkforceAuthenticator(config=config, store=store, api_client=api_client, cognito_client=FakeCognitoClient())
    store.save_session(
        SessionSnapshot(
            provider="cognito",
            tokens=WorkforceTokens(access_token="old-access", refresh_token="old-refresh"),
            user={"email": "hr@example.com", "role": "HR_MANAGER"},
            server_session={"session_id": "session-1"},
            provider_refresh_token="cognito-refresh",
            provider_access_token="cognito-access",
            provider_username="hr@example.com",
        )
    )

    refreshed = authenticator.refresh_session()

    assert refreshed.provider == "cognito"
    assert refreshed.tokens.access_token == "access-oidc"


def test_sync_engine_flushes_employee_update_and_caches_response(tmp_path: Path):
    config = DesktopClientConfig(data_dir=tmp_path)
    store = OfflineStore(db_path=config.offline_db_path, token_key_path=config.token_key_path)
    api_client = FakeApiClient()
    authenticator = WorkforceAuthenticator(config=config, store=store, api_client=api_client, cognito_client=FakeCognitoClient())
    store.save_session(
        SessionSnapshot(
            provider="workforce_password",
            tokens=WorkforceTokens(access_token="cached-access", refresh_token="cached-refresh"),
            user={"email": "hr@example.com", "role": "HR_MANAGER"},
            server_session={"session_id": "session-1"},
        )
    )
    sync_engine = WorkforceSyncEngine(authenticator=authenticator, store=store)

    mutation_id = sync_engine.queue_employee_update("EMP-0841", {"email": "desktop@example.com"})
    results = sync_engine.flush()
    cached = store.load_cached_employee_profile("EMP-0841")

    assert results == [{"mutation_id": mutation_id, "status": "synced"}]
    assert cached is not None
    assert cached.payload["employee_profile"]["email"] == "desktop@example.com"


def test_build_action_error_payload_formats_api_client_error():
    exc = ApiClientError(status_code=403, body={"error": "Access denied."})

    payload = build_action_error_payload("Login", exc)

    assert payload == {
        "action": "Login",
        "error": "Access denied.",
        "status_code": 403,
        "details": {"error": "Access denied."},
    }


def test_build_action_error_payload_formats_runtime_error():
    payload = build_action_error_payload("Refresh session", RuntimeError("No local WorkforceIQ session is available."))

    assert payload == {
        "action": "Refresh session",
        "error": "No local WorkforceIQ session is available.",
        "exception_type": "RuntimeError",
    }


def _session_response(*, email: str, role: str, access_token: str, refresh_token: str) -> dict:
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "user": {
            "email": email,
            "role": role,
            "organization_id": "org-demo",
            "user_id": "1",
        },
        "session": {"session_id": "session-1"},
    }
