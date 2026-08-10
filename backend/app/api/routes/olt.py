from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pydantic import Field
from uuid import UUID, uuid4

from app.api.routes.technician_auth import require_technician
from app.core.config import get_settings
from app.core.provisioning_store import ProvisioningStore
from app.core.tenant_context import get_current_organization
from app.integrations.olt.factory import build_olt_gateway

router = APIRouter(
    prefix="/olt",
    tags=["olt-simulator"],
    dependencies=[Depends(require_technician)],
)
_gateways = {}
provisioning_store = ProvisioningStore(get_settings().database_url)


def _gateway(organization_id: str | None = None):
    current_organization_id = organization_id or get_current_organization()
    if current_organization_id not in _gateways:
        _gateways[current_organization_id] = build_olt_gateway(get_settings())
    return _gateways[current_organization_id]


class ProvisionRequest(BaseModel):
    serial: str
    profile: str
    work_order_id: str = "bench-work-order"
    operation_id: UUID = Field(default_factory=uuid4)


@router.get("/onus")
async def discover() -> list[dict]:
    return [asdict(item) for item in await _gateway().discover()]


@router.get("/provisioning")
async def provisioning_history(work_order_id: str) -> list[dict]:
    if not work_order_id.strip():
        raise HTTPException(422, "work_order_id is required")
    return provisioning_store.list_for_work_order(work_order_id)


@router.post("/onus/provision")
async def provision(request: ProvisionRequest) -> dict:
    if (
        not request.serial.strip()
        or not request.profile.strip()
        or not request.work_order_id.strip()
    ):
        raise HTTPException(422, "serial, profile and work_order_id are required")
    operation_id = str(request.operation_id)
    previous = provisioning_store.get(operation_id)
    if previous is not None:
        return {**previous, "duplicate": True}
    result = {
        **asdict(await _gateway().provision(request.serial, request.profile)),
        "operation_id": operation_id,
        "work_order_id": request.work_order_id,
        "duplicate": False,
    }
    return provisioning_store.save(
        operation_id,
        request.work_order_id,
        request.serial.upper(),
        request.profile,
        result,
    )
