import asyncio
from html import escape
from urllib.parse import parse_qs
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.routes.financial import (
    ensure_simulated_account,
    reset_simulated_account,
    simulate_pix_account,
    trust_unlock_account,
)
from app.core.organization_store import organization_store
from app.core.login_attempt_store import login_attempt_store
from app.core.integration_config_store import get_integration_settings
from app.core.config import get_settings
from app.core.audit_store import audit_store
from app.core.tenant_context import set_current_organization
from app.core.trust_unlock_store import TrustUnlockStore
from app.core.trust_unlock_orchestrator import request_trust_unlock
from app.core.financial_payment_store import financial_payment_store
from app.core.mercado_pago_config_store import mercado_pago_config_store
from app.core.portal_customer_store import portal_customer_store
from app.core.portal_invite_store import portal_invite_store
from app.core.portal_session import (
    PORTAL_COOKIE_NAME,
    new_portal_session,
    require_portal_customer,
)
from app.api.routes.support import list_support_requests, save_rating
from app.api.routes.network import list_active_alerts
from app.integrations.mkauth.client import simulated_mkauth_gateway
from app.integrations.mkauth.api_client import MkAuthApiClient
from app.integrations.mercado_pago.client import (
    MercadoPagoUnavailableError,
    mercado_pago_client,
)
from app.integrations.routeros.client import RouterOsReadOnlyClient

router = APIRouter(tags=["simulated-client-portal"])
_customer_id = "sim-customer-1"


def _primary_color(organization: dict) -> str:
    return escape(str(organization.get("primary_color") or "#075e54"))


def _support_contact(organization: dict) -> str:
    contacts = [
        str(organization.get("support_phone") or "").strip(),
        str(organization.get("support_email") or "").strip(),
    ]
    visible = " • ".join(escape(item) for item in contacts if item)
    return f"<p><small>Suporte: {visible}</small></p>" if visible else ""


def _portal_organization(organization_slug: str | None) -> tuple[dict, str]:
    organization = (
        organization_store.get_default()
        if organization_slug is None
        else organization_store.get_active_by_slug(organization_slug)
    )
    if organization is None:
        raise HTTPException(404, "organization_not_found")
    portal_path = (
        "/cliente"
        if organization_slug is None
        else f"/portal/{organization['slug']}"
    )
    return organization, portal_path


def _authenticated_customer(
    request: Request, organization: dict, organization_slug: str | None
) -> dict:
    if organization_slug is None:
        return {"id": _customer_id, "name": "Cliente Financeiro de Bancada"}
    try:
        return require_portal_customer(request, organization["id"])
    except HTTPException as error:
        raise HTTPException(
            303,
            "portal_login_required",
            headers={"Location": f"/portal/{organization['slug']}/login"},
        ) from error


