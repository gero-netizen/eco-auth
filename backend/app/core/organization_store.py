import sqlite3

from app.core import db
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings


class OrganizationStore:
    """Cadastro mínimo de provedores para a transição multiempresa."""

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
        self._initialize()

    def _connect(self):
        return db.connect(self._database_url, sqlite_path=self._path)

    def _initialize(self) -> None:
        settings = get_settings()
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS organizations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    slug TEXT NOT NULL UNIQUE,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                INSERT INTO organizations (id, name, slug)
                VALUES (?, ?, ?)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    settings.default_organization_id,
                    settings.default_organization_name,
                    settings.default_organization_slug,
                ),
            )
            columns = db.get_existing_columns(connection, "organizations", self._database_url)
            for name, definition in {
                "primary_color": "TEXT NOT NULL DEFAULT '#075e54'",
                "support_email": "TEXT NOT NULL DEFAULT ''",
                "support_phone": "TEXT NOT NULL DEFAULT ''",
            }.items():
                if name not in columns:
                    connection.execute(
                        f"ALTER TABLE organizations ADD COLUMN {name} {definition}"
                    )

    def get_active(self, organization_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM organizations
                WHERE id = ? AND active = 1
                """,
                (organization_id,),
            ).fetchone()
        return dict(row) if row else None

    def get(self, organization_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM organizations WHERE id = ?
                """,
                (organization_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_all(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM organizations ORDER BY name
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_active_by_slug(self, slug: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM organizations
                WHERE lower(slug) = lower(?) AND active = 1
                """,
                (slug,),
            ).fetchone()
        return dict(row) if row else None

    def get_default(self) -> dict:
        organization = self.get_active(get_settings().default_organization_id)
        if organization is None:
            raise RuntimeError("default_organization_not_available")
        return organization

    def create(self, name: str, slug: str) -> dict:
        organization_id = f"org-{uuid4()}"
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO organizations (id, name, slug)
                    VALUES (?, ?, ?)
                    """,
                    (organization_id, name, slug),
                )
        except db.IntegrityError as error:
            raise ValueError("organization_slug_already_exists") from error
        organization = self.get_active(organization_id)
        if organization is None:
            raise RuntimeError("organization_creation_failed")
        return organization

    def set_active(self, organization_id: str, active: bool) -> None:
        with self._connect() as connection:
            updated = connection.execute(
                "UPDATE organizations SET active = ? WHERE id = ?",
                (int(active), organization_id),
            )
        if updated.rowcount == 0:
            raise KeyError("organization_not_found")

    def update_branding(
        self,
        organization_id: str,
        name: str,
        primary_color: str,
        support_email: str,
        support_phone: str,
    ) -> dict:
        with self._connect() as connection:
            updated = connection.execute(
                """UPDATE organizations
                SET name = ?, primary_color = ?, support_email = ?, support_phone = ?
                WHERE id = ?""",
                (
                    name,
                    primary_color.casefold(),
                    support_email.casefold(),
                    support_phone,
                    organization_id,
                ),
            )
        if updated.rowcount == 0:
            raise KeyError("organization_not_found")
        organization = self.get(organization_id)
        if organization is None:
            raise RuntimeError("organization_update_failed")
        return organization

    def delete(self, organization_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM organizations WHERE id = ?", (organization_id,)
            )


organization_store = OrganizationStore(get_settings().database_url)
