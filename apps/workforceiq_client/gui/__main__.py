from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk

from apps.workforceiq_client.core import (
    ApiClientError,
    DesktopClientConfig,
    OfflineStore,
    WorkforceApiClient,
    WorkforceAuthenticator,
    WorkforceSyncEngine,
)


def build_action_error_payload(action_name: str, exc: Exception) -> dict[str, object]:
    payload: dict[str, object] = {
        "action": action_name,
        "error": str(exc),
    }
    if isinstance(exc, ApiClientError):
        payload["status_code"] = exc.status_code
        payload["details"] = exc.body
    else:
        payload["exception_type"] = type(exc).__name__
    return payload


class WorkforceDesktopApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("WorkforceIQ Desktop")
        self.root.geometry("900x640")

        self.config = DesktopClientConfig.from_env()
        self.config.ensure_directories()
        self.store = OfflineStore(db_path=self.config.offline_db_path, token_key_path=self.config.token_key_path)
        self.api_client = WorkforceApiClient(
            base_url=self.config.api_base_url,
            request_timeout_seconds=self.config.request_timeout_seconds,
        )
        self.authenticator = WorkforceAuthenticator(config=self.config, store=self.store, api_client=self.api_client)
        self.sync_engine = WorkforceSyncEngine(authenticator=self.authenticator, store=self.store)

        self.api_base_url = tk.StringVar(value=self.config.api_base_url)
        self.email = tk.StringVar()
        self.password = tk.StringVar()
        self.employee_id = tk.StringVar(value="EMP-0841")
        self.auth_mode = tk.StringVar(value="workforce")
        self.status_text = tk.StringVar(value="Not authenticated.")

        current_session = self.authenticator.current_session()
        if current_session is not None:
            cached_email = current_session.provider_username or str(current_session.user.get("email") or "")
            if cached_email:
                self.email.set(cached_email)
            self.status_text.set(
                f"Cached session for {current_session.user.get('email')} ({current_session.user.get('role')})."
            )

        self.output: tk.Text | None = None
        self._build_layout()

    def run(self) -> None:
        self.root.mainloop()

    def _build_layout(self) -> None:
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="API Base URL").grid(row=0, column=0, sticky="w")
        ttk.Entry(container, textvariable=self.api_base_url, width=56).grid(row=0, column=1, columnspan=3, sticky="ew", pady=(0, 8))

        ttk.Label(container, text="Email").grid(row=1, column=0, sticky="w")
        ttk.Entry(container, textvariable=self.email, width=40).grid(row=1, column=1, sticky="ew", padx=(0, 8))

        ttk.Label(container, text="Password").grid(row=1, column=2, sticky="w")
        ttk.Entry(container, textvariable=self.password, show="*", width=32).grid(row=1, column=3, sticky="ew")

        mode_frame = ttk.Frame(container)
        mode_frame.grid(row=2, column=0, columnspan=4, sticky="w", pady=(8, 8))
        ttk.Label(mode_frame, text="Login Mode").pack(side="left")
        ttk.Radiobutton(mode_frame, text="WorkforceIQ", variable=self.auth_mode, value="workforce").pack(side="left", padx=(8, 4))
        ttk.Radiobutton(mode_frame, text="Cognito", variable=self.auth_mode, value="cognito").pack(side="left")

        button_frame = ttk.Frame(container)
        button_frame.grid(row=3, column=0, columnspan=4, sticky="w", pady=(0, 8))
        ttk.Button(button_frame, text="Health", command=self.check_health).pack(side="left", padx=(0, 8))
        ttk.Button(button_frame, text="Ready", command=self.check_ready).pack(side="left", padx=(0, 8))
        ttk.Button(button_frame, text="Login", command=self.login).pack(side="left", padx=(0, 8))
        ttk.Button(button_frame, text="Refresh", command=self.refresh_session).pack(side="left", padx=(0, 8))
        ttk.Button(button_frame, text="Logout", command=self.logout).pack(side="left")

        employee_frame = ttk.Frame(container)
        employee_frame.grid(row=4, column=0, columnspan=4, sticky="w", pady=(0, 8))
        ttk.Label(employee_frame, text="Employee ID").pack(side="left")
        ttk.Entry(employee_frame, textvariable=self.employee_id, width=18).pack(side="left", padx=(8, 8))
        ttk.Button(employee_frame, text="Fetch Employee", command=self.fetch_employee).pack(side="left", padx=(0, 8))
        ttk.Button(employee_frame, text="Flush Sync Queue", command=self.flush_sync).pack(side="left")

        ttk.Label(container, textvariable=self.status_text).grid(row=5, column=0, columnspan=4, sticky="w", pady=(0, 8))
        self.output = tk.Text(container, wrap="word", height=24)
        self.output.grid(row=6, column=0, columnspan=4, sticky="nsew")

        for column in range(4):
            container.columnconfigure(column, weight=1)
        container.rowconfigure(6, weight=1)

    def check_health(self) -> None:
        self._refresh_api_url()
        payload = self._run_action("Health check", self.api_client.health)
        if payload is not None:
            self.status_text.set("API health check passed.")
            self._write_output(payload)

    def check_ready(self) -> None:
        self._refresh_api_url()
        payload = self._run_action("Readiness check", self.api_client.ready)
        if payload is not None:
            self.status_text.set("API readiness check passed.")
            self._write_output(payload)

    def login(self) -> None:
        self._refresh_api_url()
        if self.auth_mode.get() == "cognito":
            session = self._run_action(
                "Login",
                lambda: self.authenticator.login_with_cognito(
                    email=self.email.get(),
                    password=self.password.get(),
                ),
            )
        else:
            session = self._run_action(
                "Login",
                lambda: self.authenticator.login_with_password(
                    email=self.email.get(),
                    password=self.password.get(),
                ),
            )
        if session is None:
            return
        self.status_text.set(f"Logged in as {session.user.get('email')} ({session.user.get('role')})")
        self._write_output(session.to_payload())

    def refresh_session(self) -> None:
        session = self._run_action("Refresh session", self.authenticator.refresh_session)
        if session is None:
            return
        self.status_text.set(f"Session refreshed for {session.user.get('email')}")
        self._write_output(session.to_payload())

    def logout(self) -> None:
        result = self._run_action(
            "Logout",
            lambda: self._logout_payload(),
        )
        if result is None:
            return
        self.status_text.set("Logged out.")
        self._write_output(result)

    def fetch_employee(self) -> None:
        payload = self._run_action(
            "Fetch employee",
            lambda: self.sync_engine.pull_employee(self.employee_id.get()),
        )
        if payload is None:
            return
        self._write_output(payload)

    def flush_sync(self) -> None:
        results = self._run_action("Flush sync queue", self.sync_engine.flush)
        if results is None:
            return
        payload = {"results": results}
        self._write_output(payload)

    def _refresh_api_url(self) -> None:
        base_url = self.api_base_url.get().strip()
        self.config = self.config.with_overrides(api_base_url=base_url)
        self.api_client = WorkforceApiClient(
            base_url=self.config.api_base_url,
            request_timeout_seconds=self.config.request_timeout_seconds,
        )
        self.authenticator = WorkforceAuthenticator(config=self.config, store=self.store, api_client=self.api_client)
        self.sync_engine = WorkforceSyncEngine(authenticator=self.authenticator, store=self.store)

    def _write_output(self, payload: object) -> None:
        if self.output is None:
            return
        self.output.delete("1.0", tk.END)
        self.output.insert("1.0", json.dumps(payload, indent=2))

    def _logout_payload(self) -> dict[str, bool]:
        self.authenticator.logout()
        return {"logged_out": True}

    def _run_action(self, action_name: str, callback):
        try:
            return callback()
        except ApiClientError as exc:
            if exc.status_code == 401 and "revoked" in str(exc).lower():
                self.store.clear_session()
                self.status_text.set("Session expired or was revoked. Log in again.")
            else:
                self.status_text.set(f"{action_name} failed: {exc}")
            self._write_output(build_action_error_payload(action_name, exc))
            return None
        except Exception as exc:
            self.status_text.set(f"{action_name} failed: {exc}")
            self._write_output(build_action_error_payload(action_name, exc))
            return None


def main() -> None:
    WorkforceDesktopApp().run()


if __name__ == "__main__":
    main()
