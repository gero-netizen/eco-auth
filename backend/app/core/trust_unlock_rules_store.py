import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings
from app.core.tenant_context import get_current_organization


@dataclass(frozen=True)
class TrustUnlockRules:
    organization_id: str
    duration_hours: int
    max_unlocks_per_month: int
    max_debt_amount: float
    max_overdue_titles: int
    min_interval_hours: int
    notify_before_relock_minutes: int


_DEFAULTS = TrustUnlockRules(
    organization_id="",
    duration_hours=48,
    max_unlocks_per_month=2,
    max_debt_amount=400.0,
    max_overdue_titles=3,
    min_interval_hours=72,
    notify_before_relock_minutes=120,
)


class TrustUnlockRulesStore:
    def __init__(self, database_url: str) -> None:
        prefix = "sqlite:///"
        if not database_url.startswith(prefix):
            raise ValueError("Only sqlite:/// database URLs are supported")
        self._path = Path(database_url.removeprefix(prefix))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS organization_trust_unlock_rules (
                    organization_id TEXT PRIMARY KEY,
                    duration_hours INTEGER NOT NULL DEFAULT 48,
                    max_unlocks_per_month INTEGER NOT NULL DEFAULT 2,
                    max_debt_amount REAL NOT NULL DEFAULT 400.0,
                    max_overdue_titles INTEGER NOT NULL DEFAULT 3,
                    min_interval_hours INTEGER NOT NULL DEFAULT 72,
                    notify_before_relock_minutes INTEGER NOT NULL DEFAULT 120,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def get(self, organization_id: str | None = None) -> TrustUnlockRules:
        current_organization_id = organization_id or get_current_organization()
        with self._connect() as connection:
            row = connection.execute(
                """SELECT * FROM organization_trust_unlock_rules
                WHERE organization_id = ?""",
                (current_organization_id,),
            ).fetchone()
        if row is None:
            return TrustUnlockRules(
                organization_id=current_organization_id,
                duration_hours=_DEFAULTS.duration_hours,
                max_unlocks_per_month=_DEFAULTS.max_unlocks_per_month,
                max_debt_amount=_DEFAULTS.max_debt_amount,
                max_overdue_titles=_DEFAULTS.max_overdue_titles,
                min_interval_hours=_DEFAULTS.min_interval_hours,
                notify_before_relock_minutes=_DEFAULTS.notify_before_relock_minutes,
            )
        return TrustUnlockRules(
            organization_id=current_organization_id,
            duration_hours=int(row["duration_hours"]),
            max_unlocks_per_month=int(row["max_unlocks_per_month"]),
            max_debt_amount=float(row["max_debt_amount"]),
            max_overdue_titles=int(row["max_overdue_titles"]),
            min_interval_hours=int(row["min_interval_hours"]),
            notify_before_relock_minutes=int(row["notify_before_relock_minutes"]),
        )

    def save(
        self,
        organization_id: str,
        duration_hours: int,
        max_unlocks_per_month: int,
        max_debt_amount: float,
        max_overdue_titles: int,
        min_interval_hours: int,
        notify_before_relock_minutes: int,
    ) -> TrustUnlockRules:
        if duration_hours <= 0 or min_interval_hours < 0 or notify_before_relock_minutes < 0:
            raise ValueError("invalid_trust_unlock_rules")
        if max_unlocks_per_month <= 0 or max_overdue_titles <= 0 or max_debt_amount <= 0:
            raise ValueError("invalid_trust_unlock_rules")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO organization_trust_unlock_rules (
                    organization_id, duration_hours, max_unlocks_per_month,
                    max_debt_amount, max_overdue_titles, min_interval_hours,
                    notify_before_relock_minutes, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(organization_id) DO UPDATE SET
                    duration_hours = excluded.duration_hours,
                    max_unlocks_per_month = excluded.max_unlocks_per_month,
                    max_debt_amount = excluded.max_debt_amount,
                    max_overdue_titles = excluded.max_overdue_titles,
                    min_interval_hours = excluded.min_interval_hours,
                    notify_before_relock_minutes = excluded.notify_before_relock_minutes,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    organization_id,
                    duration_hours,
                    max_unlocks_per_month,
                    max_debt_amount,
                    max_overdue_titles,
                    min_interval_hours,
                    notify_before_relock_minutes,
                ),
            )
        return self.get(organization_id)


trust_unlock_rules_store = TrustUnlockRulesStore(get_settings().database_url)
