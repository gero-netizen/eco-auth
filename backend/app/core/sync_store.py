import sqlite3
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.domain.models import OperationResult


class SyncOperationStore:
    """Durable idempotency journal for operations received from mobile devices."""

    def __init__(self, database_url: str) -> None:
        self._database_path = self._path_from_url(database_url)
        self._initialize()

    @staticmethod
    def _path_from_url(database_url: str) -> Path:
        prefix = "sqlite:///"
        if not database_url.startswith(prefix):
            raise ValueError("Only sqlite:/// database URLs are supported")
        path = Path(database_url.removeprefix(prefix))
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=10)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_sync_operations (
                    operation_id TEXT PRIMARY KEY,
                    result_json TEXT NOT NULL,
                    processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_changes (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_id TEXT NOT NULL UNIQUE,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def get(self, operation_id: str) -> OperationResult | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT result_json FROM processed_sync_operations WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
        return OperationResult.model_validate_json(row[0]) if row else None

    def save(
        self,
        result: OperationResult,
        change: dict[str, Any] | None = None,
    ) -> OperationResult:
        """Save once and return the original result if another request won the race."""
        with self._connect() as connection:
            inserted = connection.execute(
                """
                INSERT OR IGNORE INTO processed_sync_operations
                    (operation_id, result_json)
                VALUES (?, ?)
                """,
                (str(result.operation_id), result.model_dump_json()),
            )
            if inserted.rowcount == 1 and change is not None:
                connection.execute(
                    """
                    INSERT INTO sync_changes (
                        operation_id, entity_type, entity_id, kind, payload_json
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(result.operation_id),
                        change["entity_type"],
                        change["entity_id"],
                        change["kind"],
                        json.dumps(change["payload"], separators=(",", ":")),
                    ),
                )
            row = connection.execute(
                "SELECT result_json FROM processed_sync_operations WHERE operation_id = ?",
                (str(result.operation_id),),
            ).fetchone()
        return OperationResult.model_validate_json(row[0])

    def changes_after(
        self,
        cursor: int,
        limit: int = 500,
    ) -> tuple[list[dict[str, Any]], int]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT sequence, entity_type, entity_id, kind, payload_json
                FROM sync_changes
                WHERE sequence > ?
                ORDER BY sequence ASC
                LIMIT ?
                """,
                (cursor, limit),
            ).fetchall()
        changes = [
            {
                "sequence": row[0],
                "entity_type": row[1],
                "entity_id": row[2],
                "kind": row[3],
                "payload": json.loads(row[4]),
            }
            for row in rows
        ]
        next_cursor = rows[-1][0] if rows else cursor
        return changes, next_cursor

    def append_change(self, change: dict[str, Any]) -> int:
        """Publish a server-side change for the next incremental mobile pull."""
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO sync_changes (
                    operation_id, entity_type, entity_id, kind, payload_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    change["entity_type"],
                    change["entity_id"],
                    change["kind"],
                    json.dumps(change["payload"], separators=(",", ":")),
                ),
            ).lastrowid
        return int(cursor)
