import sqlite3

from app.core import db
from pathlib import Path

from app.core.config import get_settings
from app.core.tenant_context import get_current_organization

_OPT_OUT_KEYWORDS = {"parar", "sair", "stop", "cancelar", "descadastrar"}


class WhatsappConsentStore:
    """Bloqueio de mensagens por número, por provedor. Um número bloqueado
    nunca recebe envios reais até ser desbloqueado explicitamente."""

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
                CREATE TABLE IF NOT EXISTS whatsapp_blocked_numbers (
                    organization_id TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    reason TEXT,
                    blocked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (organization_id, phone)
                )
                """
            )

    def _connect(self):
        return db.connect(self._database_url, sqlite_path=self._path)

    @staticmethod
    def is_opt_out_message(text: str) -> bool:
        normalized = (text or "").strip().casefold()
        return normalized in _OPT_OUT_KEYWORDS

    def is_blocked(self, organization_id: str, phone: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT 1 FROM whatsapp_blocked_numbers
                WHERE organization_id = ? AND phone = ?""",
                (organization_id, phone),
            ).fetchone()
        return row is not None

    def block(
        self, organization_id: str, phone: str, reason: str = "opt_out"
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO whatsapp_blocked_numbers (organization_id, phone, reason)
                VALUES (?, ?, ?)
                ON CONFLICT(organization_id, phone) DO UPDATE SET
                    reason = excluded.reason, blocked_at = CURRENT_TIMESTAMP""",
                (organization_id, phone, reason),
            )

    def unblock(self, organization_id: str, phone: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM whatsapp_blocked_numbers WHERE organization_id = ? AND phone = ?",
                (organization_id, phone),
            )

    def list_blocked(self, organization_id: str | None = None) -> list[dict]:
        current_organization_id = organization_id or get_current_organization()
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT * FROM whatsapp_blocked_numbers WHERE organization_id = ?
                ORDER BY blocked_at DESC""",
                (current_organization_id,),
            ).fetchall()
        return [dict(row) for row in rows]


whatsapp_consent_store = WhatsappConsentStore(get_settings().database_url)
