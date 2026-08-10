import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings
from app.domain.models import InventoryItem


class SimulatedInventoryGateway:
    def __init__(self) -> None:
        self._database_path = Path(
            get_settings().database_url.removeprefix("sqlite:///")
        )
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS simulated_inventory (
                    id TEXT PRIMARY KEY,
                    sku TEXT NOT NULL,
                    description TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    unit TEXT NOT NULL,
                    serial_number TEXT,
                    version INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS simulated_inventory_movements (
                    id TEXT PRIMARY KEY,
                    item_id TEXT NOT NULL,
                    work_order_id TEXT,
                    kind TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            for item in self._seed_items():
                connection.execute(
                    """
                    INSERT OR IGNORE INTO simulated_inventory (
                        id, sku, description, quantity, unit,
                        serial_number, version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._values(item),
                )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    @staticmethod
    def _seed_items() -> list[InventoryItem]:
        return [
            InventoryItem(
                id="drop-cable",
                sku="CABO-DROP-01",
                description="Cabo drop óptico",
                quantity=100.0,
                unit="m",
            ),
            InventoryItem(
                id="fast-connector",
                sku="CONECTOR-FAST",
                description="Conector de campo",
                quantity=20.0,
                unit="un",
            ),
            InventoryItem(
                id="router-bench-01",
                sku="ROTEADOR-AC",
                description="Roteador Wi-Fi de bancada",
                quantity=1.0,
                unit="un",
                serial_number="RTR-BENCH-001",
            ),
        ]

    @staticmethod
    def _values(item: InventoryItem) -> tuple:
        return (
            item.id,
            item.sku,
            item.description,
            item.quantity,
            item.unit,
            item.serial_number,
            item.version,
        )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> InventoryItem:
        return InventoryItem(
            id=row["id"],
            sku=row["sku"],
            description=row["description"],
            quantity=row["quantity"],
            unit=row["unit"],
            serial_number=row["serial_number"],
            version=row["version"],
        )

    async def list_items(self, technician_id: str) -> list[InventoryItem]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM simulated_inventory ORDER BY description"
            ).fetchall()
        return [self._from_row(row) for row in rows]

    async def _item(self, item_id: str) -> InventoryItem:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM simulated_inventory WHERE id = ?", (item_id,)
            ).fetchone()
        if row is None:
            raise KeyError("inventory_item_not_found")
        return self._from_row(row)

    async def consume(
        self,
        item_id: str,
        quantity: float,
        base_version: int | None,
        movement_id: str | None = None,
        work_order_id: str | None = None,
    ) -> InventoryItem:
        item = await self._item(item_id)
        if base_version is not None and base_version != item.version:
            raise ValueError("version_conflict")
        if quantity <= 0 or quantity > item.quantity:
            raise ValueError("insufficient_stock")
        updated = await self._set_quantity(item, item.quantity - quantity)
        self.record_movement(
            movement_id or str(uuid4()),
            item_id,
            work_order_id,
            "consume",
            quantity,
            "technician",
        )
        return updated

    async def restock(self, item_id: str, quantity: float) -> InventoryItem:
        if quantity <= 0:
            raise ValueError("invalid_restock_quantity")
        item = await self._item(item_id)
        updated = await self._set_quantity(item, item.quantity + quantity)
        self.record_movement(
            str(uuid4()), item_id, None, "restock", quantity, "central"
        )
        return updated

    def record_movement(
        self,
        movement_id: str,
        item_id: str,
        work_order_id: str | None,
        kind: str,
        quantity: float,
        source: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO simulated_inventory_movements (
                    id, item_id, work_order_id, kind, quantity, source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    movement_id,
                    item_id,
                    work_order_id,
                    kind,
                    quantity,
                    source,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def list_movements(self, work_order_id: str | None = None) -> list[dict]:
        query = """
            SELECT movement.*, item.description, item.unit
            FROM simulated_inventory_movements movement
            JOIN simulated_inventory item ON item.id = movement.item_id
        """
        parameters: tuple = ()
        if work_order_id is not None:
            query += " WHERE movement.work_order_id = ?"
            parameters = (work_order_id,)
        query += " ORDER BY movement.created_at DESC"
        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [dict(row) for row in rows]

    async def _set_quantity(
        self, item: InventoryItem, quantity: float
    ) -> InventoryItem:
        updated = item.model_copy(
            update={"quantity": quantity, "version": item.version + 1}
        )
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE simulated_inventory
                SET quantity = ?, version = ? WHERE id = ?
                """,
                (updated.quantity, updated.version, updated.id),
            )
        return updated


simulated_inventory_gateway = SimulatedInventoryGateway()
