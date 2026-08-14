from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.core import db
from app.core.config import get_settings
from app.core.tenant_context import get_current_organization
from app.domain.models import InventoryItem


class SimulatedInventoryGateway:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or get_settings().database_url
        self._database_path = (
            None
            if db.is_postgres_url(self._database_url)
            else Path(self._database_url.removeprefix("sqlite:///"))
        )
        if self._database_path is not None:
            self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        return db.connect(
            self._database_url, sqlite_path=self._database_path, enable_sqlite_wal=True
        )

    def _initialize(self) -> None:
        with self._connect() as connection:
            inventory_columns = db.get_existing_columns(
                connection, "simulated_inventory", self._database_url
            )
            if inventory_columns and "organization_id" not in inventory_columns:
                connection.execute(
                    "ALTER TABLE simulated_inventory RENAME TO simulated_inventory_legacy"
                )
            movement_columns = db.get_existing_columns(
                connection, "simulated_inventory_movements", self._database_url
            )
            if movement_columns and "organization_id" not in movement_columns:
                connection.execute(
                    "ALTER TABLE simulated_inventory_movements "
                    "RENAME TO simulated_inventory_movements_legacy"
                )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS simulated_inventory (
                    organization_id TEXT NOT NULL,
                    id TEXT NOT NULL,
                    sku TEXT NOT NULL,
                    description TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    unit TEXT NOT NULL,
                    serial_number TEXT,
                    version INTEGER NOT NULL,
                    technician_id TEXT,
                    PRIMARY KEY (organization_id, id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS simulated_inventory_movements (
                    organization_id TEXT NOT NULL,
                    id TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    work_order_id TEXT,
                    kind TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (organization_id, id)
                )
                """
            )
            if inventory_columns and "organization_id" not in inventory_columns:
                connection.execute(
                    """
                    INSERT INTO simulated_inventory (
                        organization_id, id, sku, description, quantity,
                        unit, serial_number, version
                    )
                    SELECT ?, id, sku, description, quantity, unit,
                           serial_number, version
                    FROM simulated_inventory_legacy
                    """,
                    (get_settings().default_organization_id,),
                )
                connection.execute("DROP TABLE simulated_inventory_legacy")
            if movement_columns and "organization_id" not in movement_columns:
                connection.execute(
                    """
                    INSERT INTO simulated_inventory_movements (
                        organization_id, id, item_id, work_order_id, kind,
                        quantity, source, created_at
                    )
                    SELECT ?, id, item_id, work_order_id, kind, quantity,
                           source, created_at
                    FROM simulated_inventory_movements_legacy
                    """,
                    (get_settings().default_organization_id,),
                )
                connection.execute("DROP TABLE simulated_inventory_movements_legacy")
            inventory_current_columns = db.get_existing_columns(
                connection, "simulated_inventory", self._database_url
            )
            if "technician_id" not in inventory_current_columns:
                connection.execute(
                    "ALTER TABLE simulated_inventory ADD COLUMN technician_id TEXT"
                )
            for item in self._seed_items():
                connection.execute(
                    """
                    INSERT INTO simulated_inventory (
                        organization_id, id, sku, description, quantity,
                        unit, serial_number, version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (organization_id, id) DO NOTHING
                    """,
                    (
                        get_settings().default_organization_id,
                        *self._values(item),
                    ),
                )

    @staticmethod
    def _seed_items() -> list[InventoryItem]:
        return [
            InventoryItem(
                id="drop-cable", sku="CABO-DROP-01",
                description="Cabo drop óptico", quantity=100.0, unit="m",
            ),
            InventoryItem(
                id="fast-connector", sku="CONECTOR-FAST",
                description="Conector de campo", quantity=20.0, unit="un",
            ),
            InventoryItem(
                id="router-bench-01", sku="ROTEADOR-AC",
                description="Roteador Wi-Fi de bancada", quantity=1.0,
                unit="un", serial_number="RTR-BENCH-001",
            ),
        ]

    @staticmethod
    def _values(item: InventoryItem) -> tuple:
        return (
            item.id, item.sku, item.description, item.quantity, item.unit,
            item.serial_number, item.version,
        )

    @staticmethod
    def _from_row(row) -> InventoryItem:
        return InventoryItem(
            id=row["id"], sku=row["sku"], description=row["description"],
            quantity=row["quantity"], unit=row["unit"],
            serial_number=row["serial_number"], version=row["version"],
            technician_id=row["technician_id"],
        )

    async def list_items(
        self, technician_id: str, organization_id: str | None = None
    ) -> list[InventoryItem]:
        """Estoque de um técnico específico — usado pelo app do técnico.
        Cada técnico só vê o material que está com ele."""
        current_organization_id = organization_id or get_current_organization()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM simulated_inventory
                WHERE organization_id = ? AND technician_id = ?
                ORDER BY description
                """,
                (current_organization_id, technician_id),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    async def list_all_items(
        self, organization_id: str | None = None
    ) -> list[InventoryItem]:
        """Todo o estoque da organização, de todos os técnicos e do estoque
        central ainda não distribuído — usado pela Central."""
        current_organization_id = organization_id or get_current_organization()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM simulated_inventory
                WHERE organization_id = ?
                ORDER BY description, technician_id
                """,
                (current_organization_id,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    async def _item(self, item_id: str, organization_id: str) -> InventoryItem:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM simulated_inventory
                WHERE id = ? AND organization_id = ?
                """,
                (item_id, organization_id),
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
        organization_id: str | None = None,
    ) -> InventoryItem:
        current_organization_id = organization_id or get_current_organization()
        item = await self._item(item_id, current_organization_id)
        if base_version is not None and base_version != item.version:
            raise ValueError("version_conflict")
        if quantity <= 0 or quantity > item.quantity:
            raise ValueError("insufficient_stock")
        updated = await self._set_quantity(
            item, item.quantity - quantity, current_organization_id
        )
        self.record_movement(
            movement_id or str(uuid4()), item_id, work_order_id, "consume",
            quantity, "technician", current_organization_id,
        )
        return updated

    async def restock(
        self,
        item_id: str,
        quantity: float,
        organization_id: str | None = None,
        technician_id: str | None = None,
    ) -> InventoryItem:
        """Repõe estoque. Se um técnico for informado, o material é
        distribuído para o estoque dele especificamente — cria uma linha
        própria para esse técnico se ainda não existir uma. Sem técnico,
        volta para o estoque central (ainda não distribuído)."""
        current_organization_id = organization_id or get_current_organization()
        if quantity <= 0:
            raise ValueError("invalid_restock_quantity")
        source_item = await self._item(item_id, current_organization_id)
        target_item = await self._find_or_create_for_technician(
            source_item, technician_id, current_organization_id
        )
        updated = await self._set_quantity(
            target_item, target_item.quantity + quantity, current_organization_id
        )
        self.record_movement(
            str(uuid4()), updated.id, None, "restock", quantity, "central",
            current_organization_id,
        )
        return updated

    async def _find_or_create_for_technician(
        self,
        source_item: InventoryItem,
        technician_id: str | None,
        organization_id: str,
    ) -> InventoryItem:
        if source_item.technician_id == technician_id:
            return source_item
        with self._connect() as connection:
            if technician_id is None:
                row = connection.execute(
                    """SELECT * FROM simulated_inventory
                    WHERE organization_id = ? AND sku = ? AND technician_id IS NULL""",
                    (organization_id, source_item.sku),
                ).fetchone()
            else:
                row = connection.execute(
                    """SELECT * FROM simulated_inventory
                    WHERE organization_id = ? AND sku = ? AND technician_id = ?""",
                    (organization_id, source_item.sku, technician_id),
                ).fetchone()
            if row is not None:
                return self._from_row(row)
            new_item = InventoryItem(
                id=str(uuid4()), sku=source_item.sku,
                description=source_item.description, quantity=0.0,
                unit=source_item.unit, serial_number=None, version=1,
                technician_id=technician_id,
            )
            connection.execute(
                """
                INSERT INTO simulated_inventory (
                    organization_id, id, sku, description, quantity,
                    unit, serial_number, version, technician_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    organization_id, new_item.id, new_item.sku,
                    new_item.description, new_item.quantity, new_item.unit,
                    new_item.serial_number, new_item.version, technician_id,
                ),
            )
            return new_item

    def record_movement(
        self,
        movement_id: str,
        item_id: str,
        work_order_id: str | None,
        kind: str,
        quantity: float,
        source: str,
        organization_id: str | None = None,
    ) -> None:
        current_organization_id = organization_id or get_current_organization()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO simulated_inventory_movements (
                    organization_id, id, item_id, work_order_id, kind,
                    quantity, source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (organization_id, id) DO NOTHING
                """,
                (
                    current_organization_id, movement_id, item_id,
                    work_order_id, kind, quantity, source,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def list_movements(
        self, work_order_id: str | None = None,
        organization_id: str | None = None,
    ) -> list[dict]:
        current_organization_id = organization_id or get_current_organization()
        query = """
            SELECT movement.*, item.description, item.unit
            FROM simulated_inventory_movements movement
            JOIN simulated_inventory item
              ON item.id = movement.item_id
             AND item.organization_id = movement.organization_id
            WHERE movement.organization_id = ?
        """
        parameters: tuple = (current_organization_id,)
        if work_order_id is not None:
            query += " AND movement.work_order_id = ?"
            parameters = (current_organization_id, work_order_id)
        query += " ORDER BY movement.created_at DESC"
        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [dict(row) for row in rows]

    async def _set_quantity(
        self, item: InventoryItem, quantity: float, organization_id: str
    ) -> InventoryItem:
        updated = item.model_copy(
            update={"quantity": quantity, "version": item.version + 1}
        )
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE simulated_inventory SET quantity = ?, version = ?
                WHERE id = ? AND organization_id = ?
                """,
                (updated.quantity, updated.version, updated.id, organization_id),
            )
        return updated


simulated_inventory_gateway = SimulatedInventoryGateway()
