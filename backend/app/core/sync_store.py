import json
import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.config import get_settings
from app.core.tenant_context import get_current_organization
from app.domain.models import OperationResult


class SyncOperationStore:
    """Diário durável e isolado por provedor para sincronização móvel."""

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
            operation_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(processed_sync_operations)"
                )
            }
            if operation_columns and "organization_id" not in operation_columns:
                connection.execute(
                    "ALTER TABLE processed_sync_operations "
                    "RENAME TO processed_sync_operations_legacy"
                )
            change_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(sync_changes)")
            }
            if change_columns and "organization_id" not in change_columns:
                connection.execute(
                    "ALTER TABLE sync_changes RENAME TO sync_changes_legacy"
                )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_sync_operations (
                    organization_id TEXT NOT NULL,
                    operation_id TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (organization_id, operation_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_changes (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    organization_id TEXT NOT NULL,
                    operation_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (organization_id, operation_id)
                )
                """
            )
            if operation_columns and "organization_id" not in operation_columns:
                connection.execute(
                    """
                    INSERT INTO processed_sync_operations (
                        organization_id, operation_id, result_json, processed_at
                    )
                    SELECT ?, operation_id, result_json, processed_at
                    FROM processed_sync_operations_legacy
                    """,
                    (get_settings().default_organization_id,),
                )
                connection.execute("DROP TABLE processed_sync_operations_legacy")
            if change_columns and "organization_id" not in change_columns:
                connection.execute(
                    """
                    INSERT INTO sync_changes (
                        sequence, organization_id, operation_id, entity_type,
                        entity_id, kind, payload_json, created_at
                    )
                    SELECT sequence, ?, operation_id, entity_type, entity_id,
                           kind, payload_json, created_at
                    FROM sync_changes_legacy
                    """,
                    (get_settings().default_organization_id,),
                )
                connection.execute("DROP TABLE sync_changes_legacy")

    @staticmethod
    def _organization_id(organization_id: str | None) -> str:
        return organization_id or get_current_organization()

    def get(
        self, operation_id: str, organization_id: str | None = None
    ) -> OperationResult | None:
        current_organization_id = self._organization_id(organization_id)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT result_json FROM processed_sync_operations
                WHERE operation_id = ? AND organization_id = ?
                """,
                (operation_id, current_organization_id),
            ).fetchone()
        return OperationResult.model_validate_json(row[0]) if row else None

    def save(
        self,
        result: OperationResult,
        change: dict[str, Any] | None = None,
        organization_id: str | None = None,
    ) -> OperationResult:
        current_organization_id = self._organization_id(organization_id)
        with self._connect() as connection:
            inserted = connection.execute(
                """
                INSERT OR IGNORE INTO processed_sync_operations
                    (organization_id, operation_id, result_json)
                VALUES (?, ?, ?)
                """,
                (
                    current_organization_id,
                    str(result.operation_id),
                    result.model_dump_json(),
                ),
            )
            if inserted.rowcount == 1 and change is not None:
                connection.execute(
                    """
                    INSERT INTO sync_changes (
                        organization_id, operation_id, entity_type,
                        entity_id, kind, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        current_organization_id,
                        str(result.operation_id),
                        change["entity_type"],
                        change["entity_id"],
                        change["kind"],
                        json.dumps(change["payload"], separators=(",", ":")),
                    ),
                )
            row = connection.execute(
                """
                SELECT result_json FROM processed_sync_operations
                WHERE operation_id = ? AND organization_id = ?
                """,
                (str(result.operation_id), current_organization_id),
            ).fetchone()
        return OperationResult.model_validate_json(row[0])

    def changes_after(
        self,
        cursor: int,
        limit: int = 500,
        organization_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        current_organization_id = self._organization_id(organization_id)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT sequence, entity_type, entity_id, kind, payload_json
                FROM sync_changes
                WHERE sequence > ? AND organization_id = ?
                ORDER BY sequence ASC LIMIT ?
                """,
                (cursor, current_organization_id, limit),
            ).fetchall()
        changes = [
            {
                "sequence": row[0], "entity_type": row[1],
                "entity_id": row[2], "kind": row[3],
                "payload": json.loads(row[4]),
            }
            for row in rows
        ]
        next_cursor = rows[-1][0] if rows else cursor
        return changes, next_cursor

    def append_change(
        self, change: dict[str, Any], organization_id: str | None = None
    ) -> int:
        current_organization_id = self._organization_id(organization_id)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO sync_changes (
                    organization_id, operation_id, entity_type,
                    entity_id, kind, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    current_organization_id, str(uuid4()),
                    change["entity_type"], change["entity_id"], change["kind"],
                    json.dumps(change["payload"], separators=(",", ":")),
                ),
            ).lastrowid
        return int(cursor)
