from abc import ABC, abstractmethod
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import get_settings
from app.domain.models import WorkOrder, WorkOrderStatus


class MkAuthGateway(ABC):
    @abstractmethod
    async def list_work_orders(self, technician_id: str | None) -> list[WorkOrder]: ...


class SimulatedMkAuthGateway(MkAuthGateway):
    def __init__(self) -> None:
        self._database_path = Path(
            get_settings().database_url.removeprefix("sqlite:///")
        )
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS simulated_work_orders (
                    id TEXT PRIMARY KEY,
                    code TEXT NOT NULL UNIQUE,
                    customer_name TEXT NOT NULL,
                    address TEXT NOT NULL,
                    status TEXT NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    version INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(simulated_work_orders)")
            }
            if "technician_id" not in columns:
                connection.execute(
                    "ALTER TABLE simulated_work_orders ADD COLUMN technician_id TEXT NOT NULL DEFAULT 'bench-technician'"
                )
            if "priority" not in columns:
                connection.execute(
                    "ALTER TABLE simulated_work_orders ADD COLUMN priority TEXT NOT NULL DEFAULT 'normal'"
                )
            if "scheduled_at" not in columns:
                connection.execute(
                    "ALTER TABLE simulated_work_orders ADD COLUMN scheduled_at TEXT"
                )
            if "external_customer_id" not in columns:
                connection.execute(
                    "ALTER TABLE simulated_work_orders ADD COLUMN external_customer_id TEXT"
                )
            if "external_ticket_id" not in columns:
                connection.execute(
                    "ALTER TABLE simulated_work_orders ADD COLUMN external_ticket_id TEXT"
                )
            if "external_ticket_closed_at" not in columns:
                connection.execute(
                    "ALTER TABLE simulated_work_orders ADD COLUMN external_ticket_closed_at TEXT"
                )
            if "archived_at" not in columns:
                connection.execute(
                    "ALTER TABLE simulated_work_orders ADD COLUMN archived_at TEXT"
                )
            if "deleted_at" not in columns:
                connection.execute(
                    "ALTER TABLE simulated_work_orders ADD COLUMN deleted_at TEXT"
                )
            if "deletion_reason" not in columns:
                connection.execute(
                    "ALTER TABLE simulated_work_orders ADD COLUMN deletion_reason TEXT"
                )
            order = WorkOrder(
                id="sim-os-1",
                code="OS-0001",
                customer_name="Cliente de Bancada",
                address="Ambiente de testes",
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO simulated_work_orders (
                    id, code, customer_name, address, status, latitude,
                    longitude, version, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._values(order),
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    @staticmethod
    def _values(order: WorkOrder) -> tuple:
        return (
            order.id,
            order.code,
            order.customer_name,
            order.address,
            order.status.value,
            order.latitude,
            order.longitude,
            order.version,
            order.updated_at.isoformat(),
        )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> WorkOrder:
        return WorkOrder(
            id=row["id"],
            code=row["code"],
            customer_name=row["customer_name"],
            address=row["address"],
            external_customer_id=row["external_customer_id"],
            external_ticket_id=row["external_ticket_id"],
            external_ticket_closed_at=(
                datetime.fromisoformat(row["external_ticket_closed_at"])
                if row["external_ticket_closed_at"]
                else None
            ),
            archived_at=(
                datetime.fromisoformat(row["archived_at"])
                if row["archived_at"]
                else None
            ),
            deleted_at=(
                datetime.fromisoformat(row["deleted_at"])
                if row["deleted_at"]
                else None
            ),
            deletion_reason=row["deletion_reason"],
            status=WorkOrderStatus(row["status"]),
            latitude=row["latitude"],
            longitude=row["longitude"],
            technician_id=row["technician_id"],
            priority=row["priority"],
            scheduled_at=(
                datetime.fromisoformat(row["scheduled_at"])
                if row["scheduled_at"]
                else None
            ),
            version=row["version"],
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    async def list_work_orders(self, technician_id: str | None) -> list[WorkOrder]:
        with self._connect() as connection:
            if technician_id is None:
                rows = connection.execute(
                    "SELECT * FROM simulated_work_orders ORDER BY code"
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM simulated_work_orders WHERE technician_id = ? ORDER BY code",
                    (technician_id,),
                ).fetchall()
        return [self._from_row(row) for row in rows]

    async def create_work_order(
        self,
        customer_name: str,
        address: str,
        latitude: float | None = None,
        longitude: float | None = None,
        technician_id: str = "bench-technician",
        priority: str = "normal",
        scheduled_at: datetime | None = None,
        external_customer_id: str | None = None,
        external_ticket_id: str | None = None,
    ) -> WorkOrder:
        with self._connect() as connection:
            sequence = connection.execute(
                "SELECT COALESCE(MAX(CAST(SUBSTR(code, 4) AS INTEGER)), 0) + 1 FROM simulated_work_orders"
            ).fetchone()[0]
            order = WorkOrder(
                id=f"sim-os-{sequence}",
                code=f"OS-{sequence:04d}",
                customer_name=customer_name,
                address=address,
                external_customer_id=external_customer_id,
                external_ticket_id=external_ticket_id,
                latitude=latitude,
                longitude=longitude,
                technician_id=technician_id,
                priority=priority,
                scheduled_at=scheduled_at,
            )
            connection.execute(
                """
                INSERT INTO simulated_work_orders (
                    id, code, customer_name, address, status, latitude,
                    longitude, version, updated_at, technician_id, priority,
                    scheduled_at, external_customer_id, external_ticket_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    *self._values(order),
                    technician_id,
                    priority,
                    scheduled_at.isoformat() if scheduled_at else None,
                    external_customer_id,
                    external_ticket_id,
                ),
            )
        return order

    async def transition_work_order(
        self,
        work_order_id: str,
        to_status: WorkOrderStatus,
        base_version: int | None,
    ) -> WorkOrder:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM simulated_work_orders WHERE id = ?",
                (work_order_id,),
            ).fetchone()
        if row is None:
            raise KeyError("work_order_not_found")
        current = self._from_row(row)
        if base_version is not None and base_version != current.version:
            raise ValueError("version_conflict")
        updated = current.model_copy(
            update={
                "status": to_status,
                "version": current.version + 1,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE simulated_work_orders
                SET status = ?, latitude = ?, longitude = ?, version = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    updated.status.value,
                    updated.latitude,
                    updated.longitude,
                    updated.version,
                    updated.updated_at.isoformat(),
                    updated.id,
                ),
            )
        return updated

    async def assign_work_order(
        self, work_order_id: str, technician_id: str
    ) -> WorkOrder:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM simulated_work_orders WHERE id = ?",
                (work_order_id,),
            ).fetchone()
            if row is None:
                raise KeyError("work_order_not_found")
            current = self._from_row(row)
            if current.status in {
                WorkOrderStatus.COMPLETED,
                WorkOrderStatus.NOT_COMPLETED,
            }:
                raise ValueError("finished_work_order_cannot_be_transferred")
            updated = current.model_copy(
                update={
                    "technician_id": technician_id,
                    "version": current.version + 1,
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            connection.execute(
                "UPDATE simulated_work_orders SET technician_id = ?, version = ?, updated_at = ? WHERE id = ?",
                (
                    technician_id,
                    updated.version,
                    updated.updated_at.isoformat(),
                    work_order_id,
                ),
            )
        return updated

    async def update_work_order_planning(
        self,
        work_order_id: str,
        priority: str,
        scheduled_at: datetime | None,
    ) -> WorkOrder:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM simulated_work_orders WHERE id = ?",
                (work_order_id,),
            ).fetchone()
            if row is None:
                raise KeyError("work_order_not_found")
            current = self._from_row(row)
            if current.status in {
                WorkOrderStatus.COMPLETED,
                WorkOrderStatus.NOT_COMPLETED,
            }:
                raise ValueError("finished_work_order_cannot_be_rescheduled")
            updated = current.model_copy(
                update={
                    "priority": priority,
                    "scheduled_at": scheduled_at,
                    "version": current.version + 1,
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            connection.execute(
                """
                UPDATE simulated_work_orders
                SET priority = ?, scheduled_at = ?, version = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    priority,
                    scheduled_at.isoformat() if scheduled_at else None,
                    updated.version,
                    updated.updated_at.isoformat(),
                    work_order_id,
                ),
            )
        return updated

    async def mark_external_ticket_closed(self, work_order_id: str) -> WorkOrder:
        closed_at = datetime.now(timezone.utc)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM simulated_work_orders WHERE id = ?",
                (work_order_id,),
            ).fetchone()
            if row is None:
                raise KeyError("work_order_not_found")
            current = self._from_row(row)
            if current.external_ticket_closed_at is not None:
                raise ValueError("external_ticket_already_closed")
            connection.execute(
                "UPDATE simulated_work_orders SET external_ticket_closed_at = ? WHERE id = ?",
                (closed_at.isoformat(), work_order_id),
            )
        return current.model_copy(update={"external_ticket_closed_at": closed_at})

    async def set_work_order_archived(
        self, work_order_id: str, archived: bool
    ) -> WorkOrder:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM simulated_work_orders WHERE id = ?",
                (work_order_id,),
            ).fetchone()
            if row is None:
                raise KeyError("work_order_not_found")
            current = self._from_row(row)
            if archived:
                if current.status not in {
                    WorkOrderStatus.COMPLETED,
                    WorkOrderStatus.NOT_COMPLETED,
                }:
                    raise ValueError("only_finished_work_orders_can_be_archived")
                if (
                    current.external_ticket_id
                    and current.external_ticket_closed_at is None
                ):
                    raise ValueError("linked_mkauth_ticket_must_be_closed_first")
            archived_at = datetime.now(timezone.utc) if archived else None
            connection.execute(
                "UPDATE simulated_work_orders SET archived_at = ? WHERE id = ?",
                (archived_at.isoformat() if archived_at else None, work_order_id),
            )
        return current.model_copy(update={"archived_at": archived_at})

    async def delete_unstarted_work_order(
        self, work_order_id: str, reason: str
    ) -> WorkOrder:
        deleted_at = datetime.now(timezone.utc)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM simulated_work_orders WHERE id = ?",
                (work_order_id,),
            ).fetchone()
            if row is None:
                raise KeyError("work_order_not_found")
            current = self._from_row(row)
            if current.deleted_at is not None:
                raise ValueError("work_order_already_deleted")
            if current.status is not WorkOrderStatus.ASSIGNED:
                raise ValueError("only_unstarted_work_orders_can_be_deleted")
            connection.execute(
                "UPDATE simulated_work_orders SET deleted_at = ?, deletion_reason = ? WHERE id = ?",
                (deleted_at.isoformat(), reason, work_order_id),
            )
        return current.model_copy(
            update={"deleted_at": deleted_at, "deletion_reason": reason}
        )


simulated_mkauth_gateway = SimulatedMkAuthGateway()
