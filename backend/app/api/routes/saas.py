from fastapi import APIRouter, Depends

from app.api.routes.central_auth import require_central_session
from app.core.integration_config_store import integration_config_store

router = APIRouter(prefix="/saas", tags=["saas"])


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
