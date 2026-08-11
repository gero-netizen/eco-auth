import sqlite3
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings
from app.core.tenant_context import get_current_organization


class CtoStore:
    """Cadastro real de CTOs (caixas de splitter): coordenadas, capacidade
    de portas e vínculo de cada porta a um cliente/OS específico."""

    def __init__(self, database_url: str) -> None:
        prefix = "sqlite:///"
        if not database_url.startswith(prefix):
            raise ValueError("Only sqlite:/// database URLs are supported")
        self._path = Path(database_url.removeprefix(prefix))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ctos (
                    id TEXT NOT NULL,
                    organization_id TEXT NOT NULL,
                    code TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    total_ports INTEGER NOT NULL,
                    splitter_ratio TEXT NOT NULL DEFAULT '1:8',
                    pop_reference TEXT,
                    notes TEXT,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (organization_id, id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS cto_port_assignments (
                    organization_id TEXT NOT NULL,
                    cto_id TEXT NOT NULL,
                    port_number INTEGER NOT NULL,
                    login TEXT NOT NULL,
                    work_order_id TEXT,
                    assigned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (organization_id, cto_id, port_number)
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def create(
        self,
        organization_id: str,
        code: str,
        latitude: float,
        longitude: float,
        total_ports: int,
        splitter_ratio: str = "1:8",
        pop_reference: str | None = None,
        notes: str | None = None,
    ) -> dict:
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError("invalid_coordinates")
        if total_ports <= 0 or total_ports > 144:
            raise ValueError("invalid_total_ports")
        cto_id = f"cto-{uuid4()}"
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO ctos (
                    id, organization_id, code, latitude, longitude,
                    total_ports, splitter_ratio, pop_reference, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    cto_id, organization_id, code, latitude, longitude,
                    total_ports, splitter_ratio, pop_reference, notes,
                ),
            )
        return self.get(organization_id, cto_id)

    def get(self, organization_id: str, cto_id: str) -> dict:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM ctos WHERE organization_id = ? AND id = ?",
                (organization_id, cto_id),
            ).fetchone()
        if row is None:
            raise KeyError("cto_not_found")
        return self._with_occupancy(dict(row))

    def list_active(self, organization_id: str | None = None) -> list[dict]:
        current_organization_id = organization_id or get_current_organization()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM ctos WHERE organization_id = ? AND active = 1 ORDER BY code",
                (current_organization_id,),
            ).fetchall()
        return [self._with_occupancy(dict(row)) for row in rows]

    def _occupied_ports(self, organization_id: str, cto_id: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT * FROM cto_port_assignments
                WHERE organization_id = ? AND cto_id = ? ORDER BY port_number""",
                (organization_id, cto_id),
            ).fetchall()
        return [dict(row) for row in rows]

    def _with_occupancy(self, cto: dict) -> dict:
        occupied = self._occupied_ports(cto["organization_id"], cto["id"])
        cto["occupied_ports"] = len(occupied)
        cto["available_ports"] = max(0, cto["total_ports"] - len(occupied))
        cto["assignments"] = occupied
        return cto

    def assign_port(
        self,
        organization_id: str,
        cto_id: str,
        port_number: int,
        login: str,
        work_order_id: str | None = None,
    ) -> dict:
        cto = self.get(organization_id, cto_id)
        if not 1 <= port_number <= cto["total_ports"]:
            raise ValueError("invalid_port_number")
        try:
            with self._connect() as connection:
                connection.execute(
                    """INSERT INTO cto_port_assignments (
                        organization_id, cto_id, port_number, login, work_order_id
                    ) VALUES (?, ?, ?, ?, ?)""",
                    (organization_id, cto_id, port_number, login, work_order_id),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("port_already_assigned") from error
        return self.get(organization_id, cto_id)

    def release_port(self, organization_id: str, cto_id: str, port_number: int) -> None:
        with self._connect() as connection:
            connection.execute(
                """DELETE FROM cto_port_assignments
                WHERE organization_id = ? AND cto_id = ? AND port_number = ?""",
                (organization_id, cto_id, port_number),
            )

    def deactivate(self, organization_id: str, cto_id: str) -> None:
        with self._connect() as connection:
            updated = connection.execute(
                "UPDATE ctos SET active = 0 WHERE organization_id = ? AND id = ?",
                (organization_id, cto_id),
            )
        if updated.rowcount == 0:
            raise KeyError("cto_not_found")


cto_store = CtoStore(get_settings().database_url)
