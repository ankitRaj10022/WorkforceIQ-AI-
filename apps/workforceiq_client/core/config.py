from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path


def _default_data_dir() -> Path:
    if os.name == "nt":
        base = os.getenv("LOCALAPPDATA")
        if base:
            return Path(base) / "WorkforceIQ"
        return Path.home() / "AppData" / "Local" / "WorkforceIQ"

    xdg_data_home = os.getenv("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / "WorkforceIQ"
    return Path.home() / ".local" / "share" / "WorkforceIQ"


@dataclass(frozen=True, slots=True)
class DesktopClientConfig:
    api_base_url: str = "http://127.0.0.1:5000"
    organization_id: str = "org-demo"
    data_dir: Path = _default_data_dir()
    request_timeout_seconds: int = 15
    cognito_region: str | None = None
    cognito_user_pool_id: str | None = None
    cognito_app_client_id: str | None = None
    cognito_app_client_secret: str | None = None

    @property
    def offline_db_path(self) -> Path:
        return self.data_dir / "offline.db"

    @property
    def token_key_path(self) -> Path:
        return self.data_dir / "session.key"

    @property
    def cognito_enabled(self) -> bool:
        return bool(self.cognito_region and self.cognito_user_pool_id and self.cognito_app_client_id)

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def with_overrides(
        self,
        *,
        api_base_url: str | None = None,
        organization_id: str | None = None,
        data_dir: Path | None = None,
    ) -> DesktopClientConfig:
        return replace(
            self,
            api_base_url=api_base_url or self.api_base_url,
            organization_id=organization_id or self.organization_id,
            data_dir=data_dir or self.data_dir,
        )

    @classmethod
    def from_env(cls) -> DesktopClientConfig:
        data_dir = os.getenv("WORKFORCEIQ_CLIENT_DATA_DIR")
        return cls(
            api_base_url=os.getenv("WORKFORCEIQ_CLIENT_API_BASE_URL", os.getenv("WORKFORCEIQ_API_BASE_URL", "http://127.0.0.1:5000")),
            organization_id=os.getenv("WORKFORCEIQ_CLIENT_ORGANIZATION_ID", "org-demo"),
            data_dir=Path(data_dir) if data_dir else _default_data_dir(),
            request_timeout_seconds=int(os.getenv("WORKFORCEIQ_CLIENT_TIMEOUT_SECONDS", "15")),
            cognito_region=_optional_env("WORKFORCEIQ_CLIENT_COGNITO_REGION"),
            cognito_user_pool_id=_optional_env("WORKFORCEIQ_CLIENT_COGNITO_USER_POOL_ID"),
            cognito_app_client_id=_optional_env("WORKFORCEIQ_CLIENT_COGNITO_APP_CLIENT_ID"),
            cognito_app_client_secret=_optional_env("WORKFORCEIQ_CLIENT_COGNITO_APP_CLIENT_SECRET"),
        )


def _optional_env(name: str) -> str | None:
    raw = os.getenv(name)
    if raw is None:
        return None
    normalized = raw.strip()
    return normalized or None
