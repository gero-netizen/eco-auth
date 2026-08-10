from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.routes.central_auth import require_central_roles, require_central_session
from app.core.central_user_store import CENTRAL_USER_ROLES, central_user_store
from app.core.integration_config_store import integration_config_store

router = APIRouter(prefix="/saas", tags=["saas"])


class CreateCentralUserRequest(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=200)
    role: str


@router.get("/organization/current")
async def current_organization(session: dict = Depends(require_central_session)) -> dict:
    organization = session["organization"]
    return {
        "id": organization["id"],
        "name": organization["name"],
        "slug": organization["slug"],
        "active": bool(organization["active"]),
    }


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
    try:
        return central_user_store.create(
            session["organization"]["id"],
            request.name.strip(),
            request.username.strip(),
            request.password,
            request.role,
        )
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
