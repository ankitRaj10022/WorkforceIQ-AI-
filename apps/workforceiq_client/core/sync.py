from __future__ import annotations

from typing import Any

from .api import ApiClientError
from .auth import WorkforceAuthenticator
from .models import CachedDocument, QueuedMutation
from .offline_store import OfflineStore


class WorkforceSyncEngine:
    def __init__(self, *, authenticator: WorkforceAuthenticator, store: OfflineStore) -> None:
        self.authenticator = authenticator
        self.store = store

    def queue_employee_update(self, employee_id: str, changes: dict[str, Any]) -> int:
        return self.store.enqueue_mutation(
            mutation_type="employee_update",
            method="PATCH",
            resource_path=f"/api/employees/{employee_id}",
            body=changes,
        )

    def flush(self, *, limit: int = 100) -> list[dict[str, Any]]:
        pending = self.store.list_pending_mutations(limit=limit)
        if not pending:
            return []

        api_client = self.authenticator.build_authenticated_client()
        results: list[dict[str, Any]] = []
        for mutation in pending:
            try:
                response = self._execute_mutation(api_client, mutation)
                self._cache_response(mutation, response)
                self.store.mark_mutation_synced(mutation.mutation_id)
                results.append({"mutation_id": mutation.mutation_id, "status": "synced"})
            except ApiClientError as exc:
                self.store.mark_mutation_failed(mutation.mutation_id, error_message=str(exc))
                results.append(
                    {
                        "mutation_id": mutation.mutation_id,
                        "status": "failed",
                        "error": str(exc),
                        "status_code": exc.status_code,
                    }
                )
        self.store.record_sync_state(name="last_flush", value={"results": results})
        return results

    def pull_employee(self, employee_id: str, *, prefer_cached: bool = False) -> dict[str, Any]:
        cached = self.store.load_cached_employee_profile(employee_id)
        if prefer_cached and cached is not None:
            return cached.payload

        try:
            response = self.authenticator.build_authenticated_client().get_employee(employee_id)
        except ApiClientError:
            if cached is not None:
                return cached.payload
            raise

        self.store.cache_employee_profile(employee_id, response)
        return response

    def cached_employee(self, employee_id: str) -> CachedDocument | None:
        return self.store.load_cached_employee_profile(employee_id)

    def pending_mutations(self, *, limit: int = 100) -> list[QueuedMutation]:
        return self.store.list_pending_mutations(limit=limit)

    def _cache_response(self, mutation: QueuedMutation, response: dict[str, Any]) -> None:
        if mutation.mutation_type == "employee_update":
            employee_id = mutation.resource_path.rsplit("/", 1)[-1]
            self.store.cache_employee_profile(employee_id, response)

    def _execute_mutation(self, api_client, mutation: QueuedMutation) -> dict[str, Any]:
        try:
            return api_client.request_json(
                mutation.method,
                mutation.resource_path,
                payload=mutation.body,
            )
        except ApiClientError as exc:
            if exc.status_code != 401:
                raise
            refreshed_client = self.authenticator.build_authenticated_client()
            try:
                refreshed_session = self.authenticator.refresh_session()
                refreshed_client = refreshed_client.clone_with_token(refreshed_session.tokens.access_token)
            except ApiClientError:
                pass
            return refreshed_client.request_json(
                mutation.method,
                mutation.resource_path,
                payload=mutation.body,
            )
