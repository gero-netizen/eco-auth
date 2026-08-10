from hashlib import sha256

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.routes.technician_auth import require_technician

router = APIRouter(prefix="/access", tags=["pppoe-simulator"], dependencies=[Depends(require_technician)])


class PppoeTestRequest(BaseModel):
    work_order_id: str
    username: str


class PppoeTestResult(BaseModel):
    username: str
    status: str
    assigned_ip: str
    latency_ms: int
    download_mbps: float
    upload_mbps: float
    simulated: bool = True


@router.post("/pppoe/test", response_model=PppoeTestResult)
async def test_pppoe(request: PppoeTestRequest) -> PppoeTestResult:
    username = request.username.strip().lower()
    if not request.work_order_id.strip() or not username:
        raise HTTPException(422, "work_order_id and username are required")
    seed = int(sha256(username.encode()).hexdigest()[:4], 16)
    return PppoeTestResult(
        username=username,
        status="authenticated",
        assigned_ip=f"10.20.{seed % 200}.{(seed % 250) + 1}",
        latency_ms=5 + seed % 16,
        download_mbps=480 + seed % 41,
        upload_mbps=230 + seed % 31,
    )
