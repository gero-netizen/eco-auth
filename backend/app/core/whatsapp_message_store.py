import sqlite3

from app.core import db
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings
from app.core.tenant_context import get_current_organization

DIRECTIONS = ("outbound", "inbound")
STATUSES = ("sent", "failed", "simulated_sent", "blocked", "received")


class WhatsappMessageStore:
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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS whatsapp_messages (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    login TEXT,
                    template TEXT,
                    body TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_reason TEXT,
                    wa_message_id TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_org_created
                ON whatsapp_messages (organization_id, created_at DESC)
                """
            )

    def _connect(self):
        return db.connect(self._database_url, sqlite_path=self._path)

    def record(
        self,
        organization_id: str,
        direction: str,
        phone: str,
        body: str,
        status: str,
        template: str | None = None,
        login: str | None = None,
        error_reason: str | None = None,
        wa_message_id: str | None = None,
    ) -> dict:
        if direction not in DIRECTIONS:
            raise ValueError("invalid_direction")
        if status not in STATUSES:
            raise ValueError("invalid_status")
        message_id = f"wa-msg-{uuid4()}"
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO whatsapp_messages (
                    id, organization_id, direction, phone, login, template,
                    body, status, error_reason, wa_message_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    message_id,
                    organization_id,
                    direction,
                    phone,
                    login,
                    template,
                    body,
                    status,
                    error_reason,
                    wa_message_id,
                ),
            )
        return self.get(organization_id, message_id)

    def get(self, organization_id: str, message_id: str) -> dict:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM whatsapp_messages WHERE organization_id = ? AND id = ?",
                (organization_id, message_id),
            ).fetchone()
        if row is None:
            raise KeyError("whatsapp_message_not_found")
        return dict(row)

    def list_recent(self, organization_id: str | None = None, limit: int = 50) -> list[dict]:
        current_organization_id = organization_id or get_current_organization()
        safe_limit = max(1, min(limit, 200))
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT * FROM whatsapp_messages WHERE organization_id = ?
                ORDER BY created_at DESC LIMIT ?""",
                (current_organization_id, safe_limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_conversation(
        self, organization_id: str, phone: str, limit: int = 50
    ) -> list[dict]:
        safe_limit = max(1, min(limit, 200))
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT * FROM whatsapp_messages
                WHERE organization_id = ? AND phone = ?
                ORDER BY created_at ASC LIMIT ?""",
                (organization_id, phone, safe_limit),
            ).fetchall()
        return [dict(row) for row in rows]


whatsapp_message_store = WhatsappMessageStore(get_settings().database_url)
