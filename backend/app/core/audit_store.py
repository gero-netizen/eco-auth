import json
import sqlite3
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings


class AuditStore:
    def __init__(self, database_url: str) -> None:
        prefix = "sqlite:///"
        if not database_url.startswith(prefix):
            raise ValueError("Only sqlite:/// database URLs are supported")
        self._path = Path(database_url.removeprefix(prefix))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    user_name TEXT NOT NULL,
                    username TEXT NOT NULL,
                    role TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target TEXT NOT NULL,
                    details TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_audit_events_org_created
                ON audit_events (organization_id, created_at DESC)
                """
            )

    def record(
        self,
        organization_id: str,
        user: dict,
        action: str,
        target: str,
        details: dict | None = None,
    ) -> dict:
        event_id = f"audit-{uuid4()}"
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_events (
                    id, organization_id, user_id, user_name, username,
                    role, action, target, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    organization_id,
                    user["id"],
                    user["name"],
                    user["username"],
                    user["role"],
                    action,
                    target,
                    json.dumps(details or {}, ensure_ascii=False, sort_keys=True),
                ),
            )
        return self.get(event_id, organization_id)

    def get(self, event_id: str, organization_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, organization_id, user_id, user_name, username,
                       role, action, target, details, created_at
                FROM audit_events WHERE id = ? AND organization_id = ?
                """,
                (event_id, organization_id),
            ).fetchone()
        return self._public(row) if row else None

    def list_recent(self, organization_id: str, limit: int = 200) -> list[dict]:
        safe_limit = max(1, min(limit, 500))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, organization_id, user_id, user_name, username,
                       role, action, target, details, created_at
                FROM audit_events WHERE organization_id = ?
                ORDER BY created_at DESC, rowid DESC LIMIT ?
                """,
                (organization_id, safe_limit),
            ).fetchall()
        return [self._public(row) for row in rows]

    @staticmethod
    def _public(row: sqlite3.Row) -> dict:
        item = dict(row)
        try:
            item["details"] = json.loads(item["details"])
        except (TypeError, json.JSONDecodeError):
            item["details"] = {}
        return item


audit_store = AuditStore(get_settings().database_url)
