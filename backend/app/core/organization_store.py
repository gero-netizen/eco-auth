import sqlite3
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings


class OrganizationStore:
    """Cadastro mínimo de provedores para a transição multiempresa."""

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
                INSERT OR IGNORE INTO organizations (id, name, slug)
                VALUES (?, ?, ?)
                """,
                (
                    settings.default_organization_id,
                    settings.default_organization_name,
                    settings.default_organization_slug,
                ),
            )

    def get_active(self, organization_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, name, slug, active, created_at
                FROM organizations
                WHERE id = ? AND active = 1
                """,
                (organization_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_active_by_slug(self, slug: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, name, slug, active, created_at
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
        except sqlite3.IntegrityError as error:
            raise ValueError("organization_slug_already_exists") from error
        organization = self.get_active(organization_id)
        if organization is None:
            raise RuntimeError("organization_creation_failed")
        return organization


organization_store = OrganizationStore(get_settings().database_url)
