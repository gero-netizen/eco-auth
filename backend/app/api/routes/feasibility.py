from hashlib import sha256

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.routes.technician_auth import require_technician

router = APIRouter(
    prefix="/feasibility",
    tags=["ftth-feasibility-simulator"],
    dependencies=[Depends(require_technician)],
)


class FeasibilityRequest(BaseModel):
    work_order_id: str
    address: str


class FeasibilityResult(BaseModel):
    feasible: bool
    cto_code: str
    distance_meters: int
    total_ports: int
    available_ports: int
    message: str
    simulated: bool = True


@router.post("/check", response_model=FeasibilityResult)
async def check_feasibility(request: FeasibilityRequest) -> FeasibilityResult:
    address = request.address.strip()
    if not request.work_order_id.strip() or not address:
        raise HTTPException(422, "work_order_id and address are required")
    seed = int(sha256(address.lower().encode()).hexdigest()[:4], 16)
    total_ports = 8 if seed % 2 == 0 else 16
    available_ports = 1 + seed % min(5, total_ports)
    return FeasibilityResult(
        feasible=available_ports > 0,
        cto_code=f"CTO-BENCH-{(seed % 20) + 1:02d}",
        distance_meters=60 + seed % 241,
        total_ports=total_ports,
        available_ports=available_ports,
        message="Porta disponível para instalação simulada",
    )
