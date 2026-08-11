from fastapi import APIRouter, Depends, HTTPException

from app.api.routes.technician_auth import require_technician
from app.core.config import get_settings
from app.core.customer_location_store import customer_location_store
from app.core.sync_store import SyncOperationStore
from app.core.work_order_history_store import work_order_history_store
from app.domain.models import (
    OperationResult,
    SyncPushRequest,
    SyncPushResponse,
    WorkOrderStatus,
)
from app.integrations.mkauth.client import simulated_mkauth_gateway
from app.integrations.mkauth.inventory import simulated_inventory_gateway

router = APIRouter(
    prefix="/sync",
    tags=["sync"],
    dependencies=[Depends(require_technician)],
)
_operation_store = SyncOperationStore(get_settings().database_url)

# Estados que representam o encerramento de uma visita presencial. Nesses
# momentos, se o técnico capturou GPS, a localização do cliente é atualizada
# para facilitar a próxima visita.
_ON_SITE_CLOSING_STATUSES = {WorkOrderStatus.COMPLETED, WorkOrderStatus.NOT_COMPLETED}


@router.post("/push", response_model=SyncPushResponse)
async def push(
    request: SyncPushRequest,
    technician: dict = Depends(require_technician),
) -> SyncPushResponse:
    results: list[OperationResult] = []
    for operation in request.operations:
        key = str(operation.operation_id)
        result = _operation_store.get(key, technician["organization_id"])
        if result is None:
            change = None
            try:
                if operation.entity_type == "work_order" and operation.kind == "transition":
                    note = operation.payload.get("note")
                    latitude = operation.payload.get("latitude")
                    longitude = operation.payload.get("longitude")
                    to_status = WorkOrderStatus(operation.payload["to_status"])
                    updated, from_status = await simulated_mkauth_gateway.transition_work_order(
                        operation.entity_id,
                        to_status,
                        operation.base_version,
                        technician["organization_id"],
                        latitude=latitude,
                        longitude=longitude,
                    )
                    work_order_history_store.record(
                        technician["organization_id"],
                        updated.id,
                        to_status.value,
                        from_status=from_status.value,
                        note=note,
                        latitude=latitude,
                        longitude=longitude,
                        technician_id=technician["id"],
                    )
                    if (
                        to_status in _ON_SITE_CLOSING_STATUSES
                        and latitude is not None
                        and longitude is not None
                        and updated.external_customer_id
                    ):
                        customer_location_store.confirm(
                            technician["organization_id"],
                            updated.external_customer_id,
                            latitude,
                            longitude,
                            source_work_order_id=updated.id,
                            confirmed_by_technician_id=technician["id"],
                        )
                    server_version = updated.version
                    change = {
                        "entity_type": "work_order",
                        "entity_id": updated.id,
                        "kind": "upsert",
                        "payload": updated.model_dump(mode="json"),
                    }
                elif (
                    operation.entity_type == "inventory_movement"
                    and operation.kind == "consume"
                ):
                    updated_item = await simulated_inventory_gateway.consume(
                        operation.payload["item_id"],
                        float(operation.payload["quantity"]),
                        operation.base_version,
                        str(operation.operation_id),
                        operation.payload.get("work_order_id"),
                        technician["organization_id"],
                    )
                    server_version = updated_item.version
                    change = {
                        "entity_type": "inventory_item",
                        "entity_id": updated_item.id,
                        "kind": "upsert",
                        "payload": updated_item.model_dump(mode="json"),
                    }
                else:
                    server_version = (operation.base_version or 0) + 1
                result = OperationResult(
                    operation_id=operation.operation_id,
                    status="accepted",
                    server_version=server_version,
                )
            except (KeyError, ValueError) as error:
                reason = str(error)
                result = OperationResult(
                    operation_id=operation.operation_id,
                    status="conflict" if "version_conflict" in reason else "rejected",
                    reason=reason,
                )
            result = _operation_store.save(
                result,
                change if result.status == "accepted" else None,
                technician["organization_id"],
            )
        else:
            result = result.model_copy(update={"status": "duplicate"})
        results.append(result)
    return SyncPushResponse(results=results)


@router.get("/pull")
async def pull(
    cursor: str | None = None,
    technician: dict = Depends(require_technician),
) -> dict:
    try:
        parsed_cursor = int(cursor) if cursor else 0
        if parsed_cursor < 0:
            raise ValueError
    except ValueError as error:
        raise HTTPException(status_code=422, detail="invalid_sync_cursor") from error
    changes, next_cursor = _operation_store.changes_after(
        parsed_cursor, organization_id=technician["organization_id"]
    )
    return {"changes": changes, "next_cursor": str(next_cursor)}
