import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings
from app.core.tenant_context import get_current_organization


class TrustUnlockStore:
    def __init__(self, database_url: str) -> None:
        prefix = "sqlite:///"
        if not database_url.startswith(prefix):
            raise ValueError("Only sqlite:/// database URLs are supported")
        self._path = Path(database_url.removeprefix(prefix))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(trust_unlocks)")
            }
            if columns and "organization_id" not in columns:
                connection.execute(
                    "ALTER TABLE trust_unlocks RENAME TO trust_unlocks_legacy"
                )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS trust_unlocks (
                    organization_id TEXT NOT NULL,
                    id TEXT NOT NULL,
                    client_uuid TEXT NOT NULL,
                    login TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    unlocked_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    PRIMARY KEY (organization_id, id)
                )
                """
            )
            if columns and "organization_id" not in columns:
                connection.execute(
                    """
                    INSERT INTO trust_unlocks (
                        organization_id, id, client_uuid, login, reason,
                        unlocked_at, expires_at, status
                    )
                    SELECT ?, id, client_uuid, login, reason, unlocked_at,
                           expires_at, status
                    FROM trust_unlocks_legacy
                    """,
                    (get_settings().default_organization_id,),
                )
                connection.execute("DROP TABLE trust_unlocks_legacy")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=10)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.row_factory = sqlite3.Row
        return connection

    def create(self, client_uuid: str, login: str, reason: str) -> dict:
        unlocked_at = datetime.now(timezone.utc)
        record = {
            "organization_id": get_current_organization(),
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
                    organization_id, id, client_uuid, login, reason,
                    unlocked_at, expires_at, status
                ) VALUES (
                    :organization_id, :id, :client_uuid, :login, :reason,
                    :unlocked_at, :expires_at, :status
                )
                """,
                record,
            )
        return record

    def list_recent(self) -> list[dict]:
        organization_id = get_current_organization()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM trust_unlocks WHERE organization_id = ?
                ORDER BY unlocked_at DESC LIMIT 100
                """,
                (organization_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_expired_active(self) -> list[dict]:
        now = datetime.now(timezone.utc).isoformat()
        organization_id = get_current_organization()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM trust_unlocks
                WHERE organization_id = ? AND status = 'active' AND expires_at <= ?
                ORDER BY expires_at
                """,
                (organization_id, now),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_active(self, record_id: str) -> dict | None:
        organization_id = get_current_organization()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM trust_unlocks
                WHERE organization_id = ? AND id = ? AND status = 'active'
                """,
                (organization_id, record_id),
            ).fetchone()
        return dict(row) if row else None

    def get_active_by_login(self, login: str) -> dict | None:
        organization_id = get_current_organization()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM trust_unlocks
                WHERE organization_id = ? AND lower(login) = lower(?)
                  AND status = 'active'
                ORDER BY unlocked_at DESC LIMIT 1
                """,
                (organization_id, login),
            ).fetchone()
        return dict(row) if row else None

    def mark_expired(self, record_id: str) -> None:
        organization_id = get_current_organization()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE trust_unlocks SET status = 'expired'
                WHERE organization_id = ? AND id = ? AND status = 'active'
                """,
                (organization_id, record_id),
            )

    def mark_cancelled(self, record_id: str) -> None:
        organization_id = get_current_organization()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE trust_unlocks SET status = 'cancelled'
                WHERE organization_id = ? AND id = ? AND status = 'active'
                """,
                (organization_id, record_id),
            )

    def mark_paid(self, record_id: str) -> None:
        organization_id = get_current_organization()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE trust_unlocks SET status = 'paid'
                WHERE organization_id = ? AND id = ? AND status = 'active'
                """,
                (organization_id, record_id),
            )
