from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.routes.technician_auth import require_technician
from app.core.cto_store import cto_store
from app.core.geo import GeocodingError, geocode_address, haversine_meters

router = APIRouter(
    prefix="/feasibility",
    tags=["ftth-feasibility"],
    dependencies=[Depends(require_technician)],
)

# Raio de atendimento padrão de uma CTO até o cliente, em metros. CTOs mais
# distantes que isso normalmente exigem um lançamento de cabo dedicado, o
# que já foge de uma checagem rápida de viabilidade.
_SERVICE_RADIUS_METERS = 300


class FeasibilityRequest(BaseModel):
    work_order_id: str
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class NearbyCto(BaseModel):
    cto_id: str
    code: str
    distance_meters: int
    total_ports: int
    available_ports: int


class FeasibilityResult(BaseModel):
    feasible: bool
    status: str  # disponivel | sem_porta | fora_area | necessita_analise
    nearest_cto: NearbyCto | None
    nearby_ctos: list[NearbyCto]
    message: str
    simulated: bool = False


@router.post("/check", response_model=FeasibilityResult)
async def check_feasibility(
    request: FeasibilityRequest,
    technician: dict = Depends(require_technician),
) -> FeasibilityResult:
    if not request.work_order_id.strip():
        raise HTTPException(422, "work_order_id is required")

    if request.latitude is not None and request.longitude is not None:
        latitude, longitude = request.latitude, request.longitude
    elif request.address and request.address.strip():
        try:
            latitude, longitude = geocode_address(request.address.strip())
        except GeocodingError as error:
            return FeasibilityResult(
                feasible=False,
                status="necessita_analise",
                nearest_cto=None,
                nearby_ctos=[],
                message=f"Não foi possível localizar o endereço automaticamente ({error}). "
                "Informe as coordenadas manualmente ou analise no local.",
            )
    else:
        raise HTTPException(422, "address_or_coordinates_required")

    ctos = cto_store.list_active(technician["organization_id"])
    nearby = sorted(
        (
            NearbyCto(
                cto_id=cto["id"],
                code=cto["code"],
                distance_meters=round(
                    haversine_meters(latitude, longitude, cto["latitude"], cto["longitude"])
                ),
                total_ports=cto["total_ports"],
                available_ports=cto["available_ports"],
            )
            for cto in ctos
        ),
        key=lambda item: item.distance_meters,
    )
    within_radius = [item for item in nearby if item.distance_meters <= _SERVICE_RADIUS_METERS]

    if not nearby:
        return FeasibilityResult(
            feasible=False,
            status="necessita_analise",
            nearest_cto=None,
            nearby_ctos=[],
            message="Nenhuma CTO cadastrada ainda para este provedor. Cadastre a infraestrutura na Central.",
        )
    if not within_radius:
        return FeasibilityResult(
            feasible=False,
            status="fora_area",
            nearest_cto=nearby[0],
            nearby_ctos=nearby[:5],
            message=f"Fora da área de atendimento — CTO mais próxima ({nearby[0].code}) "
            f"está a {nearby[0].distance_meters}m, acima do raio de {_SERVICE_RADIUS_METERS}m.",
        )
    with_ports = [item for item in within_radius if item.available_ports > 0]
    if with_ports:
        return FeasibilityResult(
            feasible=True,
            status="disponivel",
            nearest_cto=with_ports[0],
            nearby_ctos=within_radius[:5],
            message=f"Disponível na CTO {with_ports[0].code}, a {with_ports[0].distance_meters}m "
            f"({with_ports[0].available_ports} porta(s) livre(s)).",
        )
    return FeasibilityResult(
        feasible=False,
        status="sem_porta",
        nearest_cto=within_radius[0],
        nearby_ctos=within_radius[:5],
        message=f"CTO mais próxima ({within_radius[0].code}) está sem portas livres. "
        "Necessário expandir a infraestrutura ou aguardar liberação.",
    )
