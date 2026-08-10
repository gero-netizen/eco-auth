import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4


class TrustUnlockStore:
    def __init__(self, database_url: str) -> None:
        prefix = "sqlite:///"
        if not database_url.startswith(prefix):
            raise ValueError("Only sqlite:/// database URLs are supported")
        self._path = Path(database_url.removeprefix(prefix))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS trust_unlocks (
                    id TEXT PRIMARY KEY,
                    client_uuid TEXT NOT NULL,
                    login TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    unlocked_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    status TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=10)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.row_factory = sqlite3.Row
        return connection

    def create(self, client_uuid: str, login: str, reason: str) -> dict:
        unlocked_at = datetime.now(timezone.utc)
        record = {
            "id": str(uuid4()),
            "client_uuid": client_uuid,
            "login": login,
            "reason": reason,
            "unlocked_at": unlocked_at.isoformat(),
            "expires_at": (unlocked_at + timedelta(hours=48)).isoformat(),
            "status": "active",
        }
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO trust_unlocks (
                    id, client_uuid, login, reason, unlocked_at, expires_at, status
                ) VALUES (:id, :client_uuid, :login, :reason, :unlocked_at, :expires_at, :status)
                """,
                record,
            )
        return record

    def list_recent(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM trust_unlocks ORDER BY unlocked_at DESC LIMIT 100"
            ).fetchall()
        return [dict(row) for row in rows]

    def list_expired_active(self) -> list[dict]:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM trust_unlocks WHERE status = 'active' AND expires_at <= ? ORDER BY expires_at",
                (now,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_active(self, record_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM trust_unlocks WHERE id = ? AND status = 'active'",
                (record_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_active_by_login(self, login: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM trust_unlocks
                WHERE lower(login) = lower(?) AND status = 'active'
                ORDER BY unlocked_at DESC LIMIT 1
                """,
                (login,),
            ).fetchone()
        return dict(row) if row else None

    def mark_expired(self, record_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE trust_unlocks SET status = 'expired' WHERE id = ? AND status = 'active'",
                (record_id,),
            )

    def mark_cancelled(self, record_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE trust_unlocks SET status = 'cancelled' WHERE id = ? AND status = 'active'",
                (record_id,),
            )

    def mark_paid(self, record_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE trust_unlocks SET status = 'paid' WHERE id = ? AND status = 'active'",
                (record_id,),
            )
