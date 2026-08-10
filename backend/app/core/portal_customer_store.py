import hashlib
import hmac
import os
import sqlite3
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings


class PortalCustomerStore:
    def __init__(self, database_url: str) -> None:
        prefix = "sqlite:///"
        if not database_url.startswith(prefix):
            raise ValueError("Only sqlite:/// database URLs are supported")
        self._path = Path(database_url.removeprefix(prefix))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS portal_customers (
                    id TEXT NOT NULL,
                    organization_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (organization_id, id),
                    UNIQUE (organization_id, username)
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

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

    def ensure_demo(self, organization_id: str, organization_name: str) -> None:
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT 1 FROM portal_customers
                WHERE organization_id = ? AND lower(username) = 'cliente'
                """,
                (organization_id,),
            ).fetchone()
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO portal_customers (
                        id, organization_id, name, username, password_hash
                    ) VALUES (?, ?, ?, 'cliente', ?)
                    """,
                    (
                        "sim-customer-1",
                        organization_id,
                        f"Cliente de Bancada — {organization_name}",
                        self._hash_password("Cliente@2026"),
                    ),
                )

    def authenticate(
        self, organization_id: str, username: str, password: str
    ) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM portal_customers
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

    def get_active(self, organization_id: str, customer_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM portal_customers
                WHERE organization_id = ? AND id = ? AND active = 1
                """,
                (organization_id, customer_id),
            ).fetchone()
        return self._public(row) if row else None

    def list_all(self, organization_id: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM portal_customers WHERE organization_id = ? ORDER BY name, username",
                (organization_id,),
            ).fetchall()
        return [self._public(row) for row in rows]

    def create(self, organization_id: str, name: str, username: str, password: str) -> dict:
        customer_id = f"portal-customer-{uuid4()}"
        try:
            with self._connect() as connection:
                connection.execute(
                    """INSERT INTO portal_customers
                    (id, organization_id, name, username, password_hash)
                    VALUES (?, ?, ?, ?, ?)""",
                    (customer_id, organization_id, name, username.casefold(), self._hash_password(password)),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("portal_username_already_exists") from error
        customer = self.get_active(organization_id, customer_id)
        if customer is None:
            raise RuntimeError("portal_customer_creation_failed")
        return customer

    def set_active(self, organization_id: str, customer_id: str, active: bool) -> None:
        with self._connect() as connection:
            updated = connection.execute(
                "UPDATE portal_customers SET active = ? WHERE organization_id = ? AND id = ?",
                (int(active), organization_id, customer_id),
            )
        if updated.rowcount == 0:
            raise KeyError("portal_customer_not_found")

    def reset_password(self, organization_id: str, customer_id: str, password: str) -> None:
        with self._connect() as connection:
            updated = connection.execute(
                "UPDATE portal_customers SET password_hash = ? WHERE organization_id = ? AND id = ?",
                (self._hash_password(password), organization_id, customer_id),
            )
        if updated.rowcount == 0:
            raise KeyError("portal_customer_not_found")

    @staticmethod
    def _public(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "organization_id": row["organization_id"],
            "name": row["name"],
            "username": row["username"],
            "active": row["active"],
            "created_at": row["created_at"],
        }


portal_customer_store = PortalCustomerStore(get_settings().database_url)
