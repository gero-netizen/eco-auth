import hashlib
import hmac
import os
import sqlite3
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings

CENTRAL_USER_ROLES = {"owner", "admin", "attendant", "viewer"}


class CentralUserStore:
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
                CREATE TABLE IF NOT EXISTS central_users (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (organization_id, username)
                )
                """
            )
        if settings.central_username and settings.central_password:
            self.create_if_missing(
                "bench-owner",
                settings.default_organization_id,
                "Proprietário",
                settings.central_username,
                settings.central_password,
                "owner",
            )

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
            current = cls._hash_password(
                password, bytes.fromhex(salt_hex)
            ).split(":", 1)[1]
            return hmac.compare_digest(current, expected)
        except (TypeError, ValueError):
            return False

    def create_if_missing(
        self,
        user_id: str,
        organization_id: str,
        name: str,
        username: str,
        password: str,
        role: str,
    ) -> None:
        if role not in CENTRAL_USER_ROLES:
            raise ValueError("invalid_central_user_role")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO central_users (
                    id, organization_id, name, username, password_hash, role
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    organization_id,
                    name,
                    username.casefold(),
                    self._hash_password(password),
                    role,
                ),
            )

    def authenticate(
        self, organization_id: str, username: str, password: str
    ) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, organization_id, name, username, password_hash,
                       role, active, created_at
                FROM central_users
                WHERE organization_id = ? AND lower(username) = lower(?)
                """,
                (organization_id, username),
            ).fetchone()
        if (
            row is None
            or not row["active"]
            or not self._verify_password(password, row["password_hash"])
        ):
            return None
        return self._public(row)

    def get_active(self, user_id: str, organization_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, organization_id, name, username, role, active, created_at
                FROM central_users
                WHERE id = ? AND organization_id = ? AND active = 1
                """,
                (user_id, organization_id),
            ).fetchone()
        return dict(row) if row else None

    def list_all(self, organization_id: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, organization_id, name, username, role, active, created_at
                FROM central_users
                WHERE organization_id = ? ORDER BY name
                """,
                (organization_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create(
        self,
        organization_id: str,
        name: str,
        username: str,
        password: str,
        role: str,
    ) -> dict:
        if role not in CENTRAL_USER_ROLES:
            raise ValueError("invalid_central_user_role")
        user_id = f"central-user-{uuid4()}"
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO central_users (
                        id, organization_id, name, username, password_hash, role
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        organization_id,
                        name,
                        username.casefold(),
                        self._hash_password(password),
                        role,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("central_username_already_exists") from error
        user = self.get_active(user_id, organization_id)
        if user is None:
            raise RuntimeError("central_user_creation_failed")
        return user

    def delete(self, user_id: str, organization_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM central_users WHERE id = ? AND organization_id = ?",
                (user_id, organization_id),
            )

    @staticmethod
    def _public(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "organization_id": row["organization_id"],
            "name": row["name"],
            "username": row["username"],
            "role": row["role"],
            "active": row["active"],
            "created_at": row["created_at"],
        }


central_user_store = CentralUserStore(get_settings().database_url)
