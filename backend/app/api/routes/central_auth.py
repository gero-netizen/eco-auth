import hashlib
import hmac
import time
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.audit_store import audit_store
from app.core.central_user_store import central_user_store
from app.core.login_attempt_store import login_attempt_store
from app.core.config import get_settings
from app.core.organization_store import organization_store
from app.core.tenant_context import set_current_organization

router = APIRouter(tags=["central-authentication"])
_cookie_name = "isp_central_session"


def _signature(value: str) -> str:
    secret = get_settings().jwt_secret.encode("utf-8")
    return hmac.new(secret, value.encode("utf-8"), hashlib.sha256).hexdigest()


def _new_session(user: dict) -> str:
    payload = (
        f"{user['organization_id']}:{user['id']}:{user['username']}:"
        f"{user['role']}:{int(time.time()) + 8 * 60 * 60}"
    )
    return f"{payload}:{_signature(payload)}"


def _valid_session(value: str | None) -> dict | None:
    if not value:
        return None
    try:
        organization_id, user_id, username, role, expires, signature = value.rsplit(
            ":", 5
        )
        payload = f"{organization_id}:{user_id}:{username}:{role}:{expires}"
        valid = int(expires) >= int(time.time()) and hmac.compare_digest(
            signature, _signature(payload)
        )
        if not valid:
            return None
        organization = organization_store.get_active(organization_id)
        user = central_user_store.get_active(user_id, organization_id)
        if (
            organization is None
            or user is None
            or user["username"] != username
            or user["role"] != role
        ):
            return None
        return {"user": user, "username": username, "organization": organization}
    except (TypeError, ValueError):
        return None


def require_central_session(request: Request) -> dict:
    session = _valid_session(request.cookies.get(_cookie_name))
    if session is None:
        raise HTTPException(
            status_code=303,
            detail="central_login_required",
            headers={"Location": "/central/login"},
        )
    set_current_organization(session["organization"]["id"])
    return session


def require_central_roles(*allowed_roles: str):
    async def dependency(request: Request) -> dict:
        session = require_central_session(request)
        if session["user"]["role"] not in allowed_roles:
            raise HTTPException(403, "central_role_not_allowed")
        yield session
        _audit_mutation_once(request, session)

    return dependency


async def require_central_access(request: Request) -> dict:
    session = require_central_session(request)
    if session["user"]["role"] == "viewer" and request.method not in {
        "GET",
        "HEAD",
        "OPTIONS",
    }:
        raise HTTPException(403, "central_read_only_user")
    yield session
    _audit_mutation_once(request, session)


def _audit_mutation_once(request: Request, session: dict) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"} or getattr(
        request.state, "central_audit_recorded", False
    ):
        return
    request.state.central_audit_recorded = True
    audit_store.record(
        session["organization"]["id"],
        session["user"],
        request.method,
        request.url.path,
        {"query": str(request.url.query)} if request.url.query else {},
    )


@router.get("/central/login", response_class=HTMLResponse)
async def central_login_page(request: Request, error: bool = False, locked: bool = False):
    if _valid_session(request.cookies.get(_cookie_name)):
        return RedirectResponse("/central", status_code=303)
    if locked:
        error_message = (
            "<p class='error'>Muitas tentativas incorretas. Aguarde alguns minutos "
            "antes de tentar de novo.</p>"
        )
    elif error:
        error_message = "<p class='error'>Provedor, usuário ou senha inválidos.</p>"
    else:
        error_message = ""
    default_slug = get_settings().default_organization_slug
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Entrar na Central</title>
<style>body{{margin:0;background:#f3f8f7;color:#17332f;font:16px system-ui,sans-serif;display:grid;place-items:center;min-height:100vh}}main{{width:min(390px,90vw);background:white;padding:28px;border-radius:16px;box-shadow:0 4px 22px #17332f22}}h1{{color:#075e54}}form,label{{display:grid;gap:8px}}form{{gap:16px}}input{{padding:11px;border:1px solid #aac0bb;border-radius:8px;font:inherit}}button{{padding:12px;border:0;border-radius:8px;background:#075e54;color:white;font-weight:bold;cursor:pointer}}.simulation{{background:#fff0c2;border-left:5px solid #e59b00;padding:10px}}.error{{color:#a32616}}</style></head>
<body><main><h1>Central do Provedor</h1><p class="simulation"><b>AMBIENTE DE BANCADA</b></p>{error_message}
<form method="post" action="/central/login"><label>Provedor<input name="organization_slug" value="{default_slug}" required></label><label>Usuário<input name="username" autocomplete="username" required></label><label>Senha<input name="password" type="password" autocomplete="current-password" required></label><button type="submit">ENTRAR</button></form></main></body></html>"""


@router.post("/central/login")
async def central_login(request: Request) -> RedirectResponse:
    fields = parse_qs((await request.body()).decode("utf-8"))
    username = fields.get("username", [""])[0]
    password = fields.get("password", [""])[0]
    organization_slug = fields.get(
        "organization_slug", [get_settings().default_organization_slug]
    )[0]
    login_scope = f"central:{organization_slug.strip().casefold()}"
    if login_attempt_store.is_locked_out(login_scope, username):
        return RedirectResponse("/central/login?error=true&locked=true", status_code=303)
    organization = organization_store.get_active_by_slug(organization_slug)
    user = (
        central_user_store.authenticate(organization["id"], username, password)
        if organization
        else None
    )
    if user is None:
        login_attempt_store.record_failure(login_scope, username)
        return RedirectResponse("/central/login?error=true", status_code=303)
    login_attempt_store.record_success(login_scope, username)
    response = RedirectResponse("/central", status_code=303)
    response.set_cookie(
        _cookie_name,
        _new_session(user),
        max_age=8 * 60 * 60,
        httponly=True,
        samesite="strict",
        secure=get_settings().app_env == "production",
    )
    return response


@router.post("/central/logout")
async def central_logout() -> RedirectResponse:
    response = RedirectResponse("/central/login", status_code=303)
    response.delete_cookie(_cookie_name)
    return response
