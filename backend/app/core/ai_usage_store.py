import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import get_settings
from app.core.tenant_context import get_current_organization


class AiUsageStore:
    """Contagem de uso de IA real por provedor e por mês (competência UTC)."""

    def __init__(self, database_url: str) -> None:
        prefix = "sqlite:///"
        if not database_url.startswith(prefix):
            raise ValueError("Only sqlite:/// database URLs are supported")
        self._path = Path(database_url.removeprefix(prefix))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_usage_monthly (
                    organization_id TEXT NOT NULL,
                    year_month TEXT NOT NULL,
                    requests_used INTEGER NOT NULL DEFAULT 0,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (organization_id, year_month)
                )
                """
            )

    @staticmethod
    def _current_year_month() -> str:
        return datetime.now(UTC).strftime("%Y-%m")

    def get_usage(self, organization_id: str | None = None) -> dict:
        current_organization_id = organization_id or get_current_organization()
        year_month = self._current_year_month()
        with self._connect() as connection:
            row = connection.execute(
                """SELECT * FROM ai_usage_monthly
                WHERE organization_id = ? AND year_month = ?""",
                (current_organization_id, year_month),
            ).fetchone()
        if row is None:
            return {
                "organization_id": current_organization_id,
                "year_month": year_month,
                "requests_used": 0,
                "input_tokens": 0,
                "output_tokens": 0,
            }
        return dict(row)

    def has_budget(self, monthly_request_limit: int, organization_id: str | None = None) -> bool:
        if monthly_request_limit <= 0:
            return False
        usage = self.get_usage(organization_id)
        return usage["requests_used"] < monthly_request_limit

    def record_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        organization_id: str | None = None,
    ) -> dict:
        current_organization_id = organization_id or get_current_organization()
        year_month = self._current_year_month()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO ai_usage_monthly (
                    organization_id, year_month, requests_used, input_tokens, output_tokens
                ) VALUES (?, ?, 1, ?, ?)
                ON CONFLICT(organization_id, year_month) DO UPDATE SET
                    requests_used = requests_used + 1,
                    input_tokens = input_tokens + excluded.input_tokens,
                    output_tokens = output_tokens + excluded.output_tokens
                """,
                (current_organization_id, year_month, input_tokens, output_tokens),
            )
        return self.get_usage(current_organization_id)


ai_usage_store = AiUsageStore(get_settings().database_url)
