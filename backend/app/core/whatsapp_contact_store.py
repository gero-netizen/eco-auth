import sqlite3

from app.core import db
from pathlib import Path

from app.core.config import get_settings
from app.core.tenant_context import get_current_organization


class WhatsappContactStore:
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
                CREATE TABLE IF NOT EXISTS whatsapp_contacts (
                    organization_id TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    display_name TEXT,
                    login TEXT,
                    portal_customer_id TEXT,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (organization_id, phone)
                )
                """
            )

    def _connect(self):
        return db.connect(self._database_url, sqlite_path=self._path)

    def upsert(
        self,
        organization_id: str,
        phone: str,
        display_name: str | None = None,
        login: str | None = None,
        portal_customer_id: str | None = None,
    ) -> dict:
        """Preenche o que for informado sem apagar o que já foi vinculado
        antes (ex.: o nome do perfil chega pelo webhook, o login chega de um
        envio anterior — cada canal só sabe uma parte)."""
        existing = self.get(organization_id, phone)
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO whatsapp_contacts (
                    organization_id, phone, display_name, login, portal_customer_id
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(organization_id, phone) DO UPDATE SET
                    display_name = excluded.display_name,
                    login = excluded.login,
                    portal_customer_id = excluded.portal_customer_id,
                    updated_at = CURRENT_TIMESTAMP""",
                (
                    organization_id,
                    phone,
                    display_name or (existing["display_name"] if existing else None),
                    login or (existing["login"] if existing else None),
                    portal_customer_id
                    or (existing["portal_customer_id"] if existing else None),
                ),
            )
        return self.get(organization_id, phone)

    def get(self, organization_id: str, phone: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM whatsapp_contacts WHERE organization_id = ? AND phone = ?",
                (organization_id, phone),
            ).fetchone()
        return dict(row) if row else None

    def list_all(self, organization_id: str | None = None) -> list[dict]:
        current_organization_id = organization_id or get_current_organization()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM whatsapp_contacts WHERE organization_id = ? ORDER BY updated_at DESC",
                (current_organization_id,),
            ).fetchall()
        return [dict(row) for row in rows]


whatsapp_contact_store = WhatsappContactStore(get_settings().database_url)
