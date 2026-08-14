from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class WorkOrderStatus(StrEnum):
    ASSIGNED = "assigned"
    TRAVELING = "traveling"
    ARRIVED = "arrived"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    NOT_COMPLETED = "not_completed"


class WorkOrder(BaseModel):
    id: str
    code: str
    customer_name: str
    address: str
    external_customer_id: str | None = None
    external_ticket_id: str | None = None
    external_ticket_closed_at: datetime | None = None
    archived_at: datetime | None = None
    deleted_at: datetime | None = None
    deletion_reason: str | None = None
    status: WorkOrderStatus = WorkOrderStatus.ASSIGNED
    latitude: float | None = None
    longitude: float | None = None
    technician_id: str = "bench-technician"
    priority: str = "normal"
    scheduled_at: datetime | None = None
    version: int = 1
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SyncOperation(BaseModel):
    operation_id: UUID
    entity_type: str
    entity_id: str
    kind: str
    base_version: int | None = None
    occurred_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class SyncPushRequest(BaseModel):
    device_id: UUID
    operations: list[SyncOperation] = Field(max_length=500)


class OperationResult(BaseModel):
    operation_id: UUID
    status: str
    server_version: int | None = None
    reason: str | None = None


class SyncPushResponse(BaseModel):
    results: list[OperationResult]


class InventoryItem(BaseModel):
    id: str
    sku: str
    description: str
    quantity: float
    unit: str
    serial_number: str | None = None
    version: int = 1
    technician_id: str | None = None
