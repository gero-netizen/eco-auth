import sqlite3

from app.core import db
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings
from app.core.tenant_context import get_current_organization


class PixSimulationStore:
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
            columns = db.get_existing_columns(
                connection, "pix_simulations", self._database_url
            )
            if columns and "organization_id" not in columns:
                connection.execute(
                    "ALTER TABLE pix_simulations RENAME TO pix_simulations_legacy"
                )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS pix_simulations (
                    organization_id TEXT NOT NULL,
                    id TEXT NOT NULL,
                    title_uuid TEXT NOT NULL,
                    title_number TEXT NOT NULL,
                    login TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    simulated_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    PRIMARY KEY (organization_id, id)
                )
                """
            )
            if columns and "organization_id" not in columns:
                connection.execute(
                    """
                    INSERT INTO pix_simulations (
                        organization_id, id, title_uuid, title_number, login,
                        amount, simulated_at, status
                    )
                    SELECT ?, id, title_uuid, title_number, login, amount,
                           simulated_at, status
                    FROM pix_simulations_legacy
                    """,
                    (get_settings().default_organization_id,),
                )
                connection.execute("DROP TABLE pix_simulations_legacy")

    def _connect(self):
        return db.connect(self._database_url, sqlite_path=self._path, enable_sqlite_wal=True)

    def create(
        self,
        title_uuid: str,
        title_number: str,
        login: str,
        amount: str,
        status: str = "simulated",
    ) -> dict:
        record = {
            "organization_id": get_current_organization(),
            "id": str(uuid4()),
            "title_uuid": title_uuid,
            "title_number": title_number,
            "login": login,
            "amount": amount,
            "simulated_at": datetime.now(timezone.utc).isoformat(),
            "status": status,
        }
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO pix_simulations (
                    organization_id, id, title_uuid, title_number, login,
                    amount, simulated_at, status
                ) VALUES (
                    :organization_id, :id, :title_uuid, :title_number, :login,
                    :amount, :simulated_at, :status
                )
                """,
                record,
            )
        return record

    def has_real_payment(self, title_uuid: str) -> bool:
        organization_id = get_current_organization()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1 FROM pix_simulations
                WHERE organization_id = ? AND title_uuid = ?
                  AND status = 'real_paid' LIMIT 1
                """,
                (organization_id, title_uuid),
            ).fetchone()
        return row is not None

    def list_recent(self) -> list[dict]:
        organization_id = get_current_organization()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM pix_simulations WHERE organization_id = ?
                ORDER BY simulated_at DESC LIMIT 100
                """,
                (organization_id,),
            ).fetchall()
        return [dict(row) for row in rows]
