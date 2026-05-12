from __future__ import annotations

import base64
import hashlib
import hmac
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from .api import ApiClientError, WorkforceApiClient
from .config import DesktopClientConfig
from .models import SessionSnapshot, WorkforceTokens
from .offline_store import OfflineStore


@dataclass(slots=True)
class CognitoAuthenticationResult:
    id_token: str
    access_token: str
    refresh_token: str | None
    expires_in: int | None = None
    token_type: str | None = None


class CognitoUserPoolClient:
    def __init__(self, config: DesktopClientConfig) -> None:
        self.config = config

    def sign_up(self, *, email: str, password: str) -> dict[str, Any]:
        response = self._client().sign_up(
            ClientId=self._required(self.config.cognito_app_client_id, "cognito_app_client_id"),
            Username=email,
            Password=password,
            UserAttributes=[{"Name": "email", "Value": email}],
            **self._secret_hash_argument(email),
        )
        return {
            "user_confirmed": bool(response.get("UserConfirmed")),
            "code_delivery": response.get("CodeDeliveryDetails", {}),
            "user_sub": response.get("UserSub"),
        }

    def confirm_sign_up(self, *, email: str, confirmation_code: str) -> dict[str, Any]:
        self._client().confirm_sign_up(
            ClientId=self._required(self.config.cognito_app_client_id, "cognito_app_client_id"),
            Username=email,
            ConfirmationCode=confirmation_code,
            **self._secret_hash_argument(email),
        )
        return {"confirmed": True}

    def authenticate(self, *, email: str, password: str) -> CognitoAuthenticationResult:
        response = self._client().initiate_auth(
            ClientId=self._required(self.config.cognito_app_client_id, "cognito_app_client_id"),
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": email,
                "PASSWORD": password,
                **self._secret_hash_parameters(email),
            },
        )
        return self._normalize_authentication_result(response["AuthenticationResult"])

    def refresh(self, *, refresh_token: str, username: str | None = None) -> CognitoAuthenticationResult:
        cognito_username = username or ""
        response = self._client().initiate_auth(
            ClientId=self._required(self.config.cognito_app_client_id, "cognito_app_client_id"),
            AuthFlow="REFRESH_TOKEN_AUTH",
            AuthParameters={
                "REFRESH_TOKEN": refresh_token,
                **self._secret_hash_parameters(cognito_username),
            },
        )
        return self._normalize_authentication_result(
            response["AuthenticationResult"],
            fallback_refresh_token=refresh_token,
        )

    def global_sign_out(self, *, access_token: str) -> None:
        self._client().global_sign_out(AccessToken=access_token)

    def _client(self):
        if not self.config.cognito_enabled:
            raise RuntimeError("Cognito desktop authentication is not configured.")
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - exercised only when boto3 is absent
            raise RuntimeError(
                "Desktop Cognito authentication requires `boto3`. Install requirements-client.txt."
            ) from exc

        return boto3.client("cognito-idp", region_name=self.config.cognito_region)

    def _normalize_authentication_result(
        self,
        payload: dict[str, Any],
        *,
        fallback_refresh_token: str | None = None,
    ) -> CognitoAuthenticationResult:
        return CognitoAuthenticationResult(
            id_token=str(payload["IdToken"]),
            access_token=str(payload["AccessToken"]),
            refresh_token=str(payload.get("RefreshToken") or fallback_refresh_token) if (payload.get("RefreshToken") or fallback_refresh_token) else None,
            expires_in=int(payload["ExpiresIn"]) if "ExpiresIn" in payload else None,
            token_type=str(payload["TokenType"]) if "TokenType" in payload else None,
        )

    def _secret_hash_argument(self, username: str) -> dict[str, str]:
        if not self.config.cognito_app_client_secret:
            return {}
        return {"SecretHash": self._secret_hash(username)}

    def _secret_hash_parameters(self, username: str) -> dict[str, str]:
        if not self.config.cognito_app_client_secret:
            return {}
        return {"SECRET_HASH": self._secret_hash(username)}

    def _secret_hash(self, username: str) -> str:
        app_client_secret = self._required(self.config.cognito_app_client_secret, "cognito_app_client_secret")
        app_client_id = self._required(self.config.cognito_app_client_id, "cognito_app_client_id")
        digest = hmac.new(
            app_client_secret.encode("utf-8"),
            f"{username}{app_client_id}".encode(),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(digest).decode("ascii")

    @staticmethod
    def _required(value: str | None, field_name: str) -> str:
        if value:
            return value
        raise RuntimeError(f"Desktop Cognito authentication requires `{field_name}`.")


class WorkforceAuthenticator:
    def __init__(
        self,
        *,
        config: DesktopClientConfig,
        store: OfflineStore,
        api_client: WorkforceApiClient | None = None,
        cognito_client: CognitoUserPoolClient | None = None,
    ) -> None:
        self.config = config
        self.store = store
        self.api_client = api_client or WorkforceApiClient(
            base_url=config.api_base_url,
            request_timeout_seconds=config.request_timeout_seconds,
        )
        self.cognito_client = cognito_client or CognitoUserPoolClient(config)

    def current_session(self) -> SessionSnapshot | None:
        return self.store.load_session()

    def login_with_password(
        self,
        *,
        email: str,
        password: str,
        mfa_code: str | None = None,
    ) -> SessionSnapshot:
        response = self.api_client.login(
            email=email,
            password=password,
            organization_id=self.config.organization_id,
            mfa_code=mfa_code,
        )
        return self._persist_session(response, provider="workforce_password", provider_username=email)

    def login_with_oidc_token(self, *, id_token: str, provider: str = "oidc") -> SessionSnapshot:
        response = self.api_client.exchange_oidc(id_token=id_token, organization_id=self.config.organization_id)
        return self._persist_session(response, provider=provider)

    def login_with_cognito(self, *, email: str, password: str) -> SessionSnapshot:
        cognito_result = self.cognito_client.authenticate(email=email, password=password)
        response = self.api_client.exchange_oidc(
            id_token=cognito_result.id_token,
            organization_id=self.config.organization_id,
        )
        return self._persist_session(
            response,
            provider="cognito",
            provider_refresh_token=cognito_result.refresh_token,
            provider_access_token=cognito_result.access_token,
            provider_username=email,
        )

    def sign_up_with_cognito(self, *, email: str, password: str) -> dict[str, Any]:
        return self.cognito_client.sign_up(email=email, password=password)

    def confirm_cognito_sign_up(self, *, email: str, confirmation_code: str) -> dict[str, Any]:
        return self.cognito_client.confirm_sign_up(email=email, confirmation_code=confirmation_code)

    def refresh_session(self) -> SessionSnapshot:
        session = self._require_session()
        try:
            response = self.api_client.refresh(refresh_token=session.tokens.refresh_token)
            return self._persist_session(
                response,
                provider=session.provider,
                provider_refresh_token=session.provider_refresh_token,
                provider_access_token=session.provider_access_token,
                provider_username=session.provider_username,
            )
        except ApiClientError:
            if session.provider == "cognito" and session.provider_refresh_token:
                cognito_result = self.cognito_client.refresh(
                    refresh_token=session.provider_refresh_token,
                    username=session.provider_username,
                )
                response = self.api_client.exchange_oidc(
                    id_token=cognito_result.id_token,
                    organization_id=self.config.organization_id,
                )
                return self._persist_session(
                    response,
                    provider="cognito",
                    provider_refresh_token=cognito_result.refresh_token,
                    provider_access_token=cognito_result.access_token,
                    provider_username=session.provider_username,
                )
            raise

    def build_authenticated_client(self) -> WorkforceApiClient:
        session = self._require_session()
        return self.api_client.clone_with_token(session.tokens.access_token)

    def logout(self) -> None:
        session = self.current_session()
        if session is None:
            return

        with suppress(ApiClientError):
            self.api_client.logout(access_token=session.tokens.access_token)

        if session.provider == "cognito" and session.provider_access_token:
            with suppress(Exception):  # pragma: no cover - best effort remote sign out
                self.cognito_client.global_sign_out(access_token=session.provider_access_token)

        self.store.clear_session()

    def _persist_session(
        self,
        response: dict[str, Any],
        *,
        provider: str,
        provider_refresh_token: str | None = None,
        provider_access_token: str | None = None,
        provider_username: str | None = None,
    ) -> SessionSnapshot:
        snapshot = SessionSnapshot(
            provider=provider,
            tokens=WorkforceTokens(
                access_token=str(response["access_token"]),
                refresh_token=str(response["refresh_token"]),
                token_type=str(response.get("token_type", "Bearer")),
            ),
            user=dict(response["user"]),
            server_session=dict(response["session"]),
            provider_refresh_token=provider_refresh_token,
            provider_access_token=provider_access_token,
            provider_username=provider_username,
        )
        self.store.save_session(snapshot)
        return snapshot

    def _require_session(self) -> SessionSnapshot:
        session = self.current_session()
        if session is None:
            raise RuntimeError("No local WorkforceIQ session is available. Log in first.")
        return session
