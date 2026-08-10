import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.config import get_settings


SAAS_PLANS = {
    "starter": {
        "code": "starter",
        "name": "Essencial",
        "monthly_price": 149.90,
        "max_central_users": 3,
        "max_technicians": 2,
    },
    "professional": {
        "code": "professional",
        "name": "Profissional",
        "monthly_price": 299.90,
        "max_central_users": 10,
        "max_technicians": 10,
    },
    "scale": {
        "code": "scale",
        "name": "Escala",
        "monthly_price": 599.90,
        "max_central_users": 50,
        "max_technicians": 50,
    },
}


class SubscriptionStore:
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
                CREATE TABLE IF NOT EXISTS organization_subscriptions (
                    organization_id TEXT PRIMARY KEY,
                    plan_code TEXT NOT NULL,
                    status TEXT NOT NULL,
                    trial_ends_at TEXT,
                    current_period_ends_at TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def get_or_create(self, organization_id: str) -> dict:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT organization_id, plan_code, status, trial_ends_at,
                       current_period_ends_at, created_at, updated_at
                FROM organization_subscriptions WHERE organization_id = ?
                """,
                (organization_id,),
            ).fetchone()
            if row is None:
                trial_ends_at = (
                    datetime.now(timezone.utc) + timedelta(days=14)
                ).isoformat()
                connection.execute(
                    """
                    INSERT INTO organization_subscriptions (
                        organization_id, plan_code, status, trial_ends_at
                    ) VALUES (?, 'professional', 'trialing', ?)
                    """,
                    (organization_id, trial_ends_at),
                )
                row = connection.execute(
                    """
                    SELECT organization_id, plan_code, status, trial_ends_at,
                           current_period_ends_at, created_at, updated_at
                    FROM organization_subscriptions WHERE organization_id = ?
                    """,
                    (organization_id,),
                ).fetchone()
        return self._with_plan(dict(row))

    def simulate_plan_change(self, organization_id: str, plan_code: str) -> dict:
        if plan_code not in SAAS_PLANS:
            raise ValueError("invalid_saas_plan")
        self.get_or_create(organization_id)
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE organization_subscriptions
                SET plan_code = ?, updated_at = CURRENT_TIMESTAMP
                WHERE organization_id = ?
                """,
                (plan_code, organization_id),
            )
        return self.get_or_create(organization_id)

    def ensure_capacity(
        self, organization_id: str, resource: str, current_count: int
    ) -> None:
        subscription = self.get_or_create(organization_id)
        if subscription["status"] not in {"trialing", "active"}:
            raise ValueError("saas_subscription_inactive")
        limit_key = {
            "central_users": "max_central_users",
            "technicians": "max_technicians",
        }.get(resource)
        if limit_key is None:
            raise ValueError("invalid_saas_resource")
        if current_count >= subscription["plan"][limit_key]:
            raise ValueError(f"saas_{resource}_limit_reached")

    @staticmethod
    def _with_plan(subscription: dict) -> dict:
        if (
            subscription["status"] == "trialing"
            and subscription["trial_ends_at"]
            and datetime.fromisoformat(subscription["trial_ends_at"])
            < datetime.now(timezone.utc)
        ):
            subscription["status"] = "trial_expired"
        return {**subscription, "plan": dict(SAAS_PLANS[subscription["plan_code"]])}


subscription_store = SubscriptionStore(get_settings().database_url)
