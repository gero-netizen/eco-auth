from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.routes.central_auth import require_central_roles, require_central_session
from app.core.audit_store import audit_store
from app.core.central_user_store import CENTRAL_USER_ROLES, central_user_store
from app.core.integration_config_store import integration_config_store
from app.core.subscription_store import SAAS_PLANS, subscription_store
from app.core.technician_store import technician_store

router = APIRouter(prefix="/saas", tags=["saas"])


class CreateCentralUserRequest(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=200)
    role: str


class SimulatePlanChangeRequest(BaseModel):
    plan_code: str


@router.get("/audit-events")
async def list_audit_events(
    limit: int = 200,
    session: dict = Depends(require_central_roles("owner", "admin")),
) -> dict:
    events = audit_store.list_recent(session["organization"]["id"], limit)
    return {"events": events, "count": len(events)}


@router.get("/organization/current")
async def current_organization(session: dict = Depends(require_central_session)) -> dict:
    organization = session["organization"]
    return {
        "id": organization["id"],
        "name": organization["name"],
        "slug": organization["slug"],
        "active": bool(organization["active"]),
    }


@router.get("/subscription/current")
async def current_subscription(
    session: dict = Depends(require_central_session),
) -> dict:
    organization_id = session["organization"]["id"]
    subscription = subscription_store.get_or_create(organization_id)
    subscription["usage"] = {
        "central_users": sum(
            bool(item["active"])
            for item in central_user_store.list_all(organization_id)
        ),
        "technicians": sum(
            bool(item["active"])
            for item in technician_store.list_all(organization_id)
        ),
    }
    return subscription


@router.post("/subscription/simulate-plan")
async def simulate_plan_change(
    request: SimulatePlanChangeRequest,
    session: dict = Depends(require_central_roles("owner")),
) -> dict:
    if request.plan_code not in SAAS_PLANS:
        raise HTTPException(422, "invalid_saas_plan")
    organization_id = session["organization"]["id"]
    plan = SAAS_PLANS[request.plan_code]
    active_users = sum(
        bool(item["active"])
        for item in central_user_store.list_all(organization_id)
    )
    active_technicians = sum(
        bool(item["active"])
        for item in technician_store.list_all(organization_id)
    )
    if (
        active_users > plan["max_central_users"]
        or active_technicians > plan["max_technicians"]
    ):
        raise HTTPException(409, "saas_plan_below_current_usage")
    return subscription_store.simulate_plan_change(
        organization_id, request.plan_code
    )


@router.get("/integrations/current")
async def current_integrations(session: dict = Depends(require_central_session)) -> dict:
    return integration_config_store.public_summary(
        session["organization"]["id"]
    )


@router.get("/users/current")
async def current_central_user(
    session: dict = Depends(require_central_session),
) -> dict:
    return session["user"]


@router.get("/users")
async def list_central_users(
    session: dict = Depends(require_central_roles("owner", "admin")),
) -> dict:
    return {
        "users": central_user_store.list_all(session["organization"]["id"]),
        "roles": sorted(CENTRAL_USER_ROLES),
    }


@router.post("/users", status_code=201)
async def create_central_user(
    request: CreateCentralUserRequest,
    session: dict = Depends(require_central_roles("owner", "admin")),
) -> dict:
    if request.role not in CENTRAL_USER_ROLES:
        raise HTTPException(422, "invalid_central_user_role")
    if session["user"]["role"] == "admin" and request.role == "owner":
        raise HTTPException(403, "only_owner_can_create_owner")
    organization_id = session["organization"]["id"]
    active_users = sum(
        bool(item["active"])
        for item in central_user_store.list_all(organization_id)
    )
    try:
        subscription_store.ensure_capacity(
            organization_id, "central_users", active_users
        )
        return central_user_store.create(
            organization_id,
            request.name.strip(),
            request.username.strip(),
            request.password,
            request.role,
        )
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
