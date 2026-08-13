import hashlib
import secrets
import sqlite3

from app.core import db
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings


class PortalInviteStore:
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
                """CREATE TABLE IF NOT EXISTS portal_invites (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    customer_id TEXT NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    expires_at TEXT NOT NULL,
                    used_at TEXT,
                    created_at TEXT NOT NULL
                )"""
            )

    def _connect(self):
        return db.connect(self._database_url, sqlite_path=self._path)

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create(self, organization_id: str, customer_id: str) -> dict:
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=1)
        with self._connect() as connection:
            connection.execute(
                """UPDATE portal_invites SET used_at = ?
                WHERE organization_id = ? AND customer_id = ? AND used_at IS NULL""",
                (now.isoformat(), organization_id, customer_id),
            )
            connection.execute(
                """INSERT INTO portal_invites (
                    id, organization_id, customer_id, token_hash,
                    expires_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    f"portal-invite-{uuid4()}",
                    organization_id,
                    customer_id,
                    self._token_hash(token),
                    expires_at.isoformat(),
                    now.isoformat(),
                ),
            )
        return {"token": token, "expires_at": expires_at.isoformat()}

    def consume(self, organization_id: str, token: str) -> dict | None:
        now = datetime.now(timezone.utc)
        with self._connect() as connection:
            if db.is_postgres_url(self._database_url):
                # No Postgres, o SELECT ... FOR UPDATE trava a linha até o
                # commit/rollback, impedindo que duas requisições concorrentes
                # consumam o mesmo convite ao mesmo tempo.
                row = connection.execute(
                    """SELECT * FROM portal_invites
                    WHERE organization_id = ? AND token_hash = ?
                    AND used_at IS NULL AND expires_at >= ?
                    FOR UPDATE""",
                    (organization_id, self._token_hash(token), now.isoformat()),
                ).fetchone()
            else:
                # No SQLite, BEGIN IMMEDIATE adianta o lock de escrita para
                # antes do SELECT, com a mesma finalidade.
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    """SELECT * FROM portal_invites
                    WHERE organization_id = ? AND token_hash = ?
                    AND used_at IS NULL AND expires_at >= ?""",
                    (organization_id, self._token_hash(token), now.isoformat()),
                ).fetchone()
            if row is None:
                connection.rollback()
                return None
            connection.execute(
                "UPDATE portal_invites SET used_at = ? WHERE id = ?",
                (now.isoformat(), row["id"]),
            )
            connection.commit()
        return {
            "organization_id": row["organization_id"],
            "customer_id": row["customer_id"],
            "expires_at": row["expires_at"],
        }

    def inspect(self, organization_id: str, token: str) -> dict | None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            row = connection.execute(
                """SELECT organization_id, customer_id, expires_at
                FROM portal_invites WHERE organization_id = ? AND token_hash = ?
                AND used_at IS NULL AND expires_at >= ?""",
                (organization_id, self._token_hash(token), now),
            ).fetchone()
        return dict(row) if row else None


portal_invite_store = PortalInviteStore(get_settings().database_url)
