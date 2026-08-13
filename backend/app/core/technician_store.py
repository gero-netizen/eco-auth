import hashlib
import hmac
import os
import secrets
import sqlite3

from app.core import db
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings


class TechnicianStore:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._path = None
        if not db.is_postgres_url(database_url):
            self._path = Path(database_url.removeprefix("sqlite:///"))
            self._path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        return db.connect(self._database_url, sqlite_path=self._path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS technicians (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (organization_id, username)
                )
                """
            )
            columns = db.get_existing_columns(connection, "technicians", self._database_url)
            if "organization_id" not in columns:
                self._migrate_to_organizations(connection)
            if "must_change_password" not in columns:
                connection.execute(
                    "ALTER TABLE technicians ADD COLUMN must_change_password "
                    "INTEGER NOT NULL DEFAULT 0"
                )
        settings = get_settings()
        if settings.technician_username and settings.technician_password:
            self.create_if_missing(
                "bench-technician",
                "Técnico de Bancada",
                settings.technician_username,
                settings.technician_password,
                settings.default_organization_id,
            )

    @staticmethod
    def _migrate_to_organizations(connection) -> None:
        default_organization_id = get_settings().default_organization_id
        connection.execute(
            """
            CREATE TABLE technicians_saas (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                name TEXT NOT NULL,
                username TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (organization_id, username)
            )
            """
        )
        connection.execute(
            """
            INSERT INTO technicians_saas (
                id, organization_id, name, username, password_hash, active, created_at
            )
            SELECT id, ?, name, username, password_hash, active, created_at
            FROM technicians
            """,
            (default_organization_id,),
        )
        connection.execute("DROP TABLE technicians")
        connection.execute("ALTER TABLE technicians_saas RENAME TO technicians")

    @staticmethod
    def _hash_password(password: str, salt: bytes | None = None) -> str:
        current_salt = salt or os.urandom(16)
        digest = hashlib.scrypt(
            password.encode("utf-8"), salt=current_salt, n=16384, r=8, p=1
        )
        return f"{current_salt.hex()}:{digest.hex()}"

    @classmethod
    def _verify_password(cls, password: str, stored: str) -> bool:
        try:
            salt_hex, expected = stored.split(":", 1)
            current = cls._hash_password(password, bytes.fromhex(salt_hex)).split(":", 1)[1]
            return hmac.compare_digest(current, expected)
        except (ValueError, TypeError):
            return False

    def create_if_missing(
        self,
        technician_id: str,
        name: str,
        username: str,
        password: str,
        organization_id: str | None = None,
    ) -> None:
        current_organization_id = organization_id or get_settings().default_organization_id
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO technicians (
                    id, organization_id, name, username, password_hash
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    technician_id,
                    current_organization_id,
                    name,
                    username,
                    self._hash_password(password),
                ),
            )

    def authenticate(
        self, username: str, password: str, organization_id: str | None = None
    ) -> dict | None:
        current_organization_id = organization_id or get_settings().default_organization_id
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, organization_id, name, username, password_hash, active,
                    must_change_password
                FROM technicians
                WHERE organization_id = ? AND username = ?
                """,
                (current_organization_id, username),
            ).fetchone()
        if row is None or not row["active"] or not self._verify_password(password, row["password_hash"]):
            return None
        return {
            "id": row["id"],
            "organization_id": row["organization_id"],
            "name": row["name"],
            "username": row["username"],
            "must_change_password": bool(row["must_change_password"]),
        }

    def get_active(
        self, technician_id: str, username: str, organization_id: str | None = None
    ) -> dict | None:
        current_organization_id = organization_id or get_settings().default_organization_id
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, organization_id, name, username
                FROM technicians
                WHERE id = ? AND username = ? AND organization_id = ? AND active = 1
                """,
                (technician_id, username, current_organization_id),
            ).fetchone()
        return dict(row) if row else None

    def list_all(self, organization_id: str | None = None) -> list[dict]:
        current_organization_id = organization_id or get_settings().default_organization_id
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, organization_id, name, username, active, created_at
                FROM technicians
                WHERE organization_id = ?
                ORDER BY name
                """,
                (current_organization_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create(
        self,
        name: str,
        username: str,
        password: str,
        organization_id: str | None = None,
    ) -> dict:
        current_organization_id = organization_id or get_settings().default_organization_id
        technician_id = f"technician-{uuid4()}"
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO technicians (
                        id, organization_id, name, username, password_hash
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        technician_id,
                        current_organization_id,
                        name,
                        username,
                        self._hash_password(password),
                    ),
                )
        except db.IntegrityError as error:
            raise ValueError("technician_username_already_exists") from error
        return {
            "id": technician_id,
            "organization_id": current_organization_id,
            "name": name,
            "username": username,
            "active": 1,
        }

    def set_active(
        self, technician_id: str, active: bool, organization_id: str | None = None
    ) -> None:
        current_organization_id = organization_id or get_settings().default_organization_id
        with self._connect() as connection:
            updated = connection.execute(
                """
                UPDATE technicians SET active = ?
                WHERE id = ? AND organization_id = ?
                """,
                (int(active), technician_id, current_organization_id),
            )
        if updated.rowcount == 0:
            raise KeyError("technician_not_found")

    def change_password(
        self,
        technician_id: str,
        current_password: str,
        new_password: str,
        organization_id: str | None = None,
    ) -> None:
        """Troca a senha do próprio técnico. Exige a senha atual correta —
        nunca permite trocar sem confirmar quem está pedindo."""
        current_organization_id = organization_id or get_settings().default_organization_id
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT password_hash FROM technicians
                WHERE id = ? AND organization_id = ? AND active = 1
                """,
                (technician_id, current_organization_id),
            ).fetchone()
            if row is None:
                raise KeyError("technician_not_found")
            if not self._verify_password(current_password, row["password_hash"]):
                raise ValueError("current_password_incorrect")
            connection.execute(
                """
                UPDATE technicians SET password_hash = ?, must_change_password = 0
                WHERE id = ? AND organization_id = ?
                """,
                (
                    self._hash_password(new_password),
                    technician_id,
                    current_organization_id,
                ),
            )

    def reset_password(
        self, technician_id: str, organization_id: str | None = None
    ) -> str:
        """Recuperação de acesso: o dono/admin gera uma senha temporária
        nova para o técnico (ex.: esqueceu a senha, trocou de aparelho).
        A senha só é exibida uma vez, na tela do admin — o técnico é
        obrigado a trocá-la assim que fizer login de novo."""
        current_organization_id = organization_id or get_settings().default_organization_id
        temporary_password = secrets.token_urlsafe(9)
        with self._connect() as connection:
            updated = connection.execute(
                """
                UPDATE technicians
                SET password_hash = ?, must_change_password = 1
                WHERE id = ? AND organization_id = ? AND active = 1
                """,
                (
                    self._hash_password(temporary_password),
                    technician_id,
                    current_organization_id,
                ),
            )
        if updated.rowcount == 0:
            raise KeyError("technician_not_found")
        return temporary_password

    def delete(self, technician_id: str, organization_id: str | None = None) -> None:
        current_organization_id = organization_id or get_settings().default_organization_id
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM technicians WHERE id = ? AND organization_id = ?",
                (technician_id, current_organization_id),
            )


technician_store = TechnicianStore(get_settings().database_url)
