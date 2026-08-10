import hashlib
import hmac
import time

from fastapi import HTTPException, Request

from app.core.config import get_settings
from app.core.portal_customer_store import portal_customer_store

PORTAL_COOKIE_NAME = "isp_portal_session"


def _signature(value: str) -> str:
    secret = get_settings().jwt_secret.encode("utf-8")
    return hmac.new(secret, value.encode("utf-8"), hashlib.sha256).hexdigest()


def new_portal_session(customer: dict) -> str:
    payload = (
        f"{customer['organization_id']}:{customer['id']}:"
        f"{int(time.time()) + 8 * 60 * 60}"
    )
    return f"{payload}:{_signature(payload)}"


def require_portal_customer(request: Request, organization_id: str) -> dict:
    value = request.cookies.get(PORTAL_COOKIE_NAME)
    try:
        session_organization_id, customer_id, expires, signature = (
            value or ""
        ).rsplit(":", 3)
        payload = f"{session_organization_id}:{customer_id}:{expires}"
        valid = (
            session_organization_id == organization_id
            and int(expires) >= int(time.time())
            and hmac.compare_digest(signature, _signature(payload))
        )
    except (TypeError, ValueError):
        valid = False
        customer_id = ""
    customer = (
        portal_customer_store.get_active(organization_id, customer_id)
        if valid
        else None
    )
    if customer is None:
        raise HTTPException(401, "portal_login_required")
    return customer
