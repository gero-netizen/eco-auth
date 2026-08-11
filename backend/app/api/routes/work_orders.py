from urllib.parse import parse_qs
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.api.routes.technician_auth import require_technician
from app.api.routes.central_auth import require_central_roles
from app.core.config import get_settings
from app.core.customer_location_store import customer_location_store
from app.core.sync_store import SyncOperationStore
from app.core.tenant_context import get_current_organization
from app.domain.models import WorkOrder
from app.integrations.mkauth.client import simulated_mkauth_gateway

router = APIRouter(prefix="/work-orders", tags=["work-orders"])
_change_store = SyncOperationStore(get_settings().database_url)


class CreateWorkOrderRequest(BaseModel):
    customer_name: str = Field(min_length=3, max_length=100)
    address: str = Field(min_length=3, max_length=200)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


async def create_simulated_work_order(
    customer_name: str,
    address: str,
    latitude: float | None = None,
    longitude: float | None = None,
    technician_id: str = "bench-technician",
    priority: str = "normal",
    scheduled_at: datetime | None = None,
    external_customer_id: str | None = None,
    external_ticket_id: str | None = None,
    organization_id: str | None = None,
) -> WorkOrder:
    if latitude is None and longitude is None and external_customer_id:
        confirmed = customer_location_store.get(
            organization_id or get_current_organization(), external_customer_id
        )
        if confirmed:
            latitude, longitude = confirmed["latitude"], confirmed["longitude"]
    order = await simulated_mkauth_gateway.create_work_order(
        customer_name.strip(),
        address.strip(),
        latitude,
        longitude,
        technician_id,
        priority,
        scheduled_at,
        external_customer_id,
        external_ticket_id,
    )
    _change_store.append_change(
        {
            "entity_type": "work_order",
            "entity_id": order.id,
            "kind": "upsert",
            "payload": order.model_dump(mode="json"),
        }
    )
    return order


@router.get("", response_model=list[WorkOrder], dependencies=[Depends(require_technician)])
async def list_work_orders(
    technician: dict = Depends(require_technician),
) -> list[WorkOrder]:
    orders = await simulated_mkauth_gateway.list_work_orders(technician["id"])
    return [
        order
        for order in orders
        if order.archived_at is None and order.deleted_at is None
    ]


@router.post("", response_model=WorkOrder, status_code=201, dependencies=[Depends(require_technician)])
async def create_work_order(request: CreateWorkOrderRequest) -> WorkOrder:
    return await create_simulated_work_order(
        request.customer_name,
        request.address,
        request.latitude,
        request.longitude,
    )


@router.post("/from-central", include_in_schema=False)
async def create_work_order_from_central(
    request: Request,
    session: dict = Depends(
        require_central_roles("owner", "admin", "attendant")
    ),
) -> RedirectResponse:
    fields = parse_qs((await request.body()).decode("utf-8"))
    customer_name = fields.get("customer_name", [""])[0]
    address = fields.get("address", [""])[0]
    latitude_text = fields.get("latitude", [""])[0].strip()
    longitude_text = fields.get("longitude", [""])[0].strip()
    technician_id = fields.get("technician_id", ["bench-technician"])[0]
    priority = fields.get("priority", ["normal"])[0]
    scheduled_text = fields.get("scheduled_at", [""])[0].strip()
    external_customer_id = fields.get("external_customer_id", [""])[0].strip() or None
    external_ticket_id = fields.get("external_ticket_id", [""])[0].strip() or None
    if not 3 <= len(customer_name.strip()) <= 100:
        raise HTTPException(422, "invalid_customer_name")
    if not 3 <= len(address.strip()) <= 200:
        raise HTTPException(422, "invalid_address")
    if priority not in {"low", "normal", "high", "urgent"}:
        raise HTTPException(422, "invalid_priority")
    try:
        scheduled_at = (
            datetime.fromisoformat(scheduled_text).replace(
                tzinfo=timezone(timedelta(hours=-3))
            )
            if scheduled_text
            else None
        )
    except ValueError as error:
        raise HTTPException(422, "invalid_schedule") from error
    try:
        latitude = float(latitude_text) if latitude_text else None
        longitude = float(longitude_text) if longitude_text else None
    except ValueError as error:
        raise HTTPException(422, "invalid_coordinates") from error
    if (latitude is None) != (longitude is None):
        raise HTTPException(422, "latitude_and_longitude_are_required_together")
    if latitude is not None and not (-90 <= latitude <= 90):
        raise HTTPException(422, "invalid_latitude")
    if longitude is not None and not (-180 <= longitude <= 180):
        raise HTTPException(422, "invalid_longitude")
    await create_simulated_work_order(
        customer_name,
        address,
        latitude,
        longitude,
        technician_id,
        priority,
        scheduled_at,
        external_customer_id,
        external_ticket_id,
    )
    return RedirectResponse("/central", status_code=303)