@router.get("/portal/{organization_slug}/login", response_class=HTMLResponse)
async def portal_login_page(
    organization_slug: str, error: bool = False, locked: bool = False
) -> str:
    organization = organization_store.get_active_by_slug(organization_slug)
    if organization is None:
        raise HTTPException(404, "organization_not_found")
    if locked:
        error_message = (
            "<p class='error'>Muitas tentativas incorretas. Aguarde alguns "
            "minutos antes de tentar de novo.</p>"
        )
    elif error:
        error_message = "<p class='error'>Usuário ou senha inválidos.</p>"
    else:
        error_message = ""
    primary_color = _primary_color(organization)
    support_contact = _support_contact(organization)
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Entrar no portal</title>
<style>body{{margin:0;background:#f3f8f7;color:#17332f;font:16px system-ui,sans-serif;display:grid;place-items:center;min-height:100vh}}main{{width:min(390px,90vw);background:white;padding:28px;border-radius:16px;box-shadow:0 4px 22px #17332f22}}h1{{color:{primary_color}}}form,label{{display:grid;gap:8px}}form{{gap:16px}}input{{padding:11px;border:1px solid #aac0bb;border-radius:8px;font:inherit}}button{{padding:12px;border:0;border-radius:8px;background:{primary_color};color:white;font-weight:bold;cursor:pointer}}.simulation{{background:#fff0c2;border-left:5px solid #e59b00;padding:10px}}.error{{color:#a32616}}</style></head>
<body><main><h1>{escape(organization['name'])}</h1><p>Portal do Cliente</p>
<p class="simulation"><b>ACESSO:</b> use as credenciais fornecidas pelo seu provedor.</p>{error_message}
<form method="post" action="/portal/{escape(organization['slug'])}/login"><label>Usuário<input name="username" autocomplete="username" required></label><label>Senha<input name="password" type="password" autocomplete="current-password" required></label><button type="submit">ENTRAR</button></form>{support_contact}</main></body></html>"""


@router.post("/portal/{organization_slug}/login")
async def portal_login(
    organization_slug: str, request: Request
) -> RedirectResponse:
    organization = organization_store.get_active_by_slug(organization_slug)
    if organization is None:
        raise HTTPException(404, "organization_not_found")
    fields = parse_qs((await request.body()).decode("utf-8"))
    username = fields.get("username", [""])[0]
    login_scope = f"portal:{organization_slug.strip().casefold()}"
    if login_attempt_store.is_locked_out(login_scope, username):
        return RedirectResponse(
            f"/portal/{organization_slug}/login?error=true&locked=true", status_code=303
        )
    customer = portal_customer_store.authenticate(
        organization["id"], username, fields.get("password", [""])[0]
    )
    if customer is None:
        login_attempt_store.record_failure(login_scope, username)
        return RedirectResponse(
            f"/portal/{organization_slug}/login?error=true", status_code=303
        )
    login_attempt_store.record_success(login_scope, username)
    response = RedirectResponse(f"/portal/{organization_slug}", status_code=303)
    response.set_cookie(
        PORTAL_COOKIE_NAME,
        new_portal_session(customer),
        max_age=8 * 60 * 60,
        httponly=True,
        samesite="strict",
        secure=get_settings().app_env == "production",
        path=f"/portal/{organization_slug}",
    )
    return response


@router.post("/portal/{organization_slug}/logout")
async def portal_logout(organization_slug: str) -> RedirectResponse:
    response = RedirectResponse(
        f"/portal/{organization_slug}/login", status_code=303
    )
    response.delete_cookie(
        PORTAL_COOKIE_NAME, path=f"/portal/{organization_slug}"
    )
    return response


@router.get(
    "/portal/{organization_slug}/convite/{token}",
    response_class=HTMLResponse,
    name="portal_invite_page",
)
async def portal_invite_page(organization_slug: str, token: str) -> str:
    organization = organization_store.get_active_by_slug(organization_slug)
    if organization is None:
        raise HTTPException(404, "organization_not_found")
    invite = portal_invite_store.inspect(organization["id"], token)
    if invite is None:
        raise HTTPException(410, "portal_invite_invalid_or_expired")
    customer = portal_customer_store.get_active(
        organization["id"], invite["customer_id"]
    )
    if customer is None:
        raise HTTPException(410, "portal_invite_customer_unavailable")
    primary_color = _primary_color(organization)
    support_contact = _support_contact(organization)
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Definir senha</title>
<style>body{{margin:0;background:#f3f8f7;color:#17332f;font:16px system-ui,sans-serif;display:grid;place-items:center;min-height:100vh}}main{{width:min(420px,90vw);background:white;padding:28px;border-radius:16px;box-shadow:0 4px 22px #17332f22}}h1{{color:{primary_color}}}form,label{{display:grid;gap:8px}}form{{gap:16px}}input{{padding:11px;border:1px solid #aac0bb;border-radius:8px;font:inherit}}button{{padding:12px;border:0;border-radius:8px;background:{primary_color};color:white;font-weight:bold;cursor:pointer}}</style></head>
<body><main><h1>{escape(organization['name'])}</h1>
<p>Olá, <b>{escape(customer['name'])}</b>. Defina sua senha de acesso ao Portal do Cliente.</p>
<form method="post" action="/portal/{escape(organization_slug)}/convite/{escape(token)}">
<label>Nova senha<input name="password" type="password" minlength="8" maxlength="200" autocomplete="new-password" required></label>
<label>Confirmar senha<input name="password_confirmation" type="password" minlength="8" maxlength="200" autocomplete="new-password" required></label>
<button type="submit">DEFINIR MINHA SENHA</button></form>{support_contact}</main></body></html>"""


@router.post(
    "/portal/{organization_slug}/convite/{token}",
    response_class=HTMLResponse,
)
async def portal_accept_invite(
    organization_slug: str, token: str, request: Request
) -> str:
    organization = organization_store.get_active_by_slug(organization_slug)
    if organization is None:
        raise HTTPException(404, "organization_not_found")
    fields = parse_qs((await request.body()).decode("utf-8"))
    password = fields.get("password", [""])[0]
    confirmation = fields.get("password_confirmation", [""])[0]
    if len(password) < 8 or password != confirmation:
        raise HTTPException(422, "invalid_portal_invite_password")
    invite = portal_invite_store.consume(organization["id"], token)
    if invite is None:
        raise HTTPException(410, "portal_invite_invalid_or_expired")
    try:
        portal_customer_store.reset_password(
            organization["id"], invite["customer_id"], password
        )
    except KeyError as error:
        raise HTTPException(410, "portal_invite_customer_unavailable") from error
    login_url = f"/portal/{escape(organization_slug)}/login"
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Senha definida</title></head>
<body style="font:16px system-ui,sans-serif;background:#f3f8f7;color:#17332f"><main style="width:min(420px,90vw);margin:15vh auto;background:white;padding:28px;border-radius:16px"><h1>Senha definida com sucesso</h1><p>O convite foi utilizado e não poderá ser aberto novamente.</p><p><a href="{login_url}">ENTRAR NO PORTAL</a></p></main></body></html>"""


def _label(value: str) -> str:
    return {
        "blocked": "Bloqueada",
        "trust_released": "Liberada em confiança",
        "active": "Ativa",
        "overdue": "Vencida",
        "paid": "Paga",
    }.get(value, value)


def _work_order_label(value: str) -> str:
    return {
        "assigned": "OS criada — aguardando deslocamento",
        "traveling": "Técnico em deslocamento",
        "arrived": "Técnico chegou ao local",
        "in_progress": "Atendimento em andamento",
        "blocked": "Atendimento temporariamente impedido",
        "completed": "Atendimento finalizado",
        "not_completed": "Atendimento não concluído",
    }.get(value, "Aguardando atualização")


async def _fetch_client_details(organization_id: str, login: str) -> dict | None:
    """Dados reais do cadastro do cliente no MK-AUTH (nome, plano, status,
    ONU, porta OLT). Retorna None se não for possível consultar."""
    settings = get_integration_settings(organization_id)
    if settings.mkauth_mode != "real":
        return None
    try:
        client = MkAuthApiClient(
            settings.mkauth_base_url,
            settings.mkauth_client_id,
            settings.mkauth_client_secret,
            settings.mkauth_verify_ssl,
            settings.mkauth_allow_http and settings.app_env == "development",
        )
        item = await client.get_client_details(login)
    except (ValueError, httpx.HTTPError):
        return None
    return {
        "name": str(item.get("nome") or item.get("nome_res") or "-"),
        "login": str(item.get("login") or login),
        "connection_type": str(item.get("tipo") or "-"),
        "plan": str(item.get("plano") or "-"),
        "activated": str(item.get("cli_ativado") or "-").strip().casefold()
        in {"s", "sim", "1", "true", "ativo"},
        "blocked": str(item.get("bloqueado") or "-").strip().casefold()
        in {"s", "sim", "1", "true", "bloq", "bloqueado"},
        "ip": str(item.get("ip") or item.get("user_ip") or "-"),
        "onu_ont": str(item.get("onu_ont") or "-"),
        "olt_port": str(item.get("porta_olt") or "-"),
        "address": str(item.get("endereco") or item.get("endereco_completo") or "-"),
    }


async def _fetch_active_session(organization_id: str, login: str) -> dict | None:
    """Sessão PPPoE real e ativa deste cliente no MikroTik (IP, tempo
    conectado). Retorna None se o cliente não estiver online agora, ou se
    a integração não estiver em modo real."""
    settings = get_integration_settings(organization_id)
    if settings.routeros_mode != "real" or not settings.routeros_username:
        return None
    try:
        client = RouterOsReadOnlyClient(
            settings.routeros_host,
            settings.routeros_port,
            settings.routeros_username,
            settings.routeros_password,
        )
        diagnostic = await asyncio.to_thread(client.diagnose)
    except Exception:
        return None
    for session in diagnostic.get("sessions", []):
        if str(session.get("username") or "").strip().casefold() == login.casefold():
            return session
    return None


async def _fetch_customer_titles(
    organization_id: str, login: str
) -> tuple[str, list[dict]]:
    """Busca os títulos reais do cliente no MK-AUTH, já filtrados (só os
    dele mesmo, nunca de outro login) e ordenados (vencidos primeiro).
    Retorna (status, títulos) — status é 'not_configured', 'error' ou 'ok'."""
    settings = get_integration_settings(organization_id)
    if settings.mkauth_mode != "real":
        return "not_configured", []
    try:
        client = MkAuthApiClient(
            settings.mkauth_base_url,
            settings.mkauth_client_id,
            settings.mkauth_client_secret,
            settings.mkauth_verify_ssl,
            settings.mkauth_allow_http and settings.app_env == "development",
        )
        raw_titles = await client.list_payable_titles(login)
    except (ValueError, httpx.HTTPError):
        return "error", []
    safe_titles = [
        item
        for item in raw_titles
        if not str(item.get("login") or "").strip()
        or str(item.get("login") or "").strip().casefold() == login.casefold()
    ]
    safe_titles.sort(
        key=lambda item: (
            0
            if str(item.get("status") or "").strip().casefold() == "vencido"
            else 1,
            str(item.get("datavenc") or item.get("vencimento") or "9999-12-31"),
        )
    )
    return "ok", safe_titles


async def _mkauth_titles_panel(
    organization_id: str, customer: dict, portal_path: str
) -> str:
    login = str(customer.get("external_login") or "").strip()
    customer_uuid = str(customer.get("external_customer_id") or "").strip()
    if not login or not customer_uuid:
        return (
            "<section><h2>Meus títulos</h2>"
            "<p>Seu acesso ainda não foi vinculado ao cadastro do provedor.</p>"
            "</section>"
        )
    status, safe_titles = await _fetch_customer_titles(organization_id, login)
    if status == "not_configured":
        return (
            "<section><h2>Meus títulos</h2>"
            "<p>A consulta ao sistema financeiro ainda não está disponível.</p>"
            "</section>"
        )
    if status == "error":
        return (
            "<section><h2>Meus títulos</h2>"
            "<p>Não foi possível consultar seus títulos agora. Tente novamente mais tarde.</p>"
            "</section>"
        )
    mp_config = mercado_pago_config_store.get(organization_id)
    pix_available = mp_config.enabled and bool(mp_config.access_token)
    rows = "".join(
        "<tr>"
        f"<td>{escape(str(item.get('titulo') or item.get('numero') or '-'))}</td>"
        f"<td>R$ {escape(str(item.get('valor') or '0,00'))}</td>"
        f"<td>{escape(str(item.get('datavenc') or item.get('vencimento') or '-'))}</td>"
        f"<td>{escape(_label(str(item.get('status') or '-').strip().casefold()))}</td>"
        "<td>"
        + (
            f"<form method='post' action='{portal_path}/financeiro/{escape(str(item.get('uuid') or ''))}/pix'>"
            "<button type='submit'>PAGAR COM PIX</button></form>"
            if pix_available and item.get("uuid") else "-"
        )
        + "</td></tr>"
        for item in safe_titles
    ) or "<tr><td colspan='5'>Nenhum título vencido ou a vencer.</td></tr>"
    return (
        "<section><h2>Meus títulos</h2>"
        f"<p>Cadastro vinculado: <b>{escape(login)}</b></p>"
        "<p><small>Consulta real e somente leitura no MK-AUTH.</small></p>"
        "<table><thead><tr><th>Título</th><th>Valor</th><th>Vencimento</th>"
        f"<th>Situação</th><th>Ação</th></tr></thead><tbody>{rows}</tbody></table></section>"
    )


@router.get("/cliente", response_class=HTMLResponse)
@router.get("/portal/{organization_slug}", response_class=HTMLResponse)
async def client_portal(
    request: Request, organization_slug: str | None = None
) -> str:
    organization, portal_path = _portal_organization(organization_slug)
    customer = _authenticated_customer(request, organization, organization_slug)
    organization_id = organization["id"]
    primary_color = _primary_color(organization)
    login = str(customer.get("external_login") or "").strip()
    first_name = escape(str(customer.get("name") or "Cliente").split(" ")[0])
    full_name = escape(str(customer.get("name") or "Cliente"))

    # ---------- Dados reais: MK-AUTH, MikroTik, títulos ----------
    client_details = await _fetch_client_details(organization_id, login) if login else None
    active_session = await _fetch_active_session(organization_id, login) if login else None
    titles_status, titles = (
        await _fetch_customer_titles(organization_id, login) if login else ("not_configured", [])
    )
    account = ensure_simulated_account(organization_id, organization["name"], customer["id"])
    mp_config = mercado_pago_config_store.get(organization_id)
    pix_available = mp_config.enabled and bool(mp_config.access_token)

    # ---------- Status da conexão ----------
    bench_status_label = None
    if active_session is not None:
        connection_online = True
        connection_source = "MikroTik (tempo real)"
        connection_ip = escape(str(active_session.get("address") or "-"))
        connection_uptime = escape(str(active_session.get("uptime") or "-"))
    elif client_details is not None:
        connection_online = client_details["activated"] and not client_details["blocked"]
        connection_source = "Cadastro MK-AUTH"
        connection_ip = escape(client_details["ip"])
        connection_uptime = "-"
    else:
        connection_online = account["access_status"] == "active"
        connection_source = "Bancada (simulado)"
        connection_ip = "-"
        connection_uptime = "-"
        bench_status_label = escape(_label(account["access_status"]))
    plan_name = escape(
        client_details["plan"] if client_details and client_details["plan"] != "-"
        else "Plano não identificado"
    )

    # ---------- Próxima fatura ----------
    open_titles = [
        item for item in titles
        if str(item.get("status") or "").strip().casefold() not in {"pago", "liquidado", "recebido", "baixado"}
    ]
    next_title = open_titles[0] if open_titles else None
    if next_title is not None:
        invoice_amount = escape(str(next_title.get("valor") or "0,00"))
        invoice_due = escape(str(next_title.get("datavenc") or next_title.get("vencimento") or "-"))
        invoice_status_label = escape(_label(str(next_title.get("status") or "-").strip().casefold()))
        title_uuid = str(next_title.get("uuid") or "")
        can_pay_pix = pix_available and bool(title_uuid)
    else:
        invoice_amount = f"{account['invoice_amount']:.2f}"
        invoice_due = "-"
        invoice_status_label = escape(_label(account["invoice_status"]))
        title_uuid = ""
        can_pay_pix = False

    # ---------- Avisos de rede ----------
    alerts = list_active_alerts(organization_id)
    all_systems_ok = not alerts
    notice_html = "".join(
        f"<div class='notice-banner'><i data-lucide='alert-triangle'></i>"
        f"<p><span>{escape(alert.title)}</span> — área afetada: {escape(alert.area)}. "
        "Nossa equipe já foi avisada, não é preciso abrir chamado para isso.</p></div>"
        for alert in alerts
    )

    # ---------- Chamados ----------
    requests = list_support_requests(customer["id"], organization_id)
    orders = {
        order.id: order
        for order in await simulated_mkauth_gateway.list_work_orders("bench-technician", organization_id)
    }
    ticket_rows = []
    for item in requests[:8]:
        order = orders.get(item["work_order_id"])
        if order is not None:
            status = f"{order.code} • {_work_order_label(order.status.value)}"
        elif item["status"] == "converted":
            status = "OS gerada — aguardando atualização"
        elif item["status"] == "answered":
            status = "Respondido pela equipe"
        else:
            status = "Recebido — aguardando a central"
        ticket_rows.append(
            f"<li class='ticket-row'><div><p class='ticket-subject'>#{item['id']} — {escape(item['subject'])}</p>"
            f"<p class='ticket-meta'>Ver detalhes</p></div>"
            f"<a class='ticket-badge' href='{portal_path}/chamados/{item['id']}'>{escape(status)}</a></li>"
        )
    ticket_list_html = "".join(ticket_rows) or "<li class='ticket-empty'>Nenhum chamado aberto ainda.</li>"

    # ---------- Suporte via WhatsApp ----------
    support_phone = str(organization.get("support_phone") or "").strip()
    whatsapp_digits = "".join(ch for ch in support_phone if ch.isdigit())
    whatsapp_href = f"https://wa.me/{whatsapp_digits}" if whatsapp_digits else "#"

    logout_action = f"{portal_path}/logout" if organization_slug is not None else None

    trust_unlock_block = (
        f"""<form method="post" action="{portal_path}/desbloqueio-confianca" id="trust-unlock-form">
          <button type="submit" class="btn-primary-outline w-full">Confirmar liberação por 48h</button>
        </form>"""
        if organization_slug is not None else
        "<p class='text-xs text-faint'>Disponível apenas para clientes com acesso ao portal (fora do modo de bancada).</p>"
    )

    pix_action_html = (
        f"<form method='post' action='{portal_path}/financeiro/{escape(title_uuid)}/pix'>"
        "<button type='submit' class='btn-pix w-full'><i data-lucide=\"qr-code\"></i> Pagar com PIX</button></form>"
        if can_pay_pix else
        "<button class='btn-pix w-full' disabled title='Pix real não configurado para este provedor'>"
        "<i data-lucide=\"qr-code\"></i> Pagar com PIX</button>"
    )

    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{escape(organization['name'])} • Central do Cliente</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<script src="https://unpkg.com/lucide@latest/dist/umd/lucide.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<script>
  tailwind.config = {{ theme: {{ extend: {{
    colors: {{ bg:'#0B1220', surface:'#141D33', surface2:'#1B2743', border:'#26314F', ink:'#F1F5F9', muted:'#94A3B8', faint:'#5D6B8A',
      blue: {{ DEFAULT:'{primary_color}', dark:'{primary_color}', soft:'#DBEAFE' }}, green: {{ DEFAULT:'#22C55E' }} }},
    fontFamily: {{ sans: ['Inter','sans-serif'] }} }} }} }};
</script>
<style>
  body{{background:#0B1220}} ::-webkit-scrollbar{{width:10px}} ::-webkit-scrollbar-thumb{{background:#26314F;border-radius:999px}}
  .tab-panel{{display:none}} .tab-panel.active{{display:block;animation:fade-in .2s ease}}
  @keyframes fade-in{{from{{opacity:0;transform:translateY(4px)}}to{{opacity:1;transform:translateY(0)}}}}
  .nav-item[aria-current="page"]{{background:{primary_color};color:white}} .nav-item:not([aria-current="page"]):hover{{background:#1B2743}}
  .notice-banner{{display:flex;gap:12px;align-items:flex-start;background:#DBEAFE;color:#1e293b;border-radius:16px;padding:16px 20px;margin-bottom:12px}}
  .notice-banner i{{width:18px;height:18px;color:{primary_color};flex-shrink:0;margin-top:2px}}
  .notice-ok{{display:flex;gap:10px;align-items:center;background:#141D33;border:1px solid #26314F;border-radius:16px;padding:14px 20px;margin-bottom:20px;color:#94A3B8;font-size:14px}}
  .card{{border-radius:16px;border:1px solid #26314F;background:#141D33;padding:24px;box-shadow:0 12px 30px -18px rgba(0,0,0,.6)}}
  .btn-primary{{background:{primary_color};color:white;font-weight:600;border-radius:12px;padding:11px 16px;border:0;cursor:pointer;font-size:14px}}
  .btn-primary-outline{{border:1px solid {primary_color}66;color:{primary_color};background:transparent;font-weight:600;border-radius:12px;padding:11px 16px;cursor:pointer;font-size:14px}}
  .btn-pix{{background:#22C55E;color:white;font-weight:600;border-radius:12px;padding:11px 16px;border:0;cursor:pointer;font-size:14px;display:flex;align-items:center;justify-content:center;gap:8px}}
  .btn-pix:disabled{{opacity:.5;cursor:not-allowed}}
  .btn-secondary{{border:1px solid #26314F;background:transparent;color:#F1F5F9;font-weight:500;border-radius:12px;padding:11px 16px;cursor:pointer;font-size:14px}}
  .estimate-badge{{font-size:10px;font-weight:600;background:#F5A62333;color:#F5A623;padding:2px 8px;border-radius:999px;margin-left:6px;vertical-align:middle}}
  .ticket-row{{display:flex;align-items:center;justify-content:space-between;padding:12px 0;border-bottom:1px solid #26314F}}
  .ticket-row:last-child{{border-bottom:0}} .ticket-subject{{font-size:14px;margin:0}} .ticket-meta{{font-size:11px;color:#5D6B8A;margin:2px 0 0}}
  .ticket-badge{{font-size:11px;font-weight:600;background:#F5A62326;color:#F5A623;padding:5px 10px;border-radius:999px;text-decoration:none;white-space:nowrap}}
  .ticket-empty{{color:#5D6B8A;font-size:14px;padding:12px 0}}
  input,textarea,select{{background:#1B2743;border:1px solid #26314F;border-radius:10px;padding:10px 12px;font:inherit;color:#F1F5F9;width:100%}}
  input::placeholder,textarea::placeholder{{color:#5D6B8A}}
  @media (min-width:768px){{ #mobile-tabbar{{display:none}} }} @media (max-width:767px){{ #sidebar{{display:none}} }}
</style>
</head>
<body class="bg-bg text-ink font-sans antialiased min-h-screen">
<div class="flex min-h-screen">
  <aside id="sidebar" class="w-64 shrink-0 bg-bg border-r border-border flex flex-col h-screen sticky top-0">
    <div class="h-20 flex items-center gap-3 px-6">
      <div class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style="background:{primary_color}"><i data-lucide="wifi" class="w-5 h-5 text-white"></i></div>
      <div class="leading-tight"><p class="font-extrabold text-lg tracking-tight">{escape(organization['name'])}</p><p class="text-[10px] text-faint tracking-widest">CENTRAL DO CLIENTE</p></div>
    </div>
    <nav class="flex-1 px-4 pt-4 space-y-1.5">
      <button class="nav-item w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-muted transition-colors" data-tab="inicio" aria-current="page"><i data-lucide="home" class="w-[18px] h-[18px]"></i> Início</button>
      <button class="nav-item w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-muted transition-colors" data-tab="financeiro"><i data-lucide="dollar-sign" class="w-[18px] h-[18px]"></i> Faturas &amp; Financeiro</button>
      <button class="nav-item w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-muted transition-colors" data-tab="rede"><i data-lucide="wifi" class="w-[18px] h-[18px]"></i> Minha Rede</button>
      <button class="nav-item w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-muted transition-colors" data-tab="suporte"><i data-lucide="headphones" class="w-[18px] h-[18px]"></i> Suporte Técnico</button>
      <button class="nav-item w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-muted transition-colors" data-tab="perfil"><i data-lucide="user" class="w-[18px] h-[18px]"></i> Contrato &amp; Perfil</button>
    </nav>
    <div class="p-4 border-t border-border">
      <div class="flex items-center gap-3 px-2 py-2">
        <div class="w-10 h-10 rounded-full bg-surface2 grid place-items-center shrink-0"><i data-lucide="user" class="w-5 h-5 text-muted"></i></div>
        <div class="min-w-0"><p class="text-sm font-semibold truncate">{full_name}</p><p class="text-xs text-faint truncate">{escape(login or 'sem login vinculado')}</p></div>
      </div>
      {"<form method='post' action='" + logout_action + "' class='mt-3'><button type='submit' class='w-full flex items-center gap-2 px-2 py-2 rounded-lg text-sm text-red-400 hover:bg-surface2 transition-colors'><i data-lucide=\"log-out\" class=\"w-4 h-4\"></i> Sair</button></form>" if logout_action else ""}
    </div>
  </aside>

  <div class="flex-1 min-w-0 pb-20 md:pb-0">
    <main class="px-4 md:px-8 py-6 md:py-8 max-w-[1400px] mx-auto">
      <div class="flex items-start justify-between gap-4 flex-wrap mb-6">
        <div><h1 class="text-2xl font-bold">Olá, {first_name}! <span aria-hidden="true">👋</span></h1>
        <p class="text-muted text-sm mt-1">Acompanhe sua conexão e seus serviços aqui.</p></div>
        <span class="flex items-center gap-2 {'bg-green/10 border border-green/25 text-green' if all_systems_ok else 'bg-amber-500/10 border border-amber-500/25 text-amber-400'} text-sm font-medium px-4 py-2 rounded-full">
          <span class="w-2 h-2 rounded-full {'bg-green' if all_systems_ok else 'bg-amber-400'}"></span> {'Rede sem ocorrências' if all_systems_ok else f'{len(alerts)} ocorrência(s) na sua região'}
        </span>
      </div>

      <section id="tab-inicio" class="tab-panel active space-y-6">
        {notice_html}
        <div class="grid lg:grid-cols-3 gap-6">
          <div class="card">
            <div class="flex items-center justify-between mb-4"><h2 class="font-bold text-base">Status da Conexão</h2></div>
            <span class="inline-flex items-center gap-2 {'bg-green/15 text-green' if connection_online else 'bg-red-500/15 text-red-400'} text-sm font-semibold px-4 py-2 rounded-full">
              <span class="w-2 h-2 rounded-full {'bg-green' if connection_online else 'bg-red-400'}"></span> {'Online / Ativo' if connection_online else 'Offline / Inativo'}
            </span>
            <div class="mt-4"><p class="text-xs text-faint">IP {'(sessão ativa)' if active_session else '(último registrado)'}</p><p class="font-semibold text-sm mt-0.5">{connection_ip}</p></div>
            <div class="mt-3"><p class="text-xs text-faint">Tempo conectado</p><p class="font-semibold text-sm mt-0.5">{connection_uptime}</p></div>
            <div class="mt-3"><p class="text-xs text-faint">Plano contratado</p><p class="font-bold mt-0.5" style="color:{primary_color}">{plan_name}</p></div>
            <p class="text-[11px] text-faint mt-4">Fonte: {connection_source}{f' • Situação simulada: {bench_status_label}' if bench_status_label else ''}</p>
          </div>

          <div class="card">
            <div class="flex items-center justify-between mb-1"><h2 class="font-bold text-base">Consumo de Dados<span class="estimate-badge">ESTIMATIVA</span></h2></div>
            <p class="text-xs text-faint mb-2">Ainda não coletamos tráfego em tempo real — os números abaixo são ilustrativos.</p>
            <div class="h-44 mt-2"><canvas id="usageChart"></canvas></div>
          </div>

          <div class="card">
            <h2 class="font-bold text-base mb-4">Próxima Fatura</h2>
            <div class="flex items-center justify-between">
              <div><p class="text-xs text-faint">Vencimento</p><p class="font-bold mt-0.5" style="color:{primary_color}">{invoice_due}</p></div>
              <div class="text-right"><p class="text-xs text-faint">Situação</p><p class="font-bold text-lg mt-0.5">R$ {invoice_amount}</p></div>
            </div>
            <p class="text-xs text-faint mt-3">{invoice_status_label}</p>
            <div class="mt-5">{pix_action_html}</div>
          </div>
        </div>

        <div class="grid lg:grid-cols-3 gap-6">
          <div class="card">
            <div class="flex items-center justify-between mb-3"><h2 class="font-bold text-base">Desbloqueio em Confiança</h2></div>
            <p class="text-sm text-muted mb-4">Em caso de atraso, você pode liberar sua conexão por 48 horas enquanto regulariza o pagamento. Sujeito às regras do seu provedor.</p>
            {trust_unlock_block}
          </div>
          <div class="card">
            <h2 class="font-bold text-base mb-4">Meus chamados</h2>
            <ul>{ticket_list_html}</ul>
            <button onclick="showTab('suporte')" class="btn-secondary w-full mt-4">Abrir novo chamado</button>
          </div>
          <div class="card">
            <h2 class="font-bold text-base mb-4">Suporte rápido</h2>
            <div class="space-y-2">
              <a href="{whatsapp_href}" target="_blank" rel="noopener" class="flex items-center gap-3 rounded-xl bg-surface2 p-3 hover:bg-border transition-colors">
                <div class="w-9 h-9 rounded-lg bg-green/15 grid place-items-center shrink-0"><i data-lucide="message-circle" class="w-[18px] h-[18px] text-green"></i></div>
                <div><p class="text-sm font-medium">WhatsApp</p><p class="text-xs text-faint">Atendimento rápido</p></div>
              </a>
              <button onclick="showTab('suporte')" class="w-full flex items-center gap-3 rounded-xl bg-surface2 p-3 hover:bg-border transition-colors text-left">
                <div class="w-9 h-9 rounded-lg bg-blue/15 grid place-items-center shrink-0"><i data-lucide="gauge" class="w-[18px] h-[18px]" style="color:{primary_color}"></i></div>
                <div><p class="text-sm font-medium">Teste de velocidade</p><p class="text-xs text-faint">Versão estimada</p></div>
              </button>
            </div>
          </div>
        </div>
      </section>

      <section id="tab-financeiro" class="tab-panel space-y-6">
        <div><h1 class="text-xl font-bold">Faturas &amp; Financeiro</h1><p class="text-sm text-muted mt-1">Histórico de cobranças reais consultado direto no MK-AUTH.</p></div>
        <div class="card overflow-hidden !p-0">
          <div class="divide-y divide-border">
            {"".join(
                f"<div class='flex items-center justify-between px-6 py-4'><div><p class='text-sm font-medium'>{escape(str(item.get('titulo') or item.get('numero') or '-'))}</p>"
                f"<p class='text-xs text-faint mt-0.5'>Venc. {escape(str(item.get('datavenc') or item.get('vencimento') or '-'))}</p></div>"
                f"<div class='flex items-center gap-3'><span class='ticket-badge'>{escape(_label(str(item.get('status') or '-').strip().casefold()))}</span>"
                f"<span class='text-sm font-semibold'>R$ {escape(str(item.get('valor') or '0,00'))}</span></div></div>"
                for item in titles
            ) or "<p class='px-6 py-8 text-center text-sm text-faint'>" + (
                (
                    f"Cadastro de bancada — sem título real vinculado.<br>"
                    f"Fatura simulada: R$ {account['invoice_amount']:.2f} "
                    f"({escape(_label(account['invoice_status']))})<br>"
                    f"Código Pix fictício: PIX-SIMULADO-{escape(account['invoice_id'].upper())}-NAO-PAGAR"
                ) if titles_status == "not_configured" and not login
                else "Consulta financeira real ainda não configurada para este provedor." if titles_status == "not_configured"
                else "Não foi possível consultar seus títulos agora. Tente novamente mais tarde." if titles_status == "error"
                else "Nenhum título em aberto."
            ) + "</p>"}
          </div>
        </div>
      </section>

      <section id="tab-rede" class="tab-panel space-y-6">
        <div><h1 class="text-xl font-bold">Minha Rede</h1><p class="text-sm text-muted mt-1">Dados técnicos da sua conexão.</p></div>
        <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div class="card !p-5"><i data-lucide="globe" class="w-4 h-4 mb-3" style="color:{primary_color}"></i><p class="text-xs text-faint">IP {'(sessão ativa)' if active_session else '(último registrado)'}</p><p class="font-semibold mt-1">{connection_ip}</p></div>
          <div class="card !p-5"><i data-lucide="activity" class="w-4 h-4 mb-3" style="color:{primary_color}"></i><p class="text-xs text-faint">Consumo real (hoje)<span class="estimate-badge">ESTIMATIVA</span></p><p class="font-semibold mt-1">18,4 GB</p></div>
          <div class="card !p-5"><i data-lucide="timer" class="w-4 h-4 mb-3" style="color:{primary_color}"></i><p class="text-xs text-faint">Ping<span class="estimate-badge">ESTIMATIVA</span></p><p class="font-semibold mt-1">11 ms</p></div>
          <div class="card !p-5"><i data-lucide="waves" class="w-4 h-4 mb-3" style="color:{primary_color}"></i><p class="text-xs text-faint">Latência (jitter)<span class="estimate-badge">ESTIMATIVA</span></p><p class="font-semibold mt-1">1,8 ms</p></div>
        </div>
        <div class="card"><h2 class="font-bold text-base mb-1">Latência nas últimas 12 horas<span class="estimate-badge">ESTIMATIVA</span></h2>
        <p class="text-xs text-faint mb-3">Coleta de latência em tempo real ainda não disponível — valores ilustrativos.</p>
        <div class="h-44"><canvas id="pingChart"></canvas></div></div>
      </section>

      <section id="tab-suporte" class="tab-panel space-y-6">
        <div><h1 class="text-xl font-bold">Suporte Técnico</h1><p class="text-sm text-muted mt-1">Teste sua conexão, abra um chamado ou fale com a gente.</p></div>
        <div class="grid lg:grid-cols-3 gap-6">
          <div class="card flex flex-col items-center text-center">
            <h2 class="font-bold text-base self-start mb-2">Teste de velocidade<span class="estimate-badge">ESTIMATIVA</span></h2>
            <div class="relative w-36 h-36 my-4 grid place-items-center">
              <svg class="w-full h-full -rotate-90" viewBox="0 0 120 120"><circle cx="60" cy="60" r="52" fill="none" stroke="#1B2743" stroke-width="10"/>
              <circle id="speed-ring" cx="60" cy="60" r="52" fill="none" stroke="{primary_color}" stroke-width="10" stroke-linecap="round" stroke-dasharray="327" stroke-dashoffset="327"/></svg>
              <div class="absolute"><p id="speed-value" class="text-2xl font-bold">0</p><p class="text-xs text-faint">Mbps</p></div>
            </div>
            <button id="btn-speedtest" onclick="runSpeedtest()" class="btn-primary w-full">Iniciar teste (estimativa)</button>
          </div>
          <div class="lg:col-span-2 card">
            <h2 class="font-bold text-base mb-4">Abrir chamado</h2>
            <form method="post" action="{portal_path}/chamados" class="space-y-3">
              <input name="subject" minlength="3" maxlength="100" required placeholder="Assunto — ex.: Internet sem conexão">
              <textarea name="description" minlength="5" maxlength="500" required placeholder="Descreva o problema encontrado" rows="3"></textarea>
              <button type="submit" class="btn-primary">Abrir chamado</button>
            </form>
            <div class="mt-6 pt-6 border-t border-border">
              <h3 class="text-sm font-medium text-muted mb-2">Seus chamados</h3>
              <ul>{ticket_list_html}</ul>
            </div>
          </div>
        </div>
      </section>

      <section id="tab-perfil" class="tab-panel space-y-6">
        <div><h1 class="text-xl font-bold">Contrato &amp; Perfil</h1><p class="text-sm text-muted mt-1">Seus dados cadastrais e informações contratuais.</p></div>
        <div class="grid lg:grid-cols-3 gap-6">
          <div class="lg:col-span-2 card">
            <h2 class="font-bold text-base mb-4">Dados do titular</h2>
            <dl class="grid sm:grid-cols-2 gap-4 text-sm">
              <div><dt class="text-xs text-faint">Nome completo</dt><dd class="mt-1">{full_name}</dd></div>
              <div><dt class="text-xs text-faint">Login PPPoE</dt><dd class="mt-1">{escape(login or '-')}</dd></div>
              <div><dt class="text-xs text-faint">Telefone</dt><dd class="mt-1">{escape(str(customer.get('phone') or '-'))}</dd></div>
              <div class="sm:col-span-2"><dt class="text-xs text-faint">Endereço de instalação</dt><dd class="mt-1">{escape(client_details['address']) if client_details else 'Não disponível'}</dd></div>
            </dl>
          </div>
          <div class="card">
            <h2 class="font-bold text-base mb-4">Contrato</h2>
            <dl class="space-y-3 text-sm">
              <div class="flex justify-between"><dt class="text-faint">Plano</dt><dd>{plan_name}</dd></div>
              <div class="flex justify-between"><dt class="text-faint">Tipo de conexão</dt><dd>{escape(client_details['connection_type']) if client_details else '-'}</dd></div>
              <div class="flex justify-between"><dt class="text-faint">ONU/ONT</dt><dd>{escape(client_details['onu_ont']) if client_details else '-'}</dd></div>
            </dl>
          </div>
        </div>
      </section>

      <footer class="text-center text-xs text-faint mt-10 pb-4">© {escape(organization['name'])}. Portal do cliente.</footer>
    </main>
  </div>
</div>

<nav id="mobile-tabbar" class="fixed bottom-0 inset-x-0 z-30 bg-surface/95 backdrop-blur border-t border-border grid grid-cols-5">
  <button class="nav-item flex flex-col items-center justify-center gap-1 py-2.5 text-muted" data-tab="inicio" aria-current="page"><i data-lucide="home" class="w-5 h-5"></i><span class="text-[10px]">Início</span></button>
  <button class="nav-item flex flex-col items-center justify-center gap-1 py-2.5 text-muted" data-tab="financeiro"><i data-lucide="dollar-sign" class="w-5 h-5"></i><span class="text-[10px]">Faturas</span></button>
  <button class="nav-item flex flex-col items-center justify-center gap-1 py-2.5 text-muted" data-tab="rede"><i data-lucide="wifi" class="w-5 h-5"></i><span class="text-[10px]">Rede</span></button>
  <button class="nav-item flex flex-col items-center justify-center gap-1 py-2.5 text-muted" data-tab="suporte"><i data-lucide="headphones" class="w-5 h-5"></i><span class="text-[10px]">Suporte</span></button>
  <button class="nav-item flex flex-col items-center justify-center gap-1 py-2.5 text-muted" data-tab="perfil"><i data-lucide="user" class="w-5 h-5"></i><span class="text-[10px]">Perfil</span></button>
</nav>

<script>
  lucide.createIcons();
  function showTab(name) {{
    document.querySelectorAll('.tab-panel').forEach(el => el.classList.toggle('active', el.id === 'tab-' + name));
    document.querySelectorAll('.nav-item').forEach(btn => {{ if (btn.dataset.tab === name) btn.setAttribute('aria-current','page'); else btn.removeAttribute('aria-current'); }});
    window.scrollTo({{top:0, behavior:'smooth'}});
  }}
  document.querySelectorAll('.nav-item').forEach(btn => btn.addEventListener('click', () => showTab(btn.dataset.tab)));

  function runSpeedtest() {{
    const btn = document.getElementById('btn-speedtest'), ring = document.getElementById('speed-ring'), value = document.getElementById('speed-value');
    const max = 600, circumference = 327; btn.disabled = true; btn.textContent = 'Testando...';
    let current = 0; const target = 380 + Math.round(Math.random() * 120);
    const step = setInterval(() => {{
      current += (target - current) * 0.18 + 2;
      if (current >= target) {{ current = target; clearInterval(step); btn.disabled = false; btn.textContent = 'Testar novamente (estimativa)'; }}
      value.textContent = Math.round(current); ring.style.strokeDashoffset = circumference - (current / max) * circumference;
    }}, 90);
  }}

  const usageCtx = document.getElementById('usageChart').getContext('2d');
  const gradBlue = usageCtx.createLinearGradient(0,0,0,180); gradBlue.addColorStop(0,'{primary_color}59'); gradBlue.addColorStop(1,'{primary_color}00');
  new Chart(usageCtx, {{ type:'line', data: {{ labels: Array.from({{length:13}},(_,i)=>`${{i*2}}h`),
    datasets: [{{ data: [40,60,120,260,300,250,230,270,340,460,380,180,60], borderColor:'{primary_color}', backgroundColor: gradBlue, fill:true, tension:.4, pointRadius:0, borderWidth:2 }}] }},
    options: {{ responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}},
      scales: {{ x:{{grid:{{display:false}},ticks:{{color:'#5D6B8A',font:{{size:10}}}}}}, y:{{grid:{{color:'#1B2743'}},ticks:{{color:'#5D6B8A',font:{{size:10}}}}}} }} }} }});

  let pingChartCreated = false;
  function ensurePingChart() {{
    if (pingChartCreated) return; pingChartCreated = true;
    const ctx = document.getElementById('pingChart').getContext('2d');
    new Chart(ctx, {{ type:'line', data: {{ labels: Array.from({{length:12}},(_,i)=>`${{i}}h`),
      datasets: [{{ data:[9,10,11,10,12,14,11,10,9,11,13,11], borderColor:'{primary_color}', backgroundColor:'transparent', tension:.4, pointRadius:0, borderWidth:2 }}] }},
      options: {{ responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}},
        scales: {{ x:{{grid:{{display:false}},ticks:{{color:'#5D6B8A',font:{{size:10}}}}}}, y:{{grid:{{color:'#1B2743'}},ticks:{{color:'#5D6B8A',font:{{size:10}}}}}} }} }} }});
  }}
  const _origShowTab = showTab;
  showTab = function(name) {{ _origShowTab(name); if (name === 'rede') ensurePingChart(); }};
</script>
</body></html>"""


@router.get("/cliente/chamados/{request_id}", response_class=HTMLResponse)
@router.get(
    "/portal/{organization_slug}/chamados/{request_id}",
    response_class=HTMLResponse,
)
async def client_support_detail(
    request_id: int,
    request: Request,
    organization_slug: str | None = None,
) -> str:
    organization, portal_path = _portal_organization(organization_slug)
    customer = _authenticated_customer(request, organization, organization_slug)
    organization_id = organization["id"]
    support_request = next(
        (
            item for item in list_support_requests(customer["id"], organization_id)
            if item["id"] == request_id
        ),
        None,
    )
    if support_request is None:
        raise HTTPException(404, "support_request_not_found")
    orders = await simulated_mkauth_gateway.list_work_orders(
        "bench-technician", organization_id
    )
    order = next(
        (item for item in orders if item.id == support_request["work_order_id"]),
        None,
    )
    current_status = order.status.value if order is not None else None
    stages = [
        ("assigned", "OS criada"),
        ("traveling", "Técnico em deslocamento"),
        ("arrived", "Técnico no local"),
        ("in_progress", "Atendimento em andamento"),
        ("completed", "Atendimento finalizado"),
    ]
    order_values = [item[0] for item in stages]
    current_index = order_values.index(current_status) if current_status in order_values else -1
    progress = "".join(
        f"<li class='{'done' if index <= current_index else ''}'><span>{'✓' if index < current_index else index + 1}</span>{escape(label)}</li>"
        for index, (_, label) in enumerate(stages)
    )
    exceptional = (
        f"<p class='warning'>{escape(_work_order_label(current_status))}</p>"
        if current_status in {"blocked", "not_completed"} else ""
    )
    if support_request.get("rating") is not None:
        rating_block = (
            f"<div class='thanks'><h2>Avaliação enviada</h2>"
            f"<p class='stars'>{'★' * support_request['rating']}{'☆' * (5 - support_request['rating'])}</p>"
            f"<p>{escape(support_request.get('rating_comment') or 'Sem comentário.')}</p></div>"
        )
    elif current_status == "completed":
        rating_block = f"""<div class="rating"><h2>Avalie o atendimento</h2>
<form method="post" action="{portal_path}/chamados/{request_id}/avaliar">
<label>Nota<select name="rating" required><option value="">Selecione</option><option value="5">5 — Excelente</option><option value="4">4 — Muito bom</option><option value="3">3 — Bom</option><option value="2">2 — Regular</option><option value="1">1 — Ruim</option></select></label>
<label>Comentário<textarea name="comment" maxlength="500" placeholder="Conte como foi o atendimento"></textarea></label>
<button type="submit">ENVIAR AVALIAÇÃO</button></form></div>"""
    else:
        rating_block = ""
    order_code = escape(order.code) if order is not None else "Aguardando geração da OS"
    response_block = (
        f"<div class='response'><h2>Resposta da equipe</h2><p>{escape(support_request['response'])}</p></div>"
        if support_request.get("response") else ""
    )
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Chamado #{request_id}</title>
<style>body{{margin:0;background:#f3f8f7;color:#17332f;font:16px system-ui,sans-serif}}header{{background:#075e54;color:white;padding:24px 5vw}}main{{width:min(700px,92vw);margin:24px auto}}section{{background:white;border-radius:14px;padding:20px;box-shadow:0 2px 10px #17332f18}}a{{color:#075e54}}.simulation{{background:#fff0c2;border-left:5px solid #e59b00;padding:12px}}ol{{list-style:none;padding:0;margin:24px 0}}li{{display:flex;align-items:center;gap:12px;color:#80908c;padding:10px 0;border-left:3px solid #ccd8d5;margin-left:16px;padding-left:20px}}li span{{display:grid;place-items:center;width:32px;height:32px;border-radius:50%;background:#dce6e3;color:#526561;font-weight:bold;margin-left:-38px}}li.done{{color:#075e54;border-color:#14a487;font-weight:bold}}li.done span{{background:#14a487;color:white}}.warning{{background:#fff0c2;padding:12px;border-radius:8px;color:#8a4b00}}.rating,.thanks,.response{{margin-top:24px;padding-top:14px;border-top:1px solid #dce8e5}}.response{{background:#f5fbfa;border-radius:8px;padding:14px;border-top:0}}.rating form,.rating label{{display:grid;gap:8px}}.rating form{{gap:14px}}select,textarea{{border:1px solid #aac0bb;border-radius:8px;padding:10px;font:inherit}}textarea{{min-height:90px}}button{{border:0;border-radius:8px;padding:11px;background:#075e54;color:white;font-weight:bold;cursor:pointer}}.stars{{font-size:30px;color:#e59b00}}</style></head>
<body><header><h1>Chamado #{request_id}</h1><div>{escape(support_request['subject'])}</div></header><main>
<p><a href="{portal_path}">← Voltar ao portal</a> • <a href="{portal_path}/chamados/{request_id}">Atualizar andamento</a></p><p class="simulation">Toque em “Atualizar andamento” quando desejar consultar novamente.</p>
<section><p><b>Ordem de serviço:</b> {order_code}</p><p><b>Descrição:</b> {escape(support_request['description'])}</p>{exceptional}{response_block}
<h2>Andamento do atendimento</h2><ol>{progress}</ol>{rating_block}</section></main></body></html>"""


@router.post("/cliente/chamados/{request_id}/avaliar")
@router.post("/portal/{organization_slug}/chamados/{request_id}/avaliar")
async def rate_client_support(
    request_id: int,
    request: Request,
    organization_slug: str | None = None,
) -> RedirectResponse:
    from urllib.parse import parse_qs

    organization, portal_path = _portal_organization(organization_slug)
    customer = _authenticated_customer(request, organization, organization_slug)
    organization_id = organization["id"]

    support_request = next(
        (
            item
            for item in list_support_requests(customer["id"], organization_id)
            if item["id"] == request_id
        ),
        None,
    )
    if support_request is None:
        raise HTTPException(404, "support_request_not_found")
    orders = await simulated_mkauth_gateway.list_work_orders(
        "bench-technician", organization_id
    )
    order = next(
        (item for item in orders if item.id == support_request["work_order_id"]),
        None,
    )
    if order is None or order.status.value != "completed":
        raise HTTPException(409, "work_order_not_completed")
    fields = parse_qs((await request.body()).decode("utf-8"))
    try:
        rating = int(fields.get("rating", [""])[0])
    except ValueError as error:
        raise HTTPException(422, "invalid_rating") from error
    comment = fields.get("comment", [""])[0].strip()
    if rating not in range(1, 6) or len(comment) > 500:
        raise HTTPException(422, "invalid_rating")
    save_rating(request_id, rating, comment, organization_id)
    return RedirectResponse(
        f"{portal_path}/chamados/{request_id}", status_code=303
    )


@router.post("/cliente/financeiro/{title_uuid}/pix")
@router.post("/portal/{organization_slug}/financeiro/{title_uuid}/pix")
async def portal_create_pix_charge(
    title_uuid: str,
    request: Request,
    organization_slug: str | None = None,
) -> RedirectResponse:
    organization, portal_path = _portal_organization(organization_slug)
    customer = _authenticated_customer(request, organization, organization_slug)
    organization_id = organization["id"]
    login = str(customer.get("external_login") or "").strip()
    if not login:
        raise HTTPException(404, "customer_not_linked")

    mp_config = mercado_pago_config_store.get(organization_id)
    if not mp_config.enabled or not mp_config.access_token:
        raise HTTPException(404, "pix_not_available")

    settings = get_integration_settings(organization_id)
    if settings.mkauth_mode != "real":
        raise HTTPException(404, "mkauth_not_available")
    client = MkAuthApiClient(
        settings.mkauth_base_url,
        settings.mkauth_client_id,
        settings.mkauth_client_secret,
        settings.mkauth_verify_ssl,
        settings.mkauth_allow_http and settings.app_env == "development",
    )
    try:
        title = await client.get_title(title_uuid)
    except (ValueError, httpx.HTTPError) as error:
        raise HTTPException(502, "mkauth_unavailable") from error
    if str(title.get("login") or "").casefold() != login.casefold():
        raise HTTPException(404, "title_not_found")
    paid_statuses = {"pago", "liquidado", "recebido", "baixado"}
    if str(title.get("status") or "").strip().casefold() in paid_statuses:
        raise HTTPException(409, "title_already_paid")
    amount_text = str(title.get("valor") or "").replace(",", ".").strip()
    try:
        amount = float(amount_text)
    except ValueError as error:
        raise HTTPException(422, "title_amount_invalid") from error

    external_reference = f"{organization_id}:{title_uuid}:{uuid4()}"
    base_url = str(request.base_url).rstrip("/")
    try:
        charge = mercado_pago_client.create_pix_charge(
            access_token=mp_config.access_token,
            amount=amount,
            description=f"Fatura {title.get('titulo') or title_uuid} — {organization['name']}",
            external_reference=external_reference,
            payer_email=f"{login}@cliente.invalido",
            notification_url=f"{base_url}/api/v1/financial/webhook/{organization['slug']}",
            idempotency_key=external_reference,
        )
    except MercadoPagoUnavailableError as error:
        raise HTTPException(502, str(error)) from error

    payment_record = financial_payment_store.create(
        organization_id,
        title_uuid,
        login,
        f"{amount:.2f}",
        external_reference,
        mp_payment_id=charge.payment_id,
    )
    return RedirectResponse(
        f"{portal_path}/financeiro/pix/{payment_record['id']}", status_code=303
    )


@router.get("/cliente/financeiro/pix/{payment_id}", response_class=HTMLResponse)
@router.get(
    "/portal/{organization_slug}/financeiro/pix/{payment_id}",
    response_class=HTMLResponse,
)
async def portal_show_pix_charge(
    payment_id: str,
    request: Request,
    organization_slug: str | None = None,
) -> str:
    organization, portal_path = _portal_organization(organization_slug)
    _authenticated_customer(request, organization, organization_slug)
    organization_id = organization["id"]
    try:
        payment_record = financial_payment_store.get(organization_id, payment_id)
    except KeyError as error:
        raise HTTPException(404, "payment_not_found") from error

    mp_config = mercado_pago_config_store.get(organization_id)
    qr_html = "<p>Não foi possível carregar o QR Code agora.</p>"
    if payment_record["status"] == "confirmed":
        status_html = "<p class='paid'><b>Pagamento confirmado! Seu título já foi baixado.</b></p>"
    elif mp_config.access_token and payment_record.get("mp_payment_id"):
        try:
            remote = mercado_pago_client.get_payment(
                mp_config.access_token, payment_record["mp_payment_id"]
            )
            transaction_data = remote.get("point_of_interaction", {}).get(
                "transaction_data", {}
            )
            qr_base64 = transaction_data.get("qr_code_base64", "")
            qr_code = transaction_data.get("qr_code", "")
            qr_html = (
                f"<img src='data:image/png;base64,{qr_base64}' alt='QR Code Pix' style='max-width:280px'>"
                f"<p>Ou copie o código Pix:</p><textarea readonly style='width:100%;height:80px'>{escape(qr_code)}</textarea>"
                if qr_base64 else qr_html
            )
        except MercadoPagoUnavailableError:
            pass
        status_html = (
            "<p>Aguardando confirmação do pagamento.</p>"
            f"<form method='post' action='{portal_path}/financeiro/pix/{payment_id}/verificar'>"
            "<button type='submit'>JÁ PAGUEI, VERIFICAR AGORA</button></form>"
        )
    else:
        status_html = "<p>Pagamento indisponível no momento.</p>"

    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Pagamento Pix</title>
<style>body{{margin:0;background:#f3f8f7;color:#17332f;font:16px system-ui,sans-serif}}header{{background:#075e54;color:white;padding:24px 5vw}}main{{width:min(500px,92vw);margin:24px auto;text-align:center}}section{{background:white;border-radius:14px;padding:24px;box-shadow:0 2px 10px #17332f18}}a{{color:#075e54}}button{{border:0;border-radius:8px;padding:11px 16px;background:#075e54;color:white;font-weight:bold;cursor:pointer;margin-top:12px}}.paid{{color:#0b7a4b}}</style></head>
<body><header><h1>Pagamento via Pix</h1></header><main>
<p><a href="{portal_path}">← Voltar ao portal</a></p>
<section><p>Valor: <b>R$ {escape(payment_record['amount'])}</b></p>{qr_html}{status_html}</section>
</main></body></html>"""


@router.post("/cliente/financeiro/pix/{payment_id}/verificar")
@router.post("/portal/{organization_slug}/financeiro/pix/{payment_id}/verificar")
async def portal_verify_pix_charge(
    payment_id: str,
    request: Request,
    organization_slug: str | None = None,
) -> RedirectResponse:
    organization, portal_path = _portal_organization(organization_slug)
    _authenticated_customer(request, organization, organization_slug)
    organization_id = organization["id"]
    try:
        payment_record = financial_payment_store.get(organization_id, payment_id)
    except KeyError as error:
        raise HTTPException(404, "payment_not_found") from error

    if payment_record["status"] != "confirmed" and payment_record.get("mp_payment_id"):
        mp_config = mercado_pago_config_store.get(organization_id)
        settings = get_integration_settings(organization_id)
        if mp_config.access_token and settings.mkauth_mode == "real" and settings.mkauth_writes_enabled:
            try:
                remote = mercado_pago_client.get_payment(
                    mp_config.access_token, payment_record["mp_payment_id"]
                )
            except MercadoPagoUnavailableError:
                remote = {}
            if (
                remote.get("status") == "approved"
                and str(remote.get("external_reference"))
                == payment_record["external_reference"]
            ):
                from app.api.routes.integrations import confirm_title_payment

                client = MkAuthApiClient(
                    settings.mkauth_base_url,
                    settings.mkauth_client_id,
                    settings.mkauth_client_secret,
                    settings.mkauth_verify_ssl,
                    settings.mkauth_allow_http and settings.app_env == "development",
                )
                result = await confirm_title_payment(
                    organization_id,
                    settings,
                    client,
                    payment_record["title_uuid"],
                    payment_record["login"],
                    audit_action="title_payment_confirmed_manual_check",
                )
                if result["status"] == "paid":
                    financial_payment_store.mark_confirmed(
                        organization_id, payment_id, payment_record["mp_payment_id"]
                    )
    return RedirectResponse(
        f"{portal_path}/financeiro/pix/{payment_id}", status_code=303
    )


@router.post("/cliente/desbloqueio-confianca")
@router.post("/portal/{organization_slug}/desbloqueio-confianca")
async def portal_trust_unlock(
    request: Request,
    organization_slug: str | None = None,
) -> RedirectResponse:
    organization, portal_path = _portal_organization(organization_slug)
    customer = _authenticated_customer(request, organization, organization_slug)
    organization_id = organization["id"]
    login = str(customer.get("external_login") or "").strip()
    settings = get_integration_settings(organization_id)
    if login and settings.mkauth_mode == "real" and settings.mkauth_writes_enabled:
        set_current_organization(organization_id)
        client = MkAuthApiClient(
            settings.mkauth_base_url,
            settings.mkauth_client_id,
            settings.mkauth_client_secret,
            settings.mkauth_verify_ssl,
            settings.mkauth_allow_http and settings.app_env == "development",
        )
        try:
            result = await request_trust_unlock(
                organization_id,
                TrustUnlockStore(get_settings().database_url),
                client,
                login,
                "Solicitado pelo cliente no portal",
            )
        except (ValueError, httpx.HTTPError):
            result = {"status": "error"}
        audit_store.record(
            organization_id,
            {"id": customer["id"], "name": customer.get("name") or login, "username": login, "role": "customer"},
            "trust_unlock_requested_portal",
            f"login:{login}",
            {"result": result["status"]},
        )
    else:
        trust_unlock_account(
            customer["id"],
            organization_id=organization_id,
        )
    return RedirectResponse(portal_path, status_code=303)


@router.post("/cliente/simular-pix")
@router.post("/portal/{organization_slug}/simular-pix")
async def portal_simulate_pix(
    request: Request,
    organization_slug: str | None = None,
) -> RedirectResponse:
    organization, portal_path = _portal_organization(organization_slug)
    customer = _authenticated_customer(request, organization, organization_slug)
    simulate_pix_account(
        customer["id"],
        organization_id=organization["id"],
    )
    return RedirectResponse(portal_path, status_code=303)


@router.post("/cliente/reiniciar")
@router.post("/portal/{organization_slug}/reiniciar")
async def portal_reset(
    request: Request,
    organization_slug: str | None = None,
) -> RedirectResponse:
    organization, portal_path = _portal_organization(organization_slug)
    customer = _authenticated_customer(request, organization, organization_slug)
    reset_simulated_account(
        customer["id"],
        organization_id=organization["id"],
    )
    return RedirectResponse(portal_path, status_code=303)
