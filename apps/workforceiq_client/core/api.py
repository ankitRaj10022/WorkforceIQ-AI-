from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import error, parse, request


@dataclass(slots=True)
class ApiClientError(RuntimeError):
    status_code: int
    body: dict[str, Any]

    def __post_init__(self) -> None:
        message = self.body.get("error") if isinstance(self.body, dict) else None
        RuntimeError.__init__(
            self,
            str(message or f"WorkforceIQ API request failed with status {self.status_code}."),
        )


class WorkforceApiClient:
    def __init__(
        self,
        *,
        base_url: str,
        access_token: str | None = None,
        request_timeout_seconds: int = 15,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token
        self.request_timeout_seconds = request_timeout_seconds

    def clone_with_token(self, access_token: str | None) -> WorkforceApiClient:
        return WorkforceApiClient(
            base_url=self.base_url,
            access_token=access_token,
            request_timeout_seconds=self.request_timeout_seconds,
        )

    def health(self) -> dict[str, Any]:
        return self.request_json("GET", "/api/health")

    def ready(self) -> dict[str, Any]:
        return self.request_json("GET", "/api/health/ready")

    def login(
        self,
        *,
        email: str,
        password: str,
        organization_id: str,
        mfa_code: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "email": email,
            "password": password,
            "organization_id": organization_id,
        }
        if mfa_code:
            payload["mfa_code"] = mfa_code
        return self.request_json("POST", "/api/auth/login", payload=payload)

    def exchange_oidc(self, *, id_token: str, organization_id: str) -> dict[str, Any]:
        return self.request_json(
            "POST",
            "/api/auth/sso/exchange",
            payload={"id_token": id_token, "organization_id": organization_id},
        )

    def refresh(self, *, refresh_token: str) -> dict[str, Any]:
        return self.request_json("POST", "/api/auth/refresh", access_token=refresh_token)

    def logout(self, *, access_token: str | None = None) -> dict[str, Any]:
        return self.request_json("POST", "/api/auth/logout", access_token=access_token or self.access_token)

    def get_employee(self, employee_id: str) -> dict[str, Any]:
        return self.request_json("GET", f"/api/employees/{parse.quote(employee_id, safe='')}")

    def update_employee(self, employee_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        return self.request_json("PATCH", f"/api/employees/{parse.quote(employee_id, safe='')}", payload=changes)

    def search_employees(self, *, query: str, limit: int | None = None) -> dict[str, Any]:
        query_params = {"q": query}
        if limit is not None:
            query_params["limit"] = str(limit)
        return self.request_json("GET", "/api/search/employees", query=query_params)

    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        query: dict[str, str] | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        url = self._build_url(path, query)
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"

        token = access_token if access_token is not None else self.access_token
        if token:
            headers["Authorization"] = f"Bearer {token}"

        api_request = request.Request(url, data=body, headers=headers, method=method.upper())
        try:
            with request.urlopen(api_request, timeout=self.request_timeout_seconds) as response:  # nosec B310
                return _read_json_response(response.read())
        except error.HTTPError as exc:
            raise ApiClientError(status_code=exc.code, body=_read_error_body(exc)) from exc
        except error.URLError as exc:
            raise ApiClientError(status_code=0, body={"error": f"Unable to reach WorkforceIQ API: {exc.reason}"}) from exc

    def _build_url(self, path: str, query: dict[str, str] | None) -> str:
        normalized_path = path if path.startswith("/") else f"/{path}"
        url = f"{self.base_url}{normalized_path}"
        if query:
            url = f"{url}?{parse.urlencode(query)}"
        return url


def _read_json_response(raw_body: bytes) -> dict[str, Any]:
    if not raw_body:
        return {}
    return json.loads(raw_body.decode("utf-8"))


def _read_error_body(exc: error.HTTPError) -> dict[str, Any]:
    raw = exc.read()
    if not raw:
        return {"error": f"WorkforceIQ API request failed with status {exc.code}."}
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return {"error": raw.decode("utf-8", errors="replace")}
