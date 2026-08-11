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
from app.core.integration_config_store import get_integration_settings
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
    organization_slug: str, error: bool = False
) -> str:
    organization = organization_store.get_active_by_slug(organization_slug)
    if organization is None:
        raise HTTPException(404, "organization_not_found")
    error_message = (
        "<p class='error'>Usuário ou senha inválidos.</p>" if error else ""
    )
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
    customer = portal_customer_store.authenticate(
        organization["id"],
        fields.get("username", [""])[0],
        fields.get("password", [""])[0],
    )
    if customer is None:
        return RedirectResponse(
            f"/portal/{organization_slug}/login?error=true", status_code=303
        )
    response = RedirectResponse(f"/portal/{organization_slug}", status_code=303)
    response.set_cookie(
        PORTAL_COOKIE_NAME,
        new_portal_session(customer),
        max_age=8 * 60 * 60,
        httponly=True,
        samesite="strict",
        secure=False,
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
    settings = get_integration_settings(organization_id)
    if settings.mkauth_mode != "real":
        return (
            "<section><h2>Meus títulos</h2>"
            "<p>A consulta ao sistema financeiro ainda não está disponível.</p>"
            "</section>"
        )
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
        return (
            "<section><h2>Meus títulos</h2>"
            "<p>Não foi possível consultar seus títulos agora. Tente novamente mais tarde.</p>"
            "</section>"
        )
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
    support_contact = _support_contact(organization)
    mkauth_titles_panel = await _mkauth_titles_panel(organization_id, customer, portal_path)
    account = ensure_simulated_account(
        organization_id,
        organization["name"],
        customer["id"],
    )
    access_status = escape(_label(account["access_status"]))
    invoice_status = escape(_label(account["invoice_status"]))
    trust_message = (
        f"Liberação válida até {escape(account['trust_until'])}"
        if account.get("trust_until") else "Disponível somente para este teste de bancada."
    )
    requests = list_support_requests(customer["id"], organization_id)
    alerts = list_active_alerts(organization_id)
    network_notice = (
        "".join(
            f"<div class='network-alert'><b>{escape(alert.title)}</b><br>"
            f"Área afetada: {escape(alert.area)}<br>"
            f"<small>Nossa equipe já foi informada. Evite abrir chamados duplicados.</small></div>"
            for alert in alerts
        )
        if alerts else
        "<div class='network-ok'><b>Rede sem ocorrências gerais comunicadas.</b></div>"
    )
    orders = {
        order.id: order
        for order in await simulated_mkauth_gateway.list_work_orders(
            "bench-technician", organization_id
        )
    }
    rows = []
    for item in requests[:5]:
        order = orders.get(item["work_order_id"])
        if order is not None:
            status = f"{order.code} • {_work_order_label(order.status.value)}"
        elif item["status"] == "converted":
            status = "OS gerada — aguardando atualização"
        elif item["status"] == "answered":
            status = "Respondido pela equipe"
        else:
            status = "Chamado recebido — aguardando a central"
        rows.append(
            f"<tr><td>#{item['id']}</td><td>{escape(item['subject'])}</td>"
            f"<td><a class='ticket-status' href='{portal_path}/chamados/{item['id']}'>{escape(status)}</a></td></tr>"
        )
    request_rows = "".join(rows) or "<tr><td colspan='3'>Nenhum chamado aberto.</td></tr>"
    logout_form = (
        f'<form method="post" action="{portal_path}/logout">'
        '<button type="submit">SAIR</button></form>'
        if organization_slug is not None
        else ""
    )
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Portal do Cliente</title>
<style>:root{{--green:#075e54;--mint:#d8f3ee;--ink:#17332f}}*{{box-sizing:border-box}}body{{margin:0;background:#f3f8f7;color:var(--ink);font:16px system-ui,sans-serif}}header{{background:var(--green);color:white;padding:24px 5vw}}header h1{{margin:0}}main{{width:min(720px,92vw);margin:24px auto}}.simulation{{background:#fff0c2;border-left:5px solid #e59b00;padding:13px;border-radius:8px}}.network-alert{{background:#ffe1d5;border-left:5px solid #d34a21;padding:15px;border-radius:8px;margin:16px 0}}.network-ok{{background:#dff5ea;border-left:5px solid #16845f;padding:15px;border-radius:8px;margin:16px 0}}section{{background:white;border-radius:14px;padding:20px;margin:16px 0;box-shadow:0 2px 10px #17332f18}}.status{{display:inline-block;background:var(--mint);color:var(--green);padding:7px 11px;border-radius:999px;font-weight:bold}}.ticket-status{{display:inline-block;border-left:4px solid var(--green);padding:7px 9px;background:#edf7f4;color:var(--green);text-decoration:none;font-weight:600}}.ticket-status:hover{{text-decoration:underline}}.amount{{font-size:36px;font-weight:bold;margin:8px 0}}.actions{{display:flex;flex-wrap:wrap;gap:10px}}form{{margin:0}}button{{border:0;border-radius:9px;padding:12px 15px;background:var(--green);color:white;font:inherit;font-weight:bold;cursor:pointer}}button.secondary{{background:#d78200}}button.reset{{background:#647773}}input,textarea{{width:100%;border:1px solid #aac0bb;border-radius:8px;padding:10px;font:inherit}}textarea{{min-height:90px;resize:vertical}}table{{width:100%;border-collapse:collapse}}th,td{{padding:9px;border-bottom:1px solid #dce8e5;text-align:left}}code{{display:block;padding:12px;background:#edf3f1;border-radius:8px;overflow-wrap:anywhere}}small{{color:#627773}}</style></head>
<body><style>:root{{--green:{primary_color}}}</style><header><h1>{escape(organization['name'])}</h1><div>Portal do Cliente — {escape(customer['name'])}</div>{support_contact}</header><main>
{logout_form}
<p class="simulation"><b>MODO SIMULADO</b> — nenhum pagamento ou desbloqueio real será realizado.</p>
{network_notice}
{mkauth_titles_panel}
<section><h2>Minha conexão</h2><p class="status">{access_status}</p><p>{trust_message}</p></section>
<section><h2>Minha fatura</h2><div class="amount">R$ {account['invoice_amount']:.2f}</div><p>Situação: <b>{invoice_status}</b></p>
<p>Código Pix exclusivamente fictício:</p><code>PIX-SIMULADO-{escape(account['invoice_id'].upper())}-NAO-PAGAR</code></section>
<section><h2>Serviços disponíveis</h2><div class="actions">
<form method="post" action="{portal_path}/desbloqueio-confianca"><button class="secondary" type="submit">Liberar por 48 horas</button></form>
<form method="post" action="{portal_path}/simular-pix"><button type="submit">Simular pagamento Pix</button></form>
<form method="post" action="{portal_path}/reiniciar"><button class="reset" type="submit">Reiniciar simulação</button></form>
</div><p><small>Na integração real, as regras e permissões serão consultadas no MK-AUTH antes de qualquer ação.</small></p></section>
<section><h2>Solicitar suporte</h2><form method="post" action="{portal_path}/chamados">
<p><label>Assunto<br><input name="subject" minlength="3" maxlength="100" required placeholder="Ex.: Internet sem conexão"></label></p>
<p><label>Descrição<br><textarea name="description" minlength="5" maxlength="500" required placeholder="Descreva o problema encontrado"></textarea></label></p>
<button type="submit">ABRIR CHAMADO</button></form>
<h3>Acompanhe meus chamados</h3><p><a class="ticket-status" href="{portal_path}">ATUALIZAR ANDAMENTO</a></p><table><thead><tr><th>Número</th><th>Assunto</th><th>Andamento</th></tr></thead><tbody>{request_rows}</tbody></table></section>
</main></body></html>"""


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
<p><a href="{portal_path}">← Voltar ao portal</a> • <a href="{portal_path}/chamados/{request_id}">Atualizar andamento</a></p><p class="simulation"><b>MODO SIMULADO</b> — use “Atualizar andamento” quando desejar consultar novamente.</p>
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
    trust_unlock_account(
        customer["id"],
        organization_id=organization["id"],
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
