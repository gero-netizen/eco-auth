import sqlite3
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings
from app.core.tenant_context import get_current_organization

STATUSES = ("pending", "confirmed", "rejected", "expired", "error")


class FinancialPaymentStore:
    def __init__(self, database_url: str) -> None:
        prefix = "sqlite:///"
        if not database_url.startswith(prefix):
            raise ValueError("Only sqlite:/// database URLs are supported")
        self._path = Path(database_url.removeprefix(prefix))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS financial_payments (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    title_uuid TEXT NOT NULL,
                    login TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    mp_payment_id TEXT,
                    external_reference TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    confirmed_at TEXT,
                    error_reason TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (organization_id, external_reference)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_financial_payments_mp_id
                ON financial_payments (mp_payment_id)
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def create(
        self,
        organization_id: str,
        title_uuid: str,
        login: str,
        amount: str,
        external_reference: str,
        mp_payment_id: str | None = None,
    ) -> dict:
        payment_id = f"fin-pay-{uuid4()}"
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO financial_payments (
                    id, organization_id, title_uuid, login, amount,
                    mp_payment_id, external_reference, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
                (
                    payment_id,
                    organization_id,
                    title_uuid,
                    login,
                    amount,
                    mp_payment_id,
                    external_reference,
                ),
            )
        return self.get(organization_id, payment_id)

    def get(self, organization_id: str, payment_id: str) -> dict:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM financial_payments WHERE organization_id = ? AND id = ?",
                (organization_id, payment_id),
            ).fetchone()
        if row is None:
            raise KeyError("financial_payment_not_found")
        return dict(row)

    def get_by_mp_payment_id(
        self, organization_id: str, mp_payment_id: str
    ) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT * FROM financial_payments
                WHERE organization_id = ? AND mp_payment_id = ?""",
                (organization_id, mp_payment_id),
            ).fetchone()
        return dict(row) if row else None

    def get_by_external_reference(
        self, organization_id: str, external_reference: str
    ) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT * FROM financial_payments
                WHERE organization_id = ? AND external_reference = ?""",
                (organization_id, external_reference),
            ).fetchone()
        return dict(row) if row else None

    def mark_confirmed(
        self, organization_id: str, payment_id: str, mp_payment_id: str
    ) -> dict:
        """Idempotente: se este registro já estiver confirmado, não faz nada
        (a baixa no MK-AUTH já foi disparada da primeira vez) — protege
        contra reentregas do webhook do Mercado Pago."""
        current = self.get(organization_id, payment_id)
        if current["status"] == "confirmed":
            return current
        with self._connect() as connection:
            connection.execute(
                """UPDATE financial_payments SET
                    status = 'confirmed', mp_payment_id = ?, confirmed_at = CURRENT_TIMESTAMP
                WHERE organization_id = ? AND id = ?""",
                (mp_payment_id, organization_id, payment_id),
            )
        return self.get(organization_id, payment_id)

    def mark_error(self, organization_id: str, payment_id: str, reason: str) -> dict:
        with self._connect() as connection:
            connection.execute(
                """UPDATE financial_payments SET status = 'error', error_reason = ?
                WHERE organization_id = ? AND id = ?""",
                (reason, organization_id, payment_id),
            )
        return self.get(organization_id, payment_id)

    def list_recent(self, organization_id: str | None = None, limit: int = 50) -> list[dict]:
        current_organization_id = organization_id or get_current_organization()
        safe_limit = max(1, min(limit, 200))
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT * FROM financial_payments WHERE organization_id = ?
                ORDER BY created_at DESC, rowid DESC LIMIT ?""",
                (current_organization_id, safe_limit),
            ).fetchall()
        return [dict(row) for row in rows]


financial_payment_store = FinancialPaymentStore(get_settings().database_url)
