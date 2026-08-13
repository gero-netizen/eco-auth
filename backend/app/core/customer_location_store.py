import sqlite3

from app.core import db
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import get_settings
from app.core.tenant_context import get_current_organization


class CustomerLocationStore:
    """Localização confirmada por GPS no local, por cliente. Atualizada
    sempre que um técnico conclui um atendimento com localização capturada
    — a próxima OS para o mesmo cliente já nasce com o endereço certo."""

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
                """
                CREATE TABLE IF NOT EXISTS customer_locations (
                    organization_id TEXT NOT NULL,
                    external_customer_id TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    source_work_order_id TEXT,
                    confirmed_by_technician_id TEXT,
                    confirmed_at TEXT NOT NULL,
                    PRIMARY KEY (organization_id, external_customer_id)
                )
                """
            )

    def _connect(self):
        return db.connect(self._database_url, sqlite_path=self._path)

    def confirm(
        self,
        organization_id: str,
        external_customer_id: str,
        latitude: float,
        longitude: float,
        source_work_order_id: str | None = None,
        confirmed_by_technician_id: str | None = None,
    ) -> dict:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO customer_locations (
                    organization_id, external_customer_id, latitude, longitude,
                    source_work_order_id, confirmed_by_technician_id, confirmed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(organization_id, external_customer_id) DO UPDATE SET
                    latitude = excluded.latitude,
                    longitude = excluded.longitude,
                    source_work_order_id = excluded.source_work_order_id,
                    confirmed_by_technician_id = excluded.confirmed_by_technician_id,
                    confirmed_at = excluded.confirmed_at
                """,
                (
                    organization_id, external_customer_id, latitude, longitude,
                    source_work_order_id, confirmed_by_technician_id,
                    datetime.now(UTC).isoformat(),
                ),
            )
        return self.get(organization_id, external_customer_id)

    def get(self, organization_id: str, external_customer_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT * FROM customer_locations
                WHERE organization_id = ? AND external_customer_id = ?""",
                (organization_id, external_customer_id),
            ).fetchone()
        return dict(row) if row else None


customer_location_store = CustomerLocationStore(get_settings().database_url)
