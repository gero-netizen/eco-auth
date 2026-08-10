import hashlib
import hmac
import os
import sqlite3
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings


class TechnicianStore:
    def __init__(self, database_url: str) -> None:
        self._path = Path(database_url.removeprefix("sqlite:///"))
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
                CREATE TABLE IF NOT EXISTS technicians (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        settings = get_settings()
        if settings.technician_username and settings.technician_password:
            self.create_if_missing(
                "bench-technician",
                "Técnico de Bancada",
                settings.technician_username,
                settings.technician_password,
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
            current = cls._hash_password(password, bytes.fromhex(salt_hex)).split(":", 1)[1]
            return hmac.compare_digest(current, expected)
        except (ValueError, TypeError):
            return False

    def create_if_missing(self, technician_id: str, name: str, username: str, password: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO technicians (id, name, username, password_hash)
                VALUES (?, ?, ?, ?)
                """,
                (technician_id, name, username, self._hash_password(password)),
            )

    def authenticate(self, username: str, password: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, name, username, password_hash, active FROM technicians WHERE username = ?",
                (username,),
            ).fetchone()
        if row is None or not row["active"] or not self._verify_password(password, row["password_hash"]):
            return None
        return {"id": row["id"], "name": row["name"], "username": row["username"]}

    def get_active(self, technician_id: str, username: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, name, username FROM technicians WHERE id = ? AND username = ? AND active = 1",
                (technician_id, username),
            ).fetchone()
        return dict(row) if row else None

    def list_all(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, name, username, active, created_at FROM technicians ORDER BY name"
            ).fetchall()
        return [dict(row) for row in rows]

    def create(self, name: str, username: str, password: str) -> dict:
        technician_id = f"technician-{uuid4()}"
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO technicians (id, name, username, password_hash) VALUES (?, ?, ?, ?)",
                    (technician_id, name, username, self._hash_password(password)),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("technician_username_already_exists") from error
        return {"id": technician_id, "name": name, "username": username, "active": 1}

    def set_active(self, technician_id: str, active: bool) -> None:
        with self._connect() as connection:
            updated = connection.execute(
                "UPDATE technicians SET active = ? WHERE id = ?",
                (int(active), technician_id),
            )
        if updated.rowcount == 0:
            raise KeyError("technician_not_found")

    def delete(self, technician_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM technicians WHERE id = ?", (technician_id,))


technician_store = TechnicianStore(get_settings().database_url)
