import json
import sqlite3
from pathlib import Path
from typing import Any


class ProvisioningStore:
    def __init__(self, database_url: str) -> None:
        prefix = "sqlite:///"
        if not database_url.startswith(prefix):
            raise ValueError("Only sqlite:/// database URLs are supported")
        self._path = Path(database_url.removeprefix(prefix))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS provisioning_operations (
                    operation_id TEXT PRIMARY KEY,
                    work_order_id TEXT NOT NULL,
                    serial TEXT NOT NULL,
                    profile TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=10)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def get(self, operation_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT result_json FROM provisioning_operations "
                "WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def save(
        self,
        operation_id: str,
        work_order_id: str,
        serial: str,
        profile: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO provisioning_operations (
                    operation_id, work_order_id, serial, profile, result_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    operation_id,
                    work_order_id,
                    serial,
                    profile,
                    json.dumps(result, separators=(",", ":")),
                ),
            )
            row = connection.execute(
                "SELECT result_json FROM provisioning_operations "
                "WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
        return json.loads(row[0])

    def list_for_work_order(self, work_order_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT result_json, created_at
                FROM provisioning_operations
                WHERE work_order_id = ?
                ORDER BY created_at DESC, operation_id DESC
                """,
                (work_order_id,),
            ).fetchall()
        return [
            {**json.loads(result_json), "created_at": created_at}
            for result_json, created_at in rows
        ]
