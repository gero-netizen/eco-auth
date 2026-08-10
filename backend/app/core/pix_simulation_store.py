import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class PixSimulationStore:
    def __init__(self, database_url: str) -> None:
        prefix = "sqlite:///"
        if not database_url.startswith(prefix):
            raise ValueError("Only sqlite:/// database URLs are supported")
        self._path = Path(database_url.removeprefix(prefix))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS pix_simulations (
                    id TEXT PRIMARY KEY,
                    title_uuid TEXT NOT NULL,
                    title_number TEXT NOT NULL,
                    login TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    simulated_at TEXT NOT NULL,
                    status TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=10)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.row_factory = sqlite3.Row
        return connection

    def create(
        self,
        title_uuid: str,
        title_number: str,
        login: str,
        amount: str,
        status: str = "simulated",
    ) -> dict:
        record = {
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
                    id, title_uuid, title_number, login, amount, simulated_at, status
                ) VALUES (
                    :id, :title_uuid, :title_number, :login, :amount, :simulated_at, :status
                )
                """,
                record,
            )
        return record

    def has_real_payment(self, title_uuid: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM pix_simulations WHERE title_uuid = ? AND status = 'real_paid' LIMIT 1",
                (title_uuid,),
            ).fetchone()
        return row is not None

    def list_recent(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM pix_simulations ORDER BY simulated_at DESC LIMIT 100"
            ).fetchall()
        return [dict(row) for row in rows]
