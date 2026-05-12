from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet

from .models import CachedDocument, QueuedMutation, SessionSnapshot, utc_now_iso


class OfflineStore:
    def __init__(self, *, db_path: Path, token_key_path: Path) -> None:
        self.db_path = db_path
        self.token_key_path = token_key_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_key_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS auth_session (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    encrypted_payload BLOB NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS resource_cache (
                    namespace TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (namespace, resource_id)
                );

                CREATE TABLE IF NOT EXISTS sync_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mutation_type TEXT NOT NULL,
                    method TEXT NOT NULL,
                    resource_path TEXT NOT NULL,
                    body TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_error TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_sync_queue_status_id
                ON sync_queue(status, id);

                CREATE TABLE IF NOT EXISTS sync_state (
                    name TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    def save_session(self, session: SessionSnapshot) -> None:
        payload = json.dumps(session.to_payload()).encode("utf-8")
        encrypted = self._cipher().encrypt(payload)
        updated_at = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO auth_session(id, encrypted_payload, updated_at)
                VALUES (1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    encrypted_payload = excluded.encrypted_payload,
                    updated_at = excluded.updated_at
                """,
                (encrypted, updated_at),
            )

    def load_session(self) -> SessionSnapshot | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT encrypted_payload FROM auth_session WHERE id = 1"
            ).fetchone()
        if row is None:
            return None
        decrypted = self._cipher().decrypt(row["encrypted_payload"])
        return SessionSnapshot.from_payload(json.loads(decrypted.decode("utf-8")))

    def clear_session(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM auth_session WHERE id = 1")

    def cache_document(self, *, namespace: str, resource_id: str, payload: dict[str, Any]) -> None:
        updated_at = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO resource_cache(namespace, resource_id, payload, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(namespace, resource_id) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (namespace, resource_id, json.dumps(payload), updated_at),
            )

    def load_cached_document(self, *, namespace: str, resource_id: str) -> CachedDocument | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT namespace, resource_id, payload, updated_at
                FROM resource_cache
                WHERE namespace = ? AND resource_id = ?
                """,
                (namespace, resource_id),
            ).fetchone()
        if row is None:
            return None
        return CachedDocument(
            namespace=str(row["namespace"]),
            resource_id=str(row["resource_id"]),
            payload=json.loads(str(row["payload"])),
            updated_at=str(row["updated_at"]),
        )

    def cache_employee_profile(self, employee_id: str, payload: dict[str, Any]) -> None:
        self.cache_document(namespace="employee_profile", resource_id=employee_id, payload=payload)

    def load_cached_employee_profile(self, employee_id: str) -> CachedDocument | None:
        return self.load_cached_document(namespace="employee_profile", resource_id=employee_id)

    def enqueue_mutation(
        self,
        *,
        mutation_type: str,
        method: str,
        resource_path: str,
        body: dict[str, Any],
    ) -> int:
        timestamp = utc_now_iso()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sync_queue(
                    mutation_type,
                    method,
                    resource_path,
                    body,
                    status,
                    attempts,
                    created_at,
                    updated_at,
                    last_error
                ) VALUES (?, ?, ?, ?, 'pending', 0, ?, ?, NULL)
                """,
                (mutation_type, method.upper(), resource_path, json.dumps(body), timestamp, timestamp),
            )
            return int(cursor.lastrowid)

    def list_pending_mutations(self, *, limit: int = 100) -> list[QueuedMutation]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, mutation_type, method, resource_path, body, status, attempts, created_at, updated_at, last_error
                FROM sync_queue
                WHERE status IN ('pending', 'failed')
                ORDER BY id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._queued_mutation_from_row(row) for row in rows]

    def mark_mutation_synced(self, mutation_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE sync_queue
                SET status = 'synced', updated_at = ?, last_error = NULL
                WHERE id = ?
                """,
                (utc_now_iso(), mutation_id),
            )

    def mark_mutation_failed(self, mutation_id: int, *, error_message: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE sync_queue
                SET status = 'failed',
                    attempts = attempts + 1,
                    updated_at = ?,
                    last_error = ?
                WHERE id = ?
                """,
                (utc_now_iso(), error_message, mutation_id),
            )

    def record_sync_state(self, *, name: str, value: dict[str, Any]) -> None:
        updated_at = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sync_state(name, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (name, json.dumps(value), updated_at),
            )

    def load_sync_state(self, name: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM sync_state WHERE name = ?",
                (name,),
            ).fetchone()
        if row is None:
            return None
        return json.loads(str(row["value"]))

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _cipher(self) -> Fernet:
        if not self.token_key_path.exists():
            self.token_key_path.write_bytes(Fernet.generate_key())
            with suppress(OSError):
                os.chmod(self.token_key_path, 0o600)
        return Fernet(self.token_key_path.read_bytes())

    @staticmethod
    def _queued_mutation_from_row(row: sqlite3.Row) -> QueuedMutation:
        return QueuedMutation(
            mutation_id=int(row["id"]),
            mutation_type=str(row["mutation_type"]),
            method=str(row["method"]),
            resource_path=str(row["resource_path"]),
            body=json.loads(str(row["body"])),
            status=str(row["status"]),
            attempts=int(row["attempts"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            last_error=str(row["last_error"]) if row["last_error"] is not None else None,
        )
