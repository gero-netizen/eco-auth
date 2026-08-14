from pathlib import Path
from uuid import uuid4

from app.core import db
from app.core.config import get_settings
from app.core.tenant_context import get_current_organization

CABLE_TYPES = ("backbone", "distribuicao", "drop")


class NetworkSegmentStore:
    """Rotas de cabo da rede FTTH — trechos que conectam dois pontos
    (uma CTO cadastrada, ou um ponto livre como um POP). Usado para
    desenhar o mapa visual da rede."""

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
                CREATE TABLE IF NOT EXISTS network_segments (
                    id TEXT NOT NULL,
                    organization_id TEXT NOT NULL,
                    from_cto_id TEXT,
                    from_label TEXT,
                    from_latitude REAL NOT NULL,
                    from_longitude REAL NOT NULL,
                    to_cto_id TEXT,
                    to_label TEXT,
                    to_latitude REAL NOT NULL,
                    to_longitude REAL NOT NULL,
                    cable_type TEXT NOT NULL DEFAULT 'distribuicao',
                    fiber_count INTEGER,
                    notes TEXT,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (organization_id, id)
                )
                """
            )

    def _connect(self):
        return db.connect(self._database_url, sqlite_path=self._path)

    def create(
        self,
        organization_id: str,
        from_point: dict,
        to_point: dict,
        cable_type: str,
        fiber_count: int | None,
        notes: str | None,
    ) -> dict:
        if cable_type not in CABLE_TYPES:
            raise ValueError("invalid_cable_type")
        segment_id = f"segment-{uuid4()}"
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO network_segments (
                    id, organization_id, from_cto_id, from_label,
                    from_latitude, from_longitude, to_cto_id, to_label,
                    to_latitude, to_longitude, cable_type, fiber_count, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    segment_id, organization_id,
                    from_point.get("cto_id"), from_point.get("label"),
                    from_point["latitude"], from_point["longitude"],
                    to_point.get("cto_id"), to_point.get("label"),
                    to_point["latitude"], to_point["longitude"],
                    cable_type, fiber_count, notes,
                ),
            )
        return self.get(organization_id, segment_id)

    def get(self, organization_id: str, segment_id: str) -> dict:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM network_segments WHERE organization_id = ? AND id = ?",
                (organization_id, segment_id),
            ).fetchone()
        if row is None:
            raise KeyError("network_segment_not_found")
        return dict(row)

    def list_active(self, organization_id: str | None = None) -> list[dict]:
        current_organization_id = organization_id or get_current_organization()
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT * FROM network_segments
                WHERE organization_id = ? AND active = 1
                ORDER BY created_at""",
                (current_organization_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def deactivate(self, organization_id: str, segment_id: str) -> None:
        with self._connect() as connection:
            result = connection.execute(
                """UPDATE network_segments SET active = 0
                WHERE organization_id = ? AND id = ?""",
                (organization_id, segment_id),
            )
        if result.rowcount == 0:
            raise KeyError("network_segment_not_found")


network_segment_store = NetworkSegmentStore(get_settings().database_url)
