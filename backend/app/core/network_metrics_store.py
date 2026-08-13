import sqlite3

from app.core import db
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.core.config import get_settings
from app.core.tenant_context import get_current_organization


class NetworkMetricsStore:
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
                CREATE TABLE IF NOT EXISTS network_metrics (
                    organization_id TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    router_reachable INTEGER NOT NULL,
                    active_sessions INTEGER,
                    cpu_load INTEGER,
                    radius_ok INTEGER
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_network_metrics_org_time
                ON network_metrics (organization_id, recorded_at DESC)
                """
            )

    def _connect(self):
        return db.connect(self._database_url, sqlite_path=self._path)

    def record(
        self,
        organization_id: str,
        router_reachable: bool,
        active_sessions: int | None = None,
        cpu_load: int | None = None,
        radius_ok: bool | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO network_metrics (
                    organization_id, recorded_at, router_reachable,
                    active_sessions, cpu_load, radius_ok
                ) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    organization_id,
                    datetime.now(UTC).isoformat(),
                    int(router_reachable),
                    active_sessions,
                    cpu_load,
                    None if radius_ok is None else int(radius_ok),
                ),
            )

    def average_sessions(
        self, organization_id: str, window_minutes: int, exclude_last: int = 0
    ) -> float | None:
        """Média de sessões ativas na janela recente, usada como linha de
        base para detectar quedas anormais. exclude_last permite ignorar as
        leituras mais recentes (ex.: a atual), evitando que ela contamine a
        própria comparação."""
        since = (datetime.now(UTC) - timedelta(minutes=window_minutes)).isoformat()
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT active_sessions FROM network_metrics
                WHERE organization_id = ? AND recorded_at >= ?
                  AND active_sessions IS NOT NULL
                ORDER BY recorded_at DESC""",
                (organization_id, since),
            ).fetchall()
        values = [row["active_sessions"] for row in rows][exclude_last:]
        if not values:
            return None
        return sum(values) / len(values)

    def list_recent(self, organization_id: str | None = None, limit: int = 100) -> list[dict]:
        current_organization_id = organization_id or get_current_organization()
        safe_limit = max(1, min(limit, 500))
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT * FROM network_metrics WHERE organization_id = ?
                ORDER BY recorded_at DESC LIMIT ?""",
                (current_organization_id, safe_limit),
            ).fetchall()
        return [dict(row) for row in rows]


network_metrics_store = NetworkMetricsStore(get_settings().database_url)
