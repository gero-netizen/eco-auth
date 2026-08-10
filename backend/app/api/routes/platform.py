import hashlib
import hmac
import re
import time
from html import escape
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.central_user_store import central_user_store
from app.core.config import get_settings
from app.core.integration_config_store import integration_config_store
from app.core.organization_store import organization_store
from app.core.subscription_store import SAAS_PLANS, subscription_store

router = APIRouter(tags=["platform-administration"])
_cookie_name = "isp_platform_session"


def _credentials() -> tuple[str, str]:
    settings = get_settings()
    username = settings.platform_admin_username
    password = settings.platform_admin_password
    if settings.app_env == "development":
        username = username or settings.central_username
        password = password or settings.central_password
    return username, password


def _signature(payload: str) -> str:
    return hmac.new(
        get_settings().jwt_secret.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()


def _new_session(username: str) -> str:
    payload = f"{username}:{int(time.time()) + 4 * 60 * 60}"
    return f"{payload}:{_signature(payload)}"


def _valid_session(value: str | None) -> bool:
    try:
        username, expires, signature = (value or "").rsplit(":", 2)
        payload = f"{username}:{expires}"
        expected_username, _ = _credentials()
        return (
            bool(expected_username)
            and username == expected_username
            and int(expires) >= int(time.time())
            and hmac.compare_digest(signature, _signature(payload))
        )
    except (TypeError, ValueError):
        return False


def require_platform_session(request: Request) -> None:
    if not _valid_session(request.cookies.get(_cookie_name)):
        raise HTTPException(
            303,
            "platform_login_required",
            headers={"Location": "/plataforma/login"},
        )


@router.get("/plataforma/login", response_class=HTMLResponse)
async def platform_login_page(request: Request, error: bool = False) -> str:
    if _valid_session(request.cookies.get(_cookie_name)):
        return RedirectResponse("/plataforma", status_code=303)
    message = "<p class='error'>Usuário ou senha inválidos.</p>" if error else ""
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Administração SaaS</title>
<style>body{{margin:0;background:#eef5f4;font:16px system-ui;display:grid;place-items:center;min-height:100vh}}main{{width:min(390px,90vw);background:white;padding:28px;border-radius:16px;box-shadow:0 4px 22px #17332f22}}form,label{{display:grid;gap:8px}}form{{gap:16px}}input,button{{padding:11px;border-radius:8px;font:inherit}}input{{border:1px solid #aac0bb}}button{{border:0;background:#075e54;color:white;font-weight:bold}}.error{{color:#a32616}}</style></head>
<body><main><h1>Administração SaaS</h1><p>Acesso exclusivo da operadora da plataforma.</p>{message}<form method="post" action="/plataforma/login"><label>Usuário<input name="username" required></label><label>Senha<input name="password" type="password" required></label><button>ENTRAR</button></form></main></body></html>"""


@router.post("/plataforma/login")
async def platform_login(request: Request) -> RedirectResponse:
    fields = parse_qs((await request.body()).decode())
    username = fields.get("username", [""])[0]
    password = fields.get("password", [""])[0]
    expected_username, expected_password = _credentials()
    if not expected_username or not hmac.compare_digest(username, expected_username) or not hmac.compare_digest(password, expected_password):
        return RedirectResponse("/plataforma/login?error=true", status_code=303)
    response = RedirectResponse("/plataforma", status_code=303)
    response.set_cookie(
        _cookie_name, _new_session(username), max_age=4 * 60 * 60,
        httponly=True, samesite="strict",
        secure=get_settings().app_env == "production",
    )
    return response


@router.post("/plataforma/logout")
async def platform_logout() -> RedirectResponse:
    response = RedirectResponse("/plataforma/login", status_code=303)
    response.delete_cookie(_cookie_name)
    return response


@router.get(
    "/plataforma",
    response_class=HTMLResponse,
    dependencies=[Depends(require_platform_session)],
)
async def platform_dashboard() -> str:
    organizations = organization_store.list_all()
    rows = "".join(
        _organization_row(item) for item in organizations
    ) or "<tr><td colspan='7'>Nenhum provedor cadastrado.</td></tr>"
    plan_options = "".join(
        f"<option value='{escape(code)}'>{escape(plan['name'])}</option>"
        for code, plan in SAAS_PLANS.items()
    )
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Administração SaaS</title>
<style>body{{margin:0;background:#f3f8f7;color:#17332f;font:16px system-ui}}header{{background:#075e54;color:white;padding:20px 4vw;display:flex;justify-content:space-between}}main{{width:min(1300px,94vw);margin:24px auto}}section{{background:white;padding:20px;border-radius:14px;box-shadow:0 2px 10px #17332f18;margin-bottom:18px}}form.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}label{{display:grid;gap:5px}}input,select,button{{padding:10px;border-radius:8px;font:inherit}}input,select{{border:1px solid #aac0bb}}button{{border:0;background:#075e54;color:white;cursor:pointer}}button.warning{{background:#b45309}}table{{width:100%;border-collapse:collapse}}th,td{{padding:11px 8px;border-bottom:1px solid #dce8e5;text-align:left}}.status{{font-weight:bold}}@media(max-width:760px){{form.grid{{grid-template-columns:1fr}}}}</style></head>
<body><header><div><h1>Administração SaaS</h1><span>Gestão dos provedores</span></div><form method="post" action="/plataforma/logout"><button>SAIR</button></form></header><main>
<section><h2>Cadastrar novo provedor</h2><p>O cadastro cria a organização, o proprietário inicial e o período de teste isolado.</p><form class="grid" method="post" action="/plataforma/organizations"><label>Nome do provedor<input name="name" minlength="3" required></label><label>Identificador de acesso<input name="slug" pattern="[a-z0-9-]+" minlength="3" placeholder="provedor-exemplo" required></label><label>Plano inicial<select name="plan_code">{plan_options}</select></label><label>Nome do proprietário<input name="owner_name" minlength="3" required></label><label>Usuário do proprietário<input name="owner_username" minlength="3" required></label><label>Senha inicial<input name="owner_password" type="password" minlength="8" required></label><button type="submit">CADASTRAR PROVEDOR</button></form></section>
<section><h2>Provedores cadastrados</h2><table><thead><tr><th>Provedor</th><th>Acesso</th><th>Plano</th><th>Assinatura</th><th>Teste até</th><th>Situação</th><th>Ação</th></tr></thead><tbody>{rows}</tbody></table></section>
</main></body></html>"""


def _organization_row(item: dict) -> str:
    integration_config_store.ensure_unconfigured(item["id"])
    subscription = subscription_store.get_or_create(item["id"])
    active = bool(item["active"])
    return (
        f"<tr><td>{escape(item['name'])}</td><td>{escape(item['slug'])}</td>"
        f"<td>{escape(subscription['plan']['name'])}</td><td>{escape(subscription['status'])}</td>"
        f"<td>{escape(subscription['trial_ends_at'] or '-')}</td>"
        f"<td class='status'>{'Ativo' if active else 'Inativo'}</td><td>"
        f"<form method='post' action='/plataforma/organizations/{escape(item['id'])}/toggle'>"
        f"<input type='hidden' name='active' value='{'0' if active else '1'}'>"
        f"<button class='{'warning' if active else ''}'>{'DESATIVAR' if active else 'ATIVAR'}</button></form></td></tr>"
    )


@router.post(
    "/plataforma/organizations",
    dependencies=[Depends(require_platform_session)],
)
async def create_organization(request: Request) -> RedirectResponse:
    fields = parse_qs((await request.body()).decode())
    name = fields.get("name", [""])[0].strip()
    slug = fields.get("slug", [""])[0].strip().casefold()
    plan_code = fields.get("plan_code", [""])[0]
    owner_name = fields.get("owner_name", [""])[0].strip()
    owner_username = fields.get("owner_username", [""])[0].strip().casefold()
    owner_password = fields.get("owner_password", [""])[0]
    if (
        len(name) < 3 or len(owner_name) < 3 or len(owner_username) < 3
        or len(owner_password) < 8 or not re.fullmatch(r"[a-z0-9-]{3,80}", slug)
        or plan_code not in SAAS_PLANS
    ):
        raise HTTPException(422, "invalid_organization_data")
    try:
        organization = organization_store.create(name, slug)
        integration_config_store.ensure_unconfigured(organization["id"])
        central_user_store.create(
            organization["id"], owner_name, owner_username, owner_password, "owner"
        )
        subscription_store.simulate_plan_change(organization["id"], plan_code)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    return RedirectResponse("/plataforma", status_code=303)


@router.post(
    "/plataforma/organizations/{organization_id}/toggle",
    dependencies=[Depends(require_platform_session)],
)
async def toggle_organization(
    organization_id: str, request: Request
) -> RedirectResponse:
    fields = parse_qs((await request.body()).decode())
    active = fields.get("active", ["0"])[0] == "1"
    try:
        organization_store.set_active(organization_id, active)
    except KeyError as error:
        raise HTTPException(404, str(error)) from error
    return RedirectResponse("/plataforma", status_code=303)
