import hashlib
import hmac
import time

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.technician_store import technician_store
from app.core.organization_store import organization_store

router = APIRouter(prefix="/auth", tags=["technician-authentication"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)
    organization_slug: str | None = Field(default=None, min_length=1, max_length=80)


def _signature(value: str) -> str:
    return hmac.new(
        get_settings().jwt_secret.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _new_token(organization_id: str, technician_id: str, username: str) -> str:
    payload = (
        f"{organization_id}:{technician_id}:{username}:"
        f"{int(time.time()) + 12 * 60 * 60}"
    )
    return f"{payload}:{_signature(payload)}"


def _valid_token(token: str) -> dict | None:
    try:
        organization_id, technician_id, username, expires, signature = token.rsplit(":", 4)
        payload = f"{organization_id}:{technician_id}:{username}:{expires}"
        if int(expires) < int(time.time()) or not hmac.compare_digest(signature, _signature(payload)):
            return None
        return technician_store.get_active(technician_id, username, organization_id)
    except (TypeError, ValueError):
        return False


def require_technician(
    authorization: str | None = Header(default=None),
) -> dict:
    scheme, _, token = (authorization or "").partition(" ")
    technician = _valid_token(token) if scheme.lower() == "bearer" else None
    if technician is None:
        raise HTTPException(401, "technician_authentication_required")
    return technician


@router.post("/technician/login")
async def technician_login(request: LoginRequest) -> dict:
    settings = get_settings()
    organization_slug = request.organization_slug or settings.default_organization_slug
    organization = organization_store.get_active_by_slug(organization_slug)
    if organization is None:
        raise HTTPException(401, "invalid_technician_credentials")
    technician = technician_store.authenticate(
        request.username, request.password, organization["id"]
    )
    if technician is None:
        raise HTTPException(401, "invalid_technician_credentials")
    return {
        "access_token": _new_token(
            organization["id"], technician["id"], technician["username"]
        ),
        "token_type": "bearer",
        "expires_in": 12 * 60 * 60,
        "technician": technician,
        "organization": {
            "id": organization["id"],
            "name": organization["name"],
            "slug": organization["slug"],
        },
        "simulated": True,
    }
