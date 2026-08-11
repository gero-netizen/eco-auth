import sqlite3
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings
from app.core.tenant_context import get_current_organization


class WorkOrderHistoryStore:
    def __init__(self, database_url: str) -> None:
        prefix = "sqlite:///"
        if not database_url.startswith(prefix):
            raise ValueError("Only sqlite:/// database URLs are supported")
        self._path = Path(database_url.removeprefix(prefix))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS work_order_history (
                    id TEXT NOT NULL,
                    organization_id TEXT NOT NULL,
                    work_order_id TEXT NOT NULL,
                    from_status TEXT,
                    to_status TEXT NOT NULL,
                    note TEXT,
                    latitude REAL,
                    longitude REAL,
                    technician_id TEXT,
                    occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (organization_id, id)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_work_order_history_order
                ON work_order_history (organization_id, work_order_id, occurred_at)
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def record(
        self,
        organization_id: str,
        work_order_id: str,
        to_status: str,
        from_status: str | None = None,
        note: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        technician_id: str | None = None,
    ) -> dict:
        entry_id = f"woh-{uuid4()}"
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO work_order_history (
                    id, organization_id, work_order_id, from_status, to_status,
                    note, latitude, longitude, technician_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry_id, organization_id, work_order_id, from_status, to_status,
                    note, latitude, longitude, technician_id,
                ),
            )
            row = connection.execute(
                "SELECT * FROM work_order_history WHERE organization_id = ? AND id = ?",
                (organization_id, entry_id),
            ).fetchone()
        return dict(row)

    def list_for_work_order(
        self, organization_id: str, work_order_id: str
    ) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT * FROM work_order_history
                WHERE organization_id = ? AND work_order_id = ?
                ORDER BY occurred_at ASC""",
                (organization_id, work_order_id),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_for_technician(
        self, organization_id: str | None = None, technician_id: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        current_organization_id = organization_id or get_current_organization()
        safe_limit = max(1, min(limit, 500))
        with self._connect() as connection:
            if technician_id:
                rows = connection.execute(
                    """SELECT * FROM work_order_history
                    WHERE organization_id = ? AND technician_id = ?
                    ORDER BY occurred_at DESC LIMIT ?""",
                    (current_organization_id, technician_id, safe_limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    """SELECT * FROM work_order_history
                    WHERE organization_id = ? ORDER BY occurred_at DESC LIMIT ?""",
                    (current_organization_id, safe_limit),
                ).fetchall()
        return [dict(row) for row in rows]


work_order_history_store = WorkOrderHistoryStore(get_settings().database_url)
