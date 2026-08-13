import sqlite3

from app.core import db
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings
from app.core.tenant_context import get_current_organization


class TrustUnlockStore:
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
            columns = db.get_existing_columns(connection, "trust_unlocks", self._database_url)
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
            unlock_columns = db.get_existing_columns(
                connection, "trust_unlocks", self._database_url
            )
            if "notified_before_relock" not in unlock_columns:
                connection.execute(
                    "ALTER TABLE trust_unlocks ADD COLUMN notified_before_relock INTEGER NOT NULL DEFAULT 0"
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

    def _connect(self):
        return db.connect(self._database_url, sqlite_path=self._path, enable_sqlite_wal=True)

    def create(
        self, client_uuid: str, login: str, reason: str, duration_hours: int = 48
    ) -> dict:
        unlocked_at = datetime.now(timezone.utc)
        record = {
            "organization_id": get_current_organization(),
            "id": str(uuid4()),
            "client_uuid": client_uuid,
            "login": login,
            "reason": reason,
            "unlocked_at": unlocked_at.isoformat(),
            "expires_at": (unlocked_at + timedelta(hours=duration_hours)).isoformat(),
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

    def count_since(self, login: str, since: datetime) -> int:
        organization_id = get_current_organization()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) FROM trust_unlocks
                WHERE organization_id = ? AND lower(login) = lower(?)
                  AND unlocked_at >= ? AND status != 'cancelled'
                """,
                (organization_id, login, since.isoformat()),
            ).fetchone()
        return int(row[0]) if row else 0

    def get_most_recent_by_login(self, login: str) -> dict | None:
        organization_id = get_current_organization()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM trust_unlocks
                WHERE organization_id = ? AND lower(login) = lower(?)
                ORDER BY unlocked_at DESC LIMIT 1
                """,
                (organization_id, login),
            ).fetchone()
        return dict(row) if row else None

    def list_expiring_soon(self, organization_id: str, within_minutes: int) -> list[dict]:
        now = datetime.now(timezone.utc)
        cutoff = (now + timedelta(minutes=within_minutes)).isoformat()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM trust_unlocks
                WHERE organization_id = ? AND status = 'active'
                  AND expires_at <= ? AND expires_at > ?
                  AND notified_before_relock = 0
                ORDER BY expires_at
                """,
                (organization_id, cutoff, now.isoformat()),
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_notified(self, organization_id: str, record_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE trust_unlocks SET notified_before_relock = 1
                WHERE organization_id = ? AND id = ?
                """,
                (organization_id, record_id),
            )

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
