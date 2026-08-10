import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.api.routes.technician_auth import require_technician
from app.core.config import get_settings

router = APIRouter(prefix="/network", tags=["network-monitor-simulator"])
_database_path = Path(get_settings().database_url.removeprefix("sqlite:///"))


class NetworkAlert(BaseModel):
    id: str
    severity: str
    title: str
    area: str
    status: str
    detected_at: datetime
    simulated: bool = True


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(_database_path, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def _initialize() -> None:
    _database_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS network_incidents (
                id TEXT PRIMARY KEY,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                area TEXT NOT NULL,
                status TEXT NOT NULL,
                detected_at TEXT NOT NULL,
                resolved_at TEXT
            )
            """
        )
        count = connection.execute(
            "SELECT COUNT(*) FROM network_incidents"
        ).fetchone()[0]
        if count == 0:
            create_network_incident(connection=connection)


def create_network_incident(
    connection: sqlite3.Connection | None = None,
) -> NetworkAlert:
    alert = NetworkAlert(
        id=f"sim-network-{uuid4()}",
        severity="warning",
        title="Indisponibilidade de rede detectada",
        area="Rede de bancada",
        status="active",
        detected_at=datetime.now(timezone.utc),
    )
    owns_connection = connection is None
    current = connection or _connect()
    try:
        current.execute(
            """
            INSERT INTO network_incidents (
                id, severity, title, area, status, detected_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                alert.id,
                alert.severity,
                alert.title,
                alert.area,
                alert.status,
                alert.detected_at.isoformat(),
            ),
        )
        if owns_connection:
            current.commit()
    finally:
        if owns_connection:
            current.close()
    return alert


def list_active_alerts() -> list[NetworkAlert]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT * FROM network_incidents
            WHERE status = 'active' ORDER BY detected_at DESC
            """
        ).fetchall()
    return [
        NetworkAlert(
            id=row["id"],
            severity=row["severity"],
            title=row["title"],
            area=row["area"],
            status=row["status"],
            detected_at=datetime.fromisoformat(row["detected_at"]),
        )
        for row in rows
    ]


def resolve_network_incidents() -> int:
    with _connect() as connection:
        updated = connection.execute(
            """
            UPDATE network_incidents
            SET status = 'resolved', resolved_at = ? WHERE status = 'active'
            """,
            (datetime.now(timezone.utc).isoformat(),),
        )
    return updated.rowcount


_initialize()


@router.get("/alerts", response_model=list[NetworkAlert], dependencies=[Depends(require_technician)])
async def active_alerts() -> list[NetworkAlert]:
    return list_active_alerts()


@router.post("/incidents/simulate")
async def simulate_incident() -> RedirectResponse:
    create_network_incident()
    return RedirectResponse("/central", status_code=303)


@router.post("/incidents/resolve")
async def resolve_incidents() -> RedirectResponse:
    resolve_network_incidents()
    return RedirectResponse("/central", status_code=303)
