import json
import sqlite3

from app.core import db
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.tenant_context import get_current_organization


class ProvisioningStore:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._path = None
        if not db.is_postgres_url(database_url):
            prefix = "sqlite:///"
            if not database_url.startswith(prefix):
                raise ValueError(
                    "Database URL must start with sqlite:/// or postgresql://"
                )
            self._path = Path(database_url.removeprefix(prefix))
            self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            columns = db.get_existing_columns(
                connection, "provisioning_operations", self._database_url
            )
            if columns and "organization_id" not in columns:
                connection.execute(
                    """
                    ALTER TABLE provisioning_operations
                    RENAME TO provisioning_operations_legacy
                    """
                )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS provisioning_operations (
                    organization_id TEXT NOT NULL,
                    operation_id TEXT NOT NULL,
                    work_order_id TEXT NOT NULL,
                    serial TEXT NOT NULL,
                    profile TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (organization_id, operation_id)
                )
                """
            )
            if columns and "organization_id" not in columns:
                connection.execute(
                    """
                    INSERT INTO provisioning_operations (
                        organization_id, operation_id, work_order_id, serial,
                        profile, result_json, created_at
                    )
                    SELECT ?, operation_id, work_order_id, serial, profile,
                           result_json, created_at
                    FROM provisioning_operations_legacy
                    """,
                    (get_settings().default_organization_id,),
                )
                connection.execute("DROP TABLE provisioning_operations_legacy")

    def _connect(self):
        return db.connect(self._database_url, sqlite_path=self._path, enable_sqlite_wal=True)

    def get(
        self, operation_id: str, organization_id: str | None = None
    ) -> dict[str, Any] | None:
        current_organization_id = organization_id or get_current_organization()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT result_json FROM provisioning_operations "
                "WHERE organization_id = ? AND operation_id = ?",
                (current_organization_id, operation_id),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def save(
        self,
        operation_id: str,
        work_order_id: str,
        serial: str,
        profile: str,
        result: dict[str, Any],
        organization_id: str | None = None,
    ) -> dict[str, Any]:
        current_organization_id = organization_id or get_current_organization()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO provisioning_operations (
                    organization_id, operation_id, work_order_id, serial,
                    profile, result_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (organization_id, operation_id) DO NOTHING
                """,
                (
                    current_organization_id,
                    operation_id,
                    work_order_id,
                    serial,
                    profile,
                    json.dumps(result, separators=(",", ":")),
                ),
            )
            row = connection.execute(
                "SELECT result_json FROM provisioning_operations "
                "WHERE organization_id = ? AND operation_id = ?",
                (current_organization_id, operation_id),
            ).fetchone()
        return json.loads(row[0])

    def list_for_work_order(
        self, work_order_id: str, organization_id: str | None = None
    ) -> list[dict[str, Any]]:
        current_organization_id = organization_id or get_current_organization()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT result_json, created_at
                FROM provisioning_operations
                WHERE organization_id = ? AND work_order_id = ?
                ORDER BY created_at DESC, operation_id DESC
                """,
                (current_organization_id, work_order_id),
            ).fetchall()
        return [
            {**json.loads(result_json), "created_at": created_at}
            for result_json, created_at in rows
        ]
