import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.api.routes.technician_auth import require_technician
from app.api.routes.central_auth import require_central_roles
from app.core.config import get_settings
from app.core.tenant_context import get_current_organization

router = APIRouter(prefix="/network", tags=["network-monitor-simulator"])
_database_path = Path(get_settings().database_url.removeprefix("sqlite:///"))


class NetworkAlert(BaseModel):
    id: str
    severity: str
    title: str
    area: str
    status: str
    detected_at: datetime
    kind: str = "manual_simulation"
    auto_detected: bool = False
    simulated: bool = True


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(_database_path, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def _initialize() -> None:
    _database_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(network_incidents)")
        }
        if columns and "organization_id" not in columns:
            connection.execute(
                "ALTER TABLE network_incidents RENAME TO network_incidents_legacy"
            )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS network_incidents (
                organization_id TEXT NOT NULL,
                id TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                area TEXT NOT NULL,
                status TEXT NOT NULL,
                detected_at TEXT NOT NULL,
                resolved_at TEXT,
                PRIMARY KEY (organization_id, id)
            )
            """
        )
        incident_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(network_incidents)")
        }
        if "kind" not in incident_columns:
            connection.execute(
                "ALTER TABLE network_incidents ADD COLUMN kind TEXT NOT NULL DEFAULT 'manual'"
            )
        if "auto_detected" not in incident_columns:
            connection.execute(
                "ALTER TABLE network_incidents ADD COLUMN auto_detected INTEGER NOT NULL DEFAULT 0"
            )
        if columns and "organization_id" not in columns:
            connection.execute(
                """
                INSERT INTO network_incidents (
                    organization_id, id, severity, title, area, status,
                    detected_at, resolved_at
                )
                SELECT ?, id, severity, title, area, status, detected_at, resolved_at
                FROM network_incidents_legacy
                """,
                (get_settings().default_organization_id,),
            )
            connection.execute("DROP TABLE network_incidents_legacy")
        count = connection.execute(
            "SELECT COUNT(*) FROM network_incidents WHERE organization_id = ?",
            (get_settings().default_organization_id,),
        ).fetchone()[0]
        if count == 0:
            create_network_incident(
                connection=connection,
                organization_id=get_settings().default_organization_id,
            )


def create_network_incident(
    connection: sqlite3.Connection | None = None,
    organization_id: str | None = None,
    kind: str = "manual_simulation",
    severity: str = "warning",
    title: str = "Indisponibilidade de rede detectada",
    area: str = "Rede de bancada",
    auto_detected: bool = False,
) -> NetworkAlert:
    current_organization_id = organization_id or get_current_organization()
    alert = NetworkAlert(
        id=f"sim-network-{uuid4()}",
        severity=severity,
        title=title,
        area=area,
        status="active",
        detected_at=datetime.now(timezone.utc),
    )
    owns_connection = connection is None
    current = connection or _connect()
    try:
        current.execute(
            """
            INSERT INTO network_incidents (
                organization_id, id, severity, title, area, status,
                detected_at, kind, auto_detected
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                current_organization_id,
                alert.id,
                alert.severity,
                alert.title,
                alert.area,
                alert.status,
                alert.detected_at.isoformat(),
                kind,
                int(auto_detected),
            ),
        )
        if owns_connection:
            current.commit()
    finally:
        if owns_connection:
            current.close()
    return alert


def get_active_incident_by_kind(organization_id: str, kind: str) -> dict | None:
    """Usado para evitar chamados duplicados: só abre um novo incidente do
    mesmo tipo se não houver um já ativo para este provedor."""
    with _connect() as connection:
        row = connection.execute(
            """SELECT * FROM network_incidents
            WHERE organization_id = ? AND kind = ? AND status = 'active'
            ORDER BY detected_at DESC LIMIT 1""",
            (organization_id, kind),
        ).fetchone()
    return dict(row) if row else None


def resolve_incidents_by_kind(organization_id: str, kind: str) -> int:
    """Encerra automaticamente incidentes de um tipo quando a rede normaliza."""
    with _connect() as connection:
        updated = connection.execute(
            """UPDATE network_incidents SET status = 'resolved', resolved_at = ?
            WHERE organization_id = ? AND kind = ? AND status = 'active'""",
            (datetime.now(timezone.utc).isoformat(), organization_id, kind),
        )
    return updated.rowcount


def list_active_alerts(organization_id: str | None = None) -> list[NetworkAlert]:
    current_organization_id = organization_id or get_current_organization()
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT * FROM network_incidents
            WHERE status = 'active' AND organization_id = ?
            ORDER BY detected_at DESC
            """,
            (current_organization_id,),
        ).fetchall()
    return [
        NetworkAlert(
            id=row["id"],
            severity=row["severity"],
            title=row["title"],
            area=row["area"],
            status=row["status"],
            detected_at=datetime.fromisoformat(row["detected_at"]),
            kind=row["kind"],
            auto_detected=bool(row["auto_detected"]),
        )
        for row in rows
    ]


def resolve_network_incidents(organization_id: str | None = None) -> int:
    current_organization_id = organization_id or get_current_organization()
    with _connect() as connection:
        updated = connection.execute(
            """
            UPDATE network_incidents
            SET status = 'resolved', resolved_at = ?
            WHERE status = 'active' AND organization_id = ?
            """,
            (datetime.now(timezone.utc).isoformat(), current_organization_id),
        )
    return updated.rowcount


_initialize()


@router.get("/alerts", response_model=list[NetworkAlert], dependencies=[Depends(require_technician)])
async def active_alerts(
    technician: dict = Depends(require_technician),
) -> list[NetworkAlert]:
    return list_active_alerts(technician["organization_id"])


@router.post("/incidents/simulate")
async def simulate_incident(
    session: dict = Depends(require_central_roles("owner", "admin")),
) -> RedirectResponse:
    create_network_incident(organization_id=session["organization"]["id"])
    return RedirectResponse("/central", status_code=303)


@router.post("/incidents/resolve")
async def resolve_incidents(
    session: dict = Depends(require_central_roles("owner", "admin")),
) -> RedirectResponse:
    resolve_network_incidents(session["organization"]["id"])
    return RedirectResponse("/central", status_code=303)
