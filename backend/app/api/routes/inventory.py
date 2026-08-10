from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.api.routes.technician_auth import require_technician
from app.api.routes.central_auth import require_central_roles
from app.core.config import get_settings
from app.core.sync_store import SyncOperationStore
from app.domain.models import InventoryItem
from app.integrations.mkauth.inventory import simulated_inventory_gateway

router = APIRouter(prefix="/inventory", tags=["inventory"])
_change_store = SyncOperationStore(get_settings().database_url)


class RestockRequest(BaseModel):
    quantity: float = Field(gt=0, le=10000)


async def restock_item(
    item_id: str, quantity: float, organization_id: str
) -> InventoryItem:
    try:
        item = await simulated_inventory_gateway.restock(
            item_id, quantity, organization_id
        )
    except (KeyError, ValueError) as error:
        raise HTTPException(422, str(error)) from error
    _change_store.append_change(
        {
            "entity_type": "inventory_item",
            "entity_id": item.id,
            "kind": "upsert",
            "payload": item.model_dump(mode="json"),
        },
        organization_id,
    )
    return item


@router.get("", response_model=list[InventoryItem], dependencies=[Depends(require_technician)])
async def list_inventory(
    technician_id: str = "bench-technician",
    technician: dict = Depends(require_technician),
) -> list[InventoryItem]:
    return await simulated_inventory_gateway.list_items(
        technician_id, technician["organization_id"]
    )


@router.post("/{item_id}/restock", response_model=InventoryItem, dependencies=[Depends(require_technician)])
async def restock_inventory_item(
    item_id: str,
    request: RestockRequest,
    technician: dict = Depends(require_technician),
) -> InventoryItem:
    return await restock_item(
        item_id, request.quantity, technician["organization_id"]
    )


@router.post("/{item_id}/restock-from-central", include_in_schema=False)
async def restock_from_central(
    item_id: str,
    request: Request,
    session: dict = Depends(require_central_roles("owner", "admin")),
) -> RedirectResponse:
    fields = parse_qs((await request.body()).decode("utf-8"))
    try:
        quantity = float(fields.get("quantity", [""])[0])
    except ValueError as error:
        raise HTTPException(422, "invalid_restock_quantity") from error
    await restock_item(item_id, quantity, session["organization"]["id"])
    return RedirectResponse("/central", status_code=303)
