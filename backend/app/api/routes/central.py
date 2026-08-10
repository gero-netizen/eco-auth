from html import escape
from datetime import datetime, timezone
import json
import re
import secrets
from urllib.parse import parse_qs

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.routes.evidence import list_equipment, list_evidence
from app.api.routes.olt import provisioning_store
from app.integrations.mkauth.client import simulated_mkauth_gateway
from app.integrations.mkauth.inventory import simulated_inventory_gateway
from app.api.routes.financial import list_financial_accounts
from app.api.routes.notifications import (
    list_simulated_messages,
    record_simulated_portal_invite_message,
)
from app.api.routes.support import list_support_requests
from app.api.routes.network import list_active_alerts
from app.api.routes.central_auth import (
    require_central_access,
    require_central_roles,
    require_central_session,
)
from app.core.central_user_store import CENTRAL_USER_ROLES, central_user_store
from app.core.audit_store import audit_store
from app.core.technician_store import technician_store
from app.core.config import get_settings
from app.core.integration_config_store import (
    get_integration_settings,
    integration_config_store,
)
from app.core.subscription_store import SAAS_PLANS, subscription_store
from app.core.portal_customer_store import portal_customer_store
from app.core.portal_invite_store import portal_invite_store
from app.core.organization_store import organization_store
from app.integrations.mkauth.api_client import MkAuthApiClient

router = APIRouter(
    tags=["central-dashboard"],
    dependencies=[Depends(require_central_access)],
)


@router.get("/central", response_class=HTMLResponse)
async def central_dashboard(
    session: dict = Depends(require_central_session),
) -> str:
    organization_id = session["organization"]["id"]
    all_orders = await simulated_mkauth_gateway.list_work_orders(None)
    orders = [
        order
        for order in all_orders
        if order.archived_at is None and order.deleted_at is None
    ]
    archived_orders = [
        order
        for order in all_orders
        if order.archived_at is not None and order.deleted_at is None
    ]
    inventory = await simulated_inventory_gateway.list_items(
        "bench-technician", organization_id
    )
    inventory_movements = simulated_inventory_gateway.list_movements(
        organization_id=organization_id
    )
    provisioning = provisioning_store.list_for_work_order(
        "sim-os-1", organization_id
    )
    financial_accounts = list_financial_accounts(organization_id)
    messages = list_simulated_messages(organization_id)[:5]
    support_requests = list_support_requests(organization_id=organization_id)
    network_alerts = list_active_alerts(organization_id)
    technicians = technician_store.list_all(organization_id)
    integration_config_store.ensure_unconfigured(organization_id)
    mkauth_settings = get_integration_settings(organization_id)
    active_technicians = [item for item in technicians if item["active"]]
    technician_names = {item["id"]: item["name"] for item in technicians}
    technician_options = "".join(
        f"<option value='{escape(item['id'])}'>{escape(item['name'])}</option>"
        for item in active_technicians
    )
    def mkauth_ticket_action(order) -> str:
        if not order.external_ticket_id or order.status.value != "completed":
            return ""
        if order.external_ticket_closed_at is not None:
            return " <span class='status'>Chamado MK-AUTH fechado</span>"
        return (
            f" <a class='button-link secondary-link' "
            f"href='/central/work-orders/{escape(order.id)}/mkauth-close'>"
            "FECHAR CHAMADO MK-AUTH</a>"
        )
    def archive_action(order) -> str:
        if order.status.value not in {"completed", "not_completed"}:
            return ""
        if order.external_ticket_id and order.external_ticket_closed_at is None:
            return " <span class='alert'>Feche o chamado MK-AUTH antes de arquivar</span>"
        return (
            f" <form method='post' action='/central/work-orders/{escape(order.id)}/archive'>"
            "<button class='secondary' type='submit'>ARQUIVAR OS</button></form>"
        )
    def delete_action(order) -> str:
        if order.status.value != "assigned":
            return ""
        return (
            f" <a class='button-link danger-link' "
            f"href='/central/work-orders/{escape(order.id)}/delete'>EXCLUIR OS</a>"
        )
    pending = sum(
        order.status.value not in {"completed", "not_completed"}
        for order in orders
    )
    low_stock = sum(item.quantity <= 5 for item in inventory)
    order_rows = "".join(
        f"<tr><td>{escape(order.code)}</td>"
        f"<td>{escape(order.customer_name)}</td>"
        f"<td><span class='status'>{escape(order.status.value)}</span></td>"
        f"<td><b>{escape({'low': 'Baixa', 'normal': 'Normal', 'high': 'Alta', 'urgent': 'Urgente'}.get(order.priority, order.priority))}</b></td>"
        f"<td><form method='post' action='/central/work-orders/{escape(order.id)}/planning'>"
        f"<select name='priority'>"
        + "".join(
            f"<option value='{value}' {'selected' if value == order.priority else ''}>{label}</option>"
            for value, label in (("low", "Baixa"), ("normal", "Normal"), ("high", "Alta"), ("urgent", "Urgente"))
        )
        + f"</select><input name='scheduled_at' type='datetime-local' value='{order.scheduled_at.astimezone().strftime('%Y-%m-%dT%H:%M') if order.scheduled_at else ''}'>"
        f"<button type='submit'>SALVAR</button></form></td>"
        f"<td>{escape(technician_names.get(order.technician_id, 'Não atribuído'))}"
        f"<form method='post' action='/central/work-orders/{escape(order.id)}/assign'>"
        f"<select name='technician_id'>"
        + "".join(
            f"<option value='{escape(item['id'])}' {'selected' if item['id'] == order.technician_id else ''}>"
            f"{escape(item['name'])}</option>"
            for item in active_technicians
        )
        + "</select><button type='submit'>TRANSFERIR</button></form></td>"
        f"<td><a class='button-link' href='/central/work-orders/{escape(order.id)}/evidence'>Comprovações</a> "
        f"<a class='button-link secondary-link' href='/central/work-orders/{escape(order.id)}/report'>Relatório</a>"
        f"{mkauth_ticket_action(order)}{archive_action(order)}{delete_action(order)}</td></tr>"
        for order in orders
    )
    archived_order_rows = "".join(
        f"<tr><td>{escape(order.code)}</td><td>{escape(order.customer_name)}</td>"
        f"<td>{escape(order.status.value)}</td>"
        f"<td>{escape(order.archived_at.isoformat() if order.archived_at else '-')}</td>"
        f"<td><a class='button-link secondary-link' href='/central/work-orders/{escape(order.id)}/report'>Relatório</a> "
        f"<form method='post' action='/central/work-orders/{escape(order.id)}/restore'>"
        f"<button type='submit'>RESTAURAR</button></form></td></tr>"
        for order in archived_orders
    ) or "<tr><td colspan='5'>Nenhuma OS arquivada.</td></tr>"
    inventory_rows = "".join(
        f"<tr><td>{escape(item.description)}</td>"
        f"<td>{item.quantity:g} {escape(item.unit)}</td>"
        f"<td>{escape(item.serial_number or '-')}</td>"
        f"<td><form method='post' action='/api/v1/inventory/{escape(item.id)}/restock-from-central'>"
        f"<input class='quantity' name='quantity' type='number' min='0.1' max='10000' step='0.1' required placeholder='Qtd.'>"
        f"<button type='submit'>REPOR</button></form></td></tr>"
        for item in inventory
    )
    movement_rows = "".join(
        f"<tr><td>{escape(item['description'])}</td>"
        f"<td>{'Reposição' if item['kind'] == 'restock' else 'Consumo'}</td>"
        f"<td>{item['quantity']:g} {escape(item['unit'])}</td>"
        f"<td>{escape(item['work_order_id'] or '-')}</td>"
        f"<td>{'Central' if item['source'] == 'central' else 'Técnico'}</td>"
        f"<td>{escape(item['created_at'])}</td></tr>"
        for item in inventory_movements[:20]
    ) or "<tr><td colspan='6'>Nenhuma movimentação registrada.</td></tr>"
    provisioning_rows = "".join(
        f"<tr><td>{escape(str(item['serial']))}</td>"
        f"<td>{escape(str(item.get('profile') or '-'))}</td>"
        f"<td>{escape(str(item['created_at']))}</td></tr>"
        for item in provisioning[:5]
    ) or "<tr><td colspan='3'>Nenhum provisionamento registrado</td></tr>"
    financial_rows = "".join(
        f"<tr><td>{escape(account['customer_name'])}</td>"
        f"<td>R$ {account['invoice_amount']:.2f}</td>"
        f"<td><span class='status'>{escape(account['invoice_status'])}</span></td>"
        f"<td>{escape(account['access_status'])}</td>"
        f"<td><form method='post' action='/api/v1/financial/accounts/{account['id']}/trust-unlock?redirect=true'>"
        f"<button class='secondary' type='submit'>Confiança 48h</button></form> "
        f"<form method='post' action='/api/v1/financial/accounts/{account['id']}/simulate-pix?redirect=true'>"
        f"<button type='submit'>Simular Pix</button></form></td></tr>"
        for account in financial_accounts
    )
    def message_content(message: dict) -> str:
        content = escape(message["message"])
        if message.get("template") == "portal_access_invite":
            invite_url = str(message["message"]).rsplit(" ", 1)[-1]
            content += (
                f"<br><a class='button-link' href='{escape(invite_url)}' "
                "target='_blank' rel='noopener'>ABRIR CONVITE</a>"
            )
        return content

    message_rows = "".join(
        f"<tr><td>{escape(message['template'])}</td>"
        f"<td>{escape(message.get('login', '-'))}</td>"
        f"<td>{escape(message['recipient'])}</td>"
        f"<td>{message_content(message)}</td>"
        f"<td>{escape(message['status'])}</td>"
        f"<td>{escape(message['created_at'])}</td></tr>"
        for message in messages
    ) or "<tr><td colspan='6'>Nenhuma mensagem simulada</td></tr>"
    support_rows = "".join(
        f"<tr><td>#{item['id']}</td><td>{escape(item['subject'])}</td>"
        f"<td>{escape(item['description'])}</td><td>{escape(item['status'])}</td>"
        f"<td>{escape(item['work_order_id'] or '-')}</td>"
        f"<td>{('★' * item['rating']) if item.get('rating') else '-'}</td><td>"
        + (
            f"<form method='post' action='/central/chamados/{item['id']}/gerar-os'><button type='submit'>GERAR OS</button></form>"
            if item["work_order_id"] is None else "Convertido"
        )
        + "</td></tr>"
        for item in support_requests[:10]
    ) or "<tr><td colspan='7'>Nenhum chamado recebido.</td></tr>"
    network_rows = "".join(
        f"<tr><td>{escape(alert.title)}</td><td>{escape(alert.area)}</td>"
        f"<td>{escape(alert.detected_at.isoformat())}</td></tr>"
        for alert in network_alerts
    ) or "<tr><td colspan='3'>Nenhuma ocorrência ativa.</td></tr>"
    current_user = session["user"]
    can_manage_technicians = current_user["role"] in {"owner", "admin"}
    technician_rows = "".join(
        f"<tr><td>{escape(item['name'])}</td><td>{escape(item['username'])}</td>"
        f"<td>{'Ativo' if item['active'] else 'Inativo'}</td><td>"
        + (
            f"<form method='post' action='/central/technicians/{escape(item['id'])}/toggle'>"
            f"<input type='hidden' name='active' value='{'0' if item['active'] else '1'}'>"
            f"<button class='{'secondary' if item['active'] else ''}' type='submit'>"
            f"{'DESATIVAR' if item['active'] else 'ATIVAR'}</button></form>"
            if can_manage_technicians
            else "-"
        )
        + "</td></tr>"
        for item in technicians
    )
    technician_form = ""
    if can_manage_technicians:
        technician_form = """
        <form class="create-order" method="post" action="/central/technicians">
          <label>Nome<input name="name" minlength="3" maxlength="100" required></label>
          <label>Usuário<input name="username" minlength="3" maxlength="80" required></label>
          <label>Senha inicial<input name="password" type="password" minlength="8" maxlength="200" required></label>
          <button type="submit">CADASTRAR</button>
        </form>"""
    can_manage_users = current_user["role"] in {"owner", "admin"}
    all_central_users = central_user_store.list_all(organization_id)
    central_users = (
        all_central_users
        if can_manage_users
        else [current_user]
    )
    role_labels = {
        "owner": "Proprietário",
        "admin": "Administrador",
        "attendant": "Atendente",
        "viewer": "Somente leitura",
    }
    central_user_rows = "".join(
        f"<tr><td>{escape(item['name'])}</td><td>{escape(item['username'])}</td>"
        f"<td>{escape(role_labels.get(item['role'], item['role']))}</td>"
        f"<td>{'Ativo' if item['active'] else 'Inativo'}</td><td>"
        + (
            f"<form method='post' action='/central/users/{escape(item['id'])}/toggle'>"
            f"<input type='hidden' name='active' value='{'0' if item['active'] else '1'}'>"
            f"<button class='{'secondary' if item['active'] else ''}' type='submit'>"
            f"{'DESATIVAR' if item['active'] else 'ATIVAR'}</button></form>"
            if can_manage_users and item["id"] != current_user["id"]
            else "-"
        )
        + "</td></tr>"
        for item in central_users
    )
    central_user_form = ""
    if can_manage_users:
        allowed_roles = ["admin", "attendant", "viewer"]
        if current_user["role"] == "owner":
            allowed_roles.insert(0, "owner")
        role_options = "".join(
            f"<option value='{role}'>{escape(role_labels[role])}</option>"
            for role in allowed_roles
        )
        central_user_form = (
            "<form class='create-order' method='post' action='/central/users'>"
            "<label>Nome<input name='name' minlength='3' maxlength='100' required></label>"
            "<label>Usuário<input name='username' minlength='3' maxlength='80' required></label>"
            "<label>Senha inicial<input name='password' type='password' minlength='8' maxlength='200' required></label>"
            f"<label>Perfil<select name='role' required>{role_options}</select></label>"
            "<button type='submit'>CADASTRAR</button></form>"
        )
    portal_customers = portal_customer_store.list_all(organization_id)
    portal_accesses_json = json.dumps(
        [
            {
                "external_customer_id": item.get("external_customer_id") or "",
                "external_login": item.get("external_login") or "",
                "active": bool(item["active"]),
            }
            for item in portal_customers
        ],
        ensure_ascii=True,
    ).replace("<", "\\u003c")
    branding_panel = (
        "<section class='module-panel' data-module='branding'><h2>Identidade do provedor</h2>"
        "<p>Estas informações personalizam o Portal do Cliente desta organização.</p>"
        "<form class='create-order' method='post' action='/central/branding'>"
        f"<label>Nome comercial<input name='name' minlength='3' maxlength='100' value='{escape(session['organization']['name'])}' required></label>"
        f"<label>Cor principal<input name='primary_color' type='color' value='{escape(session['organization'].get('primary_color') or '#075e54')}' required></label>"
        f"<label>E-mail de suporte<input name='support_email' type='email' maxlength='150' value='{escape(session['organization'].get('support_email') or '')}'></label>"
        f"<label>Telefone/WhatsApp<input name='support_phone' maxlength='30' value='{escape(session['organization'].get('support_phone') or '')}'></label>"
        "<button type='submit'>SALVAR IDENTIDADE</button></form></section>"
        if can_manage_users
        else "<section class='module-panel' data-module='branding'><h2>Identidade do provedor</h2><p>Somente proprietários e administradores podem alterar estes dados.</p></section>"
    )
    portal_customer_rows = "".join(
        f"<tr><td>{escape(item['name'])}</td><td>{escape(item['username'])}</td>"
        f"<td>{escape(item['external_login'] or 'Não vinculado')}</td>"
        f"<td>{escape(item['external_customer_id'] or '-')}</td>"
        f"<td>{'Ativo' if item['active'] else 'Inativo'}</td><td>"
        + (
            f"<form method='post' action='/central/portal-customers/{escape(item['id'])}/toggle'>"
            f"<input type='hidden' name='active' value='{'0' if item['active'] else '1'}'>"
            f"<button class='{'secondary' if item['active'] else ''}' type='submit'>"
            f"{'DESATIVAR' if item['active'] else 'ATIVAR'}</button></form>"
            f"<form method='post' action='/central/portal-customers/{escape(item['id'])}/password'>"
            "<input name='password' type='password' minlength='8' maxlength='200' placeholder='Nova senha' required>"
            "<button type='submit'>REDEFINIR SENHA</button></form>"
            f"<form method='post' action='/central/portal-customers/{escape(item['id'])}/link'>"
            f"<input name='external_login' value='{escape(item['external_login'] or '')}' placeholder='Login MK-AUTH' required>"
            f"<input name='external_customer_id' value='{escape(item['external_customer_id'] or '')}' placeholder='Identificador MK-AUTH' required>"
            "<button type='submit'>VINCULAR</button></form>"
            if can_manage_users else "-"
        ) + "</td></tr>"
        for item in portal_customers
    ) or "<tr><td colspan='6'>Nenhum cliente cadastrado.</td></tr>"
    subscription = subscription_store.get_or_create(organization_id)
    subscription_plan = subscription["plan"]
    active_user_count = sum(bool(item["active"]) for item in all_central_users)
    active_technician_count = sum(bool(item["active"]) for item in technicians)
    subscription_status_labels = {
        "trialing": "Período de teste",
        "active": "Ativa",
        "past_due": "Pagamento pendente",
        "canceled": "Cancelada",
        "trial_expired": "Período de teste encerrado",
    }
    plan_options = "".join(
        f"<option value='{escape(code)}' {'selected' if code == subscription['plan_code'] else ''}>"
        f"{escape(plan['name'])} — R$ {plan['monthly_price']:.2f}/mês</option>"
        for code, plan in SAAS_PLANS.items()
    )
    plan_change_form = (
        "<form method='post' action='/central/subscription/simulate-plan'>"
        f"<label>Simular plano<select name='plan_code'>{plan_options}</select></label>"
        "<button type='submit'>APLICAR NA BANCADA</button></form>"
        if current_user["role"] == "owner"
        else ""
    )
    subscription_panel = (
        "<section class='module-panel' data-module='subscription'><h2>Plano e assinatura</h2>"
        "<p><b>Ambiente de bancada:</b> nenhuma cobrança real será realizada nesta etapa.</p>"
        f"<p><b>Plano:</b> {escape(subscription_plan['name'])} — R$ {subscription_plan['monthly_price']:.2f}/mês</p>"
        f"<p><b>Situação:</b> {escape(subscription_status_labels.get(subscription['status'], subscription['status']))}</p>"
        f"<p><b>Fim do teste:</b> {escape(subscription['trial_ends_at'] or '-')}</p>"
        f"<p><b>Usuários da central:</b> {active_user_count}/{subscription_plan['max_central_users']}</p>"
        f"<p><b>Técnicos:</b> {active_technician_count}/{subscription_plan['max_technicians']}</p>"
        f"{plan_change_form}</section>"
    )
    audit_rows = ""
    if can_manage_users:
        action_labels = {
            "POST": "Alteração",
            "PUT": "Atualização",
            "PATCH": "Atualização",
            "DELETE": "Exclusão",
        }
        audit_rows = "".join(
            f"<tr><td>{escape(item['created_at'])} UTC</td>"
            f"<td>{escape(item['user_name'])} ({escape(item['username'])})</td>"
            f"<td>{escape(role_labels.get(item['role'], item['role']))}</td>"
            f"<td>{escape(action_labels.get(item['action'], item['action']))}</td>"
            f"<td><code>{escape(item['target'])}</code></td></tr>"
            for item in audit_store.list_recent(organization_id, 200)
        ) or "<tr><td colspan='5'>Nenhuma ação registrada ainda.</td></tr>"
    audit_menu = (
        '<details class="menu-category"><summary>Segurança</summary><div class="menu-items">'
        '<button class="menu-button" type="button" data-target="audit">Auditoria</button>'
        '</div></details>'
        if can_manage_users
        else ""
    )
    audit_panel = (
        "<section class='module-panel' data-module='audit'><h2>Auditoria</h2>"
        "<p>Registro das alterações realizadas nesta organização. Os dados de outros provedores nunca aparecem aqui.</p>"
        "<table><thead><tr><th>Data</th><th>Usuário</th><th>Perfil</th><th>Ação</th><th>Destino</th></tr></thead>"
        f"<tbody>{audit_rows}</tbody></table></section>"
        if can_manage_users
        else ""
    )
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Painel da Central</title>
  <style>
    :root {{ color-scheme: light; --green:#075e54; --mint:#d8f3ee; --ink:#17332f; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:#f3f8f7; color:var(--ink); font:16px system-ui,sans-serif; }}
    header {{ background:var(--green); color:white; padding:22px 5vw; }}
    header h1 {{ margin:0 0 4px; }}
    main {{ width:min(1420px,94vw); margin:24px auto 48px; }}
    .simulation {{ background:#fff0c2; border-left:5px solid #e59b00; padding:14px; border-radius:8px; }}
    .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:14px; margin:20px 0; }}
    .card, section {{ background:white; border-radius:14px; box-shadow:0 2px 10px #17332f18; }}
    .card {{ padding:18px; }} .card strong {{ display:block; font-size:30px; color:var(--green); }}
    .dashboard-layout {{ display:grid; grid-template-columns:270px minmax(0,1fr); gap:18px; align-items:start; }}
    .sidebar {{ position:sticky; top:18px; background:white; border-radius:14px; box-shadow:0 2px 10px #17332f18; padding:12px; }}
    .sidebar-title {{ margin:4px 8px 10px; color:#627773; font-size:13px; font-weight:700; text-transform:uppercase; letter-spacing:.06em; }}
    .menu-category {{ border-bottom:1px solid #e3ecea; padding:3px 0; }}
    .menu-category:last-child {{ border-bottom:0; }}
    .menu-category summary {{ list-style:none; cursor:pointer; padding:10px 9px; border-radius:9px; color:#456b65; font-size:13px; font-weight:800; text-transform:uppercase; letter-spacing:.04em; }}
    .menu-category summary::-webkit-details-marker {{ display:none; }}
    .menu-category summary::after {{ content:'▸'; float:right; transition:transform .15s ease; }}
    .menu-category[open] summary::after {{ transform:rotate(90deg); }}
    .menu-category summary:hover {{ background:#f2f8f6; }}
    .menu-items {{ padding:0 3px 5px; }}
    .menu-button {{ display:block; width:100%; padding:11px 12px; margin:2px 0; border-radius:9px; background:transparent; color:var(--ink); text-align:left; font-weight:600; }}
    .menu-button:hover {{ background:#edf7f5; }}
    .menu-button.active {{ background:var(--green); color:white; }}
    .module-area {{ min-width:0; }}
    .module-panel {{ display:none; }}
    .module-panel.active {{ display:block; }}
    section {{ padding:18px; overflow:auto; }} h2 {{ margin-top:0; font-size:20px; }}
    table {{ width:100%; border-collapse:collapse; }} th,td {{ padding:11px 8px; border-bottom:1px solid #dce8e5; text-align:left; }}
    .status {{ background:var(--mint); color:var(--green); padding:4px 8px; border-radius:999px; }}
    .client-state {{ display:inline-block; padding:4px 9px; border-radius:999px; font-weight:700; }}
    .client-state.active {{ background:#d8f3dc; color:#176b2c; }}
    .client-state.blocked {{ background:#ffe0de; color:#a51d16; }}
    tr.client-blocked {{ background:#fff5f4; }}
    tr.client-active {{ background:#f5fff7; }}
    button {{ border:0; border-radius:8px; padding:9px 12px; background:var(--green); color:white; cursor:pointer; }}
    .button-link {{ display:inline-block; border-radius:8px; padding:8px 10px; background:var(--green); color:white; text-decoration:none; white-space:nowrap; }}
    .secondary-link {{ background:#456b65; }}
    .danger-link {{ background:#b42318; }}
    button.secondary {{ background:#e59b00; }} form {{ display:inline-block; margin:2px; }}
    .create-order {{ display:grid; grid-template-columns:1.2fr 1.4fr .7fr .7fr auto; gap:10px; align-items:end; margin-bottom:18px; }}
    .create-order label {{ display:grid; gap:5px; }}
    input,select {{ border:1px solid #aac0bb; border-radius:8px; padding:10px; font:inherit; min-width:0; background:white; }}
    input.quantity {{ width:85px; padding:8px; }}
    @media(max-width:850px) {{
      .dashboard-layout {{ grid-template-columns:1fr; }}
      .sidebar {{ position:static; display:block; padding:10px; }}
      .sidebar-title {{ display:none; }}
      .menu-button {{ width:100%; white-space:normal; }}
    }}
    @media(max-width:700px) {{ .create-order {{ grid-template-columns:1fr; }} }}
    .alert {{ color:#8a4b00; }} footer {{ margin-top:20px; color:#627773; }}
    .role-viewer form:not(.logout-form) {{ display:none !important; }}
    .role-viewer .danger-link {{ display:none !important; }}
    .role-viewer .portal-manage-button, .role-attendant .portal-manage-button {{ display:none !important; }}
  </style>
</head>
<body class="role-{escape(current_user['role'])}">
  <header><h1>Painel da Central</h1><div>{escape(session['organization']['name'])} • {escape(current_user['name'])} • {escape(role_labels[current_user['role']])}</div><form class="logout-form" method="post" action="/central/logout"><button class="secondary" type="submit">SAIR</button></form></header>
  <main>
    <div class="simulation"><b>MODO SIMULADO</b> — nenhum dado desta tela representa clientes ou equipamentos reais.</div>
    <div class="cards">
      <div class="card"><span>Ordens de serviço</span><strong>{len(orders)}</strong></div>
      <div class="card"><span>OS pendentes</span><strong>{pending}</strong></div>
      <div class="card"><span>Itens com estoque baixo</span><strong>{low_stock}</strong></div>
      <div class="card"><span>Provisionamentos</span><strong>{len(provisioning)}</strong></div>
    </div>
    <div class="dashboard-layout">
      <nav class="sidebar" aria-label="Módulos da central">
        <div class="sidebar-title">Menu da central</div>
        <details class="menu-category" open><summary>Operação</summary><div class="menu-items">
          <button class="menu-button active" type="button" data-target="work-orders">Abrir OS simulada</button>
          <button class="menu-button" type="button" data-target="archived-orders">OS arquivadas</button>
          <button class="menu-button" type="button" data-target="inventory">Estoque do técnico</button>
          <button class="menu-button" type="button" data-target="materials">Histórico de materiais</button>
          <button class="menu-button" type="button" data-target="technicians">Técnicos</button>
        </div></details>
        <details class="menu-category"><summary>Clientes</summary><div class="menu-items">
          <button class="menu-button" type="button" data-target="portal-customers">Clientes do portal</button>
          <button class="menu-button" type="button" data-target="mkauth-clients">Clientes MK-AUTH</button>
          <button class="menu-button" type="button" data-target="mkauth-inactive-clients">Clientes desativados</button>
          <button class="menu-button" type="button" data-target="mkauth-additional-clients">Clientes adicionais</button>
        </div></details>
        <details class="menu-category"><summary>Financeiro</summary><div class="menu-items">
          <button class="menu-button" type="button" data-target="financial">Financeiro e desbloqueio</button>
          <button class="menu-button" type="button" data-target="mkauth-titles">Títulos MK-AUTH</button>
        </div></details>
        <details class="menu-category"><summary>Rede</summary><div class="menu-items">
          <button class="menu-button" type="button" data-target="network">Monitoramento da rede</button>
          <button class="menu-button" type="button" data-target="routeros-diagnostic">Diagnóstico PPPoE/RADIUS</button>
          <button class="menu-button" type="button" data-target="provisioning">Últimos provisionamentos</button>
        </div></details>
        <details class="menu-category"><summary>Atendimento</summary><div class="menu-items">
          <button class="menu-button" type="button" data-target="support">Chamados do portal do cliente</button>
          <button class="menu-button" type="button" data-target="mkauth-tickets">Chamados MK-AUTH</button>
          <button class="menu-button" type="button" data-target="whatsapp">WhatsApp simulado</button>
        </div></details>
        <details class="menu-category"><summary>Configurações</summary><div class="menu-items">
          <button class="menu-button" type="button" data-target="mkauth">Integração MK-AUTH</button>
          <button class="menu-button" type="button" data-target="central-users">Usuários da central</button>
          <button class="menu-button" type="button" data-target="branding">Identidade do provedor</button>
          <button class="menu-button" type="button" data-target="subscription">Plano e assinatura</button>
        </div></details>
        {audit_menu}
      </nav>
      <div class="module-area">
      <section class="module-panel active" data-module="work-orders">
        <h2>Abrir OS simulada</h2>
        <p>A OS será criada somente neste aplicativo e chegará ao celular na próxima sincronização. O cadastro do MK-AUTH não será alterado.</p>
        <form class="create-order" method="post" action="/api/v1/work-orders/from-central">
          <input id="order-external-customer-id" name="external_customer_id" type="hidden">
          <input id="order-external-ticket-id" name="external_ticket_id" type="hidden">
          <label>Selecionar cliente<select id="mkauth-client-select"><option value="">Cliente manual/fictício</option></select></label>
          <label>Cliente<input id="order-customer-name" name="customer_name" minlength="3" maxlength="100" required placeholder="Ex.: Cliente Teste 02"></label>
          <label>Endereço<input id="order-address" name="address" minlength="3" maxlength="200" required placeholder="Ex.: Rua de Testes, 20"></label>
          <label>Latitude<input id="order-latitude" name="latitude" inputmode="decimal" placeholder="-12.9714"></label>
          <label>Longitude<input id="order-longitude" name="longitude" inputmode="decimal" placeholder="-38.5014"></label>
          <label>Prioridade<select id="order-priority" name="priority"><option value="low">Baixa</option><option value="normal" selected>Normal</option><option value="high">Alta</option><option value="urgent">Urgente</option></select></label>
          <label>Data e horário<input name="scheduled_at" type="datetime-local"></label>
          <label>Técnico<select name="technician_id" required>{technician_options}</select></label>
          <button type="submit">CRIAR OS</button>
        </form>
        <p id="order-source-status"></p>
        <table><thead><tr><th>OS</th><th>Cliente</th><th>Status</th><th>Prioridade</th><th>Agendamento</th><th>Técnico</th><th></th></tr></thead><tbody>{order_rows}</tbody></table>
      </section>
      <section class="module-panel" data-module="archived-orders">
        <h2>OS arquivadas</h2>
        <p>As ordens arquivadas não aparecem na lista operacional, mas continuam disponíveis para consulta e restauração.</p>
        <table><thead><tr><th>OS</th><th>Cliente</th><th>Status</th><th>Arquivada em UTC</th><th>Ação</th></tr></thead><tbody>{archived_order_rows}</tbody></table>
      </section>
      <section class="module-panel" data-module="inventory"><h2>Estoque do técnico</h2><table><thead><tr><th>Item</th><th>Saldo</th><th>Série</th><th>Reposição</th></tr></thead><tbody>{inventory_rows}</tbody></table></section>
      <section class="module-panel" data-module="materials"><h2>Histórico de materiais</h2><table><thead><tr><th>Item</th><th>Movimento</th><th>Quantidade</th><th>OS</th><th>Origem</th><th>Data UTC</th></tr></thead><tbody>{movement_rows}</tbody></table></section>
      <section class="module-panel" data-module="mkauth">
        <h2>Integração MK-AUTH</h2>
        <p><b>Modo:</b> {escape(mkauth_settings.mkauth_mode)}</p>
        <p><b>Destino:</b> {escape(mkauth_settings.mkauth_base_url)}</p>
        <p>O diagnóstico é estritamente de leitura e não altera clientes, planos ou cobranças.</p>
        <a class="button-link" href="/api/v1/integrations/mkauth/probe" target="_blank">EXECUTAR DIAGNÓSTICO</a>
        <button type="button" id="load-mkauth-plans">ATUALIZAR PLANOS</button>
        <p id="mkauth-plans-status">Abra este módulo para consultar os planos reais.</p>
        <table>
          <thead><tr><th>Plano</th><th>Valor</th><th>Download</th><th>Upload</th><th>Identificador</th></tr></thead>
          <tbody id="mkauth-plans-body"><tr><td colspan="5">Consulta ainda não realizada.</td></tr></tbody>
        </table>
      </section>
      <section class="module-panel" data-module="mkauth-clients">
        <h2>Clientes MK-AUTH</h2>
        <p>Consulta real e somente leitura. Senha PPPoE, CPF/CNPJ, telefone e e-mail não são enviados para esta tela.</p>
        <button type="button" id="load-mkauth-clients">ATUALIZAR CLIENTES</button>
        <label>Buscar cliente <input id="mkauth-clients-filter" type="search" placeholder="Nome, login, cidade ou identificador"></label>
        <p id="mkauth-clients-status">Abra este módulo para consultar os clientes.</p>
        <table>
          <thead><tr><th>Cliente</th><th>Login PPPoE</th><th>Situação</th><th>Tipo</th><th>Cidade/UF</th><th>Coordenadas</th><th>Identificador</th><th>Ação</th></tr></thead>
          <tbody id="mkauth-clients-body"><tr><td colspan="8">Consulta ainda não realizada.</td></tr></tbody>
        </table>
        <section id="mkauth-client-details" hidden>
          <h3>Detalhes técnicos do cliente</h3>
          <p id="mkauth-client-details-status"></p>
          <table>
            <tbody id="mkauth-client-details-body"></tbody>
          </table>
        </section>
      </section>
      <section class="module-panel" data-module="mkauth-inactive-clients">
        <h2>Clientes desativados</h2>
        <p>Clientes desativados no MK-AUTH ficam separados da lista operacional e não podem ser selecionados para abrir OS.</p>
        <button type="button" id="load-mkauth-inactive-clients">ATUALIZAR CLIENTES</button>
        <p id="mkauth-inactive-clients-status">Abra este módulo para consultar os clientes desativados.</p>
        <table>
          <thead><tr><th>Cliente</th><th>Login PPPoE</th><th>Tipo</th><th>Cidade/UF</th><th>Coordenadas</th><th>Identificador</th><th>Ação</th></tr></thead>
          <tbody id="mkauth-inactive-clients-body"><tr><td colspan="7">Consulta ainda não realizada.</td></tr></tbody>
        </table>
        <section id="mkauth-inactive-client-details" hidden>
          <h3>Detalhes técnicos do cliente desativado</h3>
          <p id="mkauth-inactive-client-details-status"></p>
          <table>
            <tbody id="mkauth-inactive-client-details-body"></tbody>
          </table>
        </section>
      </section>
      <section class="module-panel" data-module="mkauth-additional-clients">
        <h2>Clientes adicionais</h2>
        <p>Consulta real e somente leitura dos acessos adicionais vinculados a clientes do MK-AUTH.</p>
        <button type="button" id="load-mkauth-additional-clients">ATUALIZAR ADICIONAIS</button>
        <p id="mkauth-additional-clients-status">Abra este módulo para consultar os clientes adicionais.</p>
        <table>
          <thead><tr><th>Adicional</th><th>Login PPPoE</th><th>Cliente principal</th><th>Plano</th><th>Situação</th><th>Identificador</th><th>Ação</th></tr></thead>
          <tbody id="mkauth-additional-clients-body"><tr><td colspan="7">Consulta ainda não realizada.</td></tr></tbody>
        </table>
      </section>
      <section class="module-panel" data-module="mkauth-titles">
        <h2>Títulos MK-AUTH</h2>
        <p>Consulta financeira real e somente leitura. CPF/CNPJ, linha digitável, QR Code e dados bancários não são enviados para esta tela.</p>
        <button type="button" id="load-mkauth-titles">ATUALIZAR TÍTULOS</button>
        <label>Login do cliente<input id="mkauth-titles-login-filter" placeholder="Ex.: cliente.pppoe"></label>
        <input id="mkauth-titles-filter" type="hidden" value="">
        <button type="button" id="filter-mkauth-titles">FILTRAR</button>
        <p id="mkauth-titles-status">Abra este módulo para consultar os títulos.</p>
        <table>
          <thead><tr><th>Título</th><th>Login</th><th>Tipo</th><th>Valor</th><th>Situação</th><th>Vencimento</th><th>Ação</th></tr></thead>
          <tbody id="mkauth-titles-body"><tr><td colspan="7">Consulta ainda não realizada.</td></tr></tbody>
        </table>
      </section>
      <section class="module-panel" data-module="mkauth-tickets">
        <h2>Chamados MK-AUTH</h2>
        <p>Consulta real e somente leitura. Nenhum chamado será editado ou fechado nesta etapa.</p>
        <button type="button" id="load-mkauth-tickets">ATUALIZAR CHAMADOS</button>
        <p id="mkauth-tickets-status">Abra este módulo para consultar os chamados.</p>
        <table>
          <thead><tr><th>Número</th><th>Abertura</th><th>Login</th><th>Assunto</th><th>Prioridade</th><th>Status</th><th>Identificador</th><th>Ação</th></tr></thead>
          <tbody id="mkauth-tickets-body"><tr><td colspan="8">Consulta ainda não realizada.</td></tr></tbody>
        </table>
      </section>
      <section class="module-panel" data-module="technicians">
        <h2>Técnicos</h2>
        {technician_form}
        <table><thead><tr><th>Nome</th><th>Usuário</th><th>Situação</th><th>Ação</th></tr></thead><tbody>{technician_rows}</tbody></table>
      </section>
      <section class="module-panel" data-module="central-users">
        <h2>Usuários da central</h2>
        <p>Organização: <b>{escape(session['organization']['name'])}</b> • Seu perfil: <b>{escape(role_labels[current_user['role']])}</b></p>
        {central_user_form}
        <table><thead><tr><th>Nome</th><th>Usuário</th><th>Perfil</th><th>Situação</th><th>Ação</th></tr></thead><tbody>{central_user_rows}</tbody></table>
      </section>
      <section class="module-panel" data-module="portal-customers">
        <h2>Clientes do portal</h2>
        <p>Contas que já possuem acesso ao portal deste provedor. Senhas nunca são exibidas.</p>
        <table><thead><tr><th>Nome</th><th>Usuário</th><th>Login MK-AUTH</th><th>Identificador MK-AUTH</th><th>Situação</th><th>Ação</th></tr></thead><tbody>{portal_customer_rows}</tbody></table>
      </section>
      {branding_panel}
      {subscription_panel}
      {audit_panel}
      <section class="module-panel" data-module="network"><h2>Monitoramento da rede</h2>
        <p class="alert"><b>{len(network_alerts)} ocorrência(s) ativa(s)</b></p>
        <form method="post" action="/api/v1/network/incidents/simulate"><button type="submit">SIMULAR INDISPONIBILIDADE</button></form>
        <form method="post" action="/api/v1/network/incidents/resolve"><button class="secondary" type="submit">ENCERRAR OCORRÊNCIAS</button></form>
        <table><thead><tr><th>Ocorrência</th><th>Área</th><th>Detectada em UTC</th></tr></thead><tbody>{network_rows}</tbody></table>
      </section>
      <section class="module-panel" data-module="routeros-diagnostic">
        <h2>Diagnóstico PPPoE/RADIUS</h2>
        <p>Consulta real e somente leitura no MikroTik. Senhas e segredos RADIUS nunca são exibidos.</p>
        <button type="button" id="load-routeros-diagnostic">EXECUTAR DIAGNÓSTICO</button>
        <label>Localizar login PPPoE<input id="routeros-username-filter" placeholder="Ex.: cliente.pppoe"></label>
        <button type="button" id="filter-routeros-session">LOCALIZAR SESSÃO</button>
        <p id="routeros-diagnostic-status">Execute o diagnóstico para consultar o roteador.</p>
        <div id="routeros-summary"></div>
        <h3>Verificações automáticas</h3>
        <table><thead><tr><th>Verificação</th><th>Resultado</th><th>Detalhe</th></tr></thead><tbody id="routeros-checks-body"><tr><td colspan="3">Consulta ainda não realizada.</td></tr></tbody></table>
        <h3>Configuração PPP AAA</h3>
        <table><tbody id="routeros-aaa-body"><tr><td>Consulta ainda não realizada.</td></tr></tbody></table>
        <h3>Servidores RADIUS</h3>
        <table><thead><tr><th>Endereço</th><th>Serviços</th><th>Autenticação</th><th>Contabilidade</th><th>Timeout</th><th>Estado</th></tr></thead><tbody id="routeros-radius-body"><tr><td colspan="6">Consulta ainda não realizada.</td></tr></tbody></table>
        <h3>Sessões PPPoE ativas</h3>
        <table><thead><tr><th>Usuário</th><th>Serviço</th><th>IP</th><th>Tempo online</th><th>Identificador</th></tr></thead><tbody id="routeros-sessions-body"><tr><td colspan="5">Consulta ainda não realizada.</td></tr></tbody></table>
      </section>
      <section class="module-panel" data-module="provisioning"><h2>Últimos provisionamentos</h2><table><thead><tr><th>Serial</th><th>Perfil</th><th>Data UTC</th></tr></thead><tbody>{provisioning_rows}</tbody></table></section>
      <section class="module-panel" data-module="financial">
        <h2>Financeiro e desbloqueio</h2>
        <table><thead><tr><th>Cliente fictício</th><th>Fatura</th><th>Situação</th><th>Acesso</th><th>Simulações</th></tr></thead><tbody>{financial_rows}</tbody></table>
        <h3>Histórico de desbloqueios de confiança MK-AUTH</h3>
        <button type="button" id="load-trust-unlocks">ATUALIZAR HISTÓRICO</button>
        <table><thead><tr><th>Login</th><th>Motivo</th><th>Desbloqueado em UTC</th><th>Validade UTC</th><th>Status</th><th>Ação</th></tr></thead><tbody id="trust-unlocks-body"><tr><td colspan="6">Consulta ainda não realizada.</td></tr></tbody></table>
        <h3>Pagamentos Pix simulados</h3>
        <p>Nenhuma baixa real é enviada ao MK-AUTH nesta etapa.</p>
        <button type="button" id="load-pix-simulations">ATUALIZAR SIMULAÇÕES</button>
        <table><thead><tr><th>Título</th><th>Login</th><th>Valor</th><th>Data UTC</th><th>Status</th></tr></thead><tbody id="pix-simulations-body"><tr><td colspan="5">Consulta ainda não realizada.</td></tr></tbody></table>
      </section>
      <section class="module-panel" data-module="support">
        <h2>Chamados do portal do cliente</h2>
        <table><thead><tr><th>Número</th><th>Assunto</th><th>Descrição</th><th>Situação</th><th>OS</th><th>Avaliação</th><th>Ação</th></tr></thead><tbody>{support_rows}</tbody></table>
      </section>
      <section class="module-panel" data-module="whatsapp">
        <h2>WhatsApp simulado</h2>
        <p>Nenhuma mensagem real será enviada. Destinatário fictício: +55 (00) 00000-0000.</p>
        <form method="post" action="/api/v1/notifications/simulate/invoice_reminder?redirect=true"><button type="submit">Simular lembrete de fatura</button></form>
        <form method="post" action="/api/v1/notifications/simulate/maintenance?redirect=true"><button class="secondary" type="submit">Simular aviso de manutenção</button></form>
        <table><thead><tr><th>Modelo</th><th>Login</th><th>Destinatário fictício</th><th>Mensagem</th><th>Status</th><th>Data UTC</th></tr></thead><tbody>{message_rows}</tbody></table>
      </section>
      </div>
    </div>
    <footer>
      <span id="refresh-status">Atualização automática desativada.</span>
      <button type="button" onclick="location.reload()">ATUALIZAR AGORA</button>
    </footer>
  </main>
  <script>
    (() => {{
      const status = document.getElementById('refresh-status');
      const menuButtons = [...document.querySelectorAll('.menu-button')];
      const modulePanels = [...document.querySelectorAll('.module-panel')];
      const moduleNames = new Set(modulePanels.map((panel) => panel.dataset.module));
      let mkauthPlansLoaded = false;
      let mkauthClientsLoaded = false;
      let mkauthTicketsLoaded = false;
      let mkauthAdditionalClientsLoaded = false;
      let mkauthTitlesLoaded = false;
      let mkauthTitlesCache = [];
      let routerosDiagnosticLoaded = false;
      let mkauthClientsCache = [];
      const portalAccesses = {portal_accesses_json};
      let renderActiveMkauthClients = () => {{}};
      const loadRouterosDiagnostic = async (force = false, requestedUsername = '') => {{
        if (routerosDiagnosticLoaded && !force) return;
        const diagnosticStatus = document.getElementById('routeros-diagnostic-status');
        const summary = document.getElementById('routeros-summary');
        const checksBody = document.getElementById('routeros-checks-body');
        const aaaBody = document.getElementById('routeros-aaa-body');
        const radiusBody = document.getElementById('routeros-radius-body');
        const sessionsBody = document.getElementById('routeros-sessions-body');
        diagnosticStatus.textContent = 'Consultando o MikroTik...';
        try {{
          const response = await fetch('/api/v1/integrations/routeros/diagnostic', {{ headers: {{ Accept: 'application/json' }} }});
          if (!response.ok) throw new Error('request_failed');
          const data = await response.json();
          if (data.status !== 'connected') throw new Error(data.reason || 'integration_unavailable');
          summary.replaceChildren();
          const summaryText = document.createElement('p');
          summaryText.textContent = `Roteador: ${{data.router.board}} • RouterOS ${{data.router.version}} • Uptime ${{data.router.uptime}} • CPU ${{data.router.cpu_load}}%`;
          summary.appendChild(summaryText);
          aaaBody.replaceChildren();
          [['Usar RADIUS', data.ppp_aaa.use_radius ? 'Sim' : 'Não'], ['Accounting', data.ppp_aaa.accounting ? 'Sim' : 'Não'], ['Atualização intermediária', data.ppp_aaa.interim_update]].forEach(([label, value]) => {{
            const row = document.createElement('tr');
            const labelCell = document.createElement('th');
            const valueCell = document.createElement('td');
            labelCell.textContent = label;
            valueCell.textContent = value;
            row.append(labelCell, valueCell);
            aaaBody.appendChild(row);
          }});
          const renderRows = (body, items, fields, emptyMessage, colspan) => {{
            body.replaceChildren();
            items.forEach((item) => {{
              const row = document.createElement('tr');
              fields(item).forEach((value) => {{
                const cell = document.createElement('td');
                cell.textContent = value;
                row.appendChild(cell);
              }});
              body.appendChild(row);
            }});
            if (!items.length) {{
              const row = document.createElement('tr');
              const cell = document.createElement('td');
              cell.colSpan = colspan;
              cell.textContent = emptyMessage;
              row.appendChild(cell);
              body.appendChild(row);
            }}
          }};
          renderRows(
            checksBody,
            data.checks,
            (item) => [item.name, item.status === 'ok' ? 'OK' : 'ATENÇÃO', item.detail],
            'Nenhuma verificação disponível.',
            3,
          );
          renderRows(radiusBody, data.radius, (item) => [item.address, item.services, item.authentication_port, item.accounting_port, item.timeout, item.disabled ? 'Desativado' : 'Ativo'], 'Nenhum servidor RADIUS configurado.', 6);
          const usernameFilter = (requestedUsername || document.getElementById('routeros-username-filter').value).trim().toLowerCase();
          if (requestedUsername) document.getElementById('routeros-username-filter').value = requestedUsername;
          const visibleSessions = usernameFilter
            ? data.sessions.filter((item) => item.username.toLowerCase() === usernameFilter)
            : data.sessions;
          renderRows(
            sessionsBody,
            visibleSessions,
            (item) => [item.username, item.service, item.address, item.uptime, item.caller_id],
            usernameFilter ? `O login ${{usernameFilter}} está offline.` : 'Nenhuma sessão PPPoE ativa.',
            5,
          );
          diagnosticStatus.textContent = usernameFilter
            ? (visibleSessions.length ? `Login ${{usernameFilter}} online • somente leitura` : `Login ${{usernameFilter}} offline • somente leitura`)
            : `Diagnóstico concluído • ${{data.sessions.length}} sessão(ões) ativa(s) • somente leitura`;
          routerosDiagnosticLoaded = true;
        }} catch (_) {{
          diagnosticStatus.textContent = 'Não foi possível consultar o MikroTik. Confira as credenciais e a configuração da API.';
        }}
      }};
      document.getElementById('load-routeros-diagnostic').addEventListener('click', () => loadRouterosDiagnostic(true));
      document.getElementById('filter-routeros-session').addEventListener('click', () => loadRouterosDiagnostic(true));
      const loadMkauthPlans = async (force = false) => {{
        if (mkauthPlansLoaded && !force) return;
        const plansStatus = document.getElementById('mkauth-plans-status');
        const plansBody = document.getElementById('mkauth-plans-body');
        plansStatus.textContent = 'Consultando planos no MK-AUTH...';
        try {{
          const response = await fetch('/api/v1/integrations/mkauth/plans', {{ headers: {{ Accept: 'application/json' }} }});
          if (!response.ok) throw new Error('request_failed');
          const data = await response.json();
          if (data.status !== 'connected') throw new Error(data.reason || 'integration_unavailable');
          plansBody.replaceChildren();
          data.plans.forEach((plan) => {{
            const row = document.createElement('tr');
            [plan.name, `R$ ${{plan.price}}`, plan.download, plan.upload, plan.uuid || '-'].forEach((value) => {{
              const cell = document.createElement('td');
              cell.textContent = value;
              row.appendChild(cell);
            }});
            plansBody.appendChild(row);
          }});
          if (!data.plans.length) {{
            const row = document.createElement('tr');
            const cell = document.createElement('td');
            cell.colSpan = 5;
            cell.textContent = 'Nenhum plano retornado pelo MK-AUTH.';
            row.appendChild(cell);
            plansBody.appendChild(row);
          }}
          plansStatus.textContent = `${{data.count}} plano(s) carregado(s) • somente leitura`;
          mkauthPlansLoaded = true;
        }} catch (_) {{
          plansStatus.textContent = 'Não foi possível consultar os planos. Execute o diagnóstico e tente novamente.';
        }}
      }};
      document.getElementById('load-mkauth-plans').addEventListener('click', () => loadMkauthPlans(true));
      const loadMkauthClients = async (force = false) => {{
        if (mkauthClientsLoaded && !force) return;
        const clientsStatus = document.getElementById('mkauth-clients-status');
        const clientsBody = document.getElementById('mkauth-clients-body');
        const inactiveStatus = document.getElementById('mkauth-inactive-clients-status');
        const inactiveBody = document.getElementById('mkauth-inactive-clients-body');
        clientsStatus.textContent = 'Consultando clientes no MK-AUTH...';
        inactiveStatus.textContent = 'Consultando clientes desativados no MK-AUTH...';
        try {{
          const response = await fetch('/api/v1/integrations/mkauth/clients', {{ headers: {{ Accept: 'application/json' }} }});
          if (!response.ok) throw new Error('request_failed');
          const data = await response.json();
          if (data.status !== 'connected') throw new Error('integration_unavailable');
          mkauthClientsCache = data.clients.filter((client) => client.active);
          const inactiveClients = data.clients.filter((client) => !client.active);
          const renderClients = (items, body, detailsTarget, emptyMessage, allowPppoeDiagnostic = false) => {{
            body.replaceChildren();
            items.forEach((client) => {{
              const row = document.createElement('tr');
              if (allowPppoeDiagnostic) row.className = client.blocked ? 'client-blocked' : 'client-active';
              const location = client.city === '-' ? client.state : `${{client.city}}/${{client.state}}`;
              [client.name, client.login].forEach((value) => {{
                const cell = document.createElement('td');
                cell.textContent = value;
                row.appendChild(cell);
              }});
              if (allowPppoeDiagnostic) {{
                const stateCell = document.createElement('td');
                const stateBadge = document.createElement('span');
                stateBadge.className = `client-state ${{client.blocked ? 'blocked' : 'active'}}`;
                stateBadge.textContent = client.blocked ? 'Bloqueado' : 'Ativo';
                stateCell.appendChild(stateBadge);
                row.appendChild(stateCell);
              }}
              [client.connection_type, location, client.coordinates, client.uuid || '-'].forEach((value) => {{
                const cell = document.createElement('td');
                cell.textContent = value;
                row.appendChild(cell);
              }});
              const actionCell = document.createElement('td');
              const detailsButton = document.createElement('button');
              detailsButton.type = 'button';
              detailsButton.textContent = 'VER DETALHES';
              detailsButton.addEventListener('click', () => loadMkauthClientDetails(client.login, detailsTarget, client.uuid));
              actionCell.appendChild(detailsButton);
              if (allowPppoeDiagnostic) {{
                const portalButton = document.createElement('button');
                portalButton.type = 'button';
                portalButton.className = 'portal-manage-button';
                const portalAccess = portalAccesses.find((access) =>
                  (client.uuid && access.external_customer_id === client.uuid) ||
                  (access.external_login || '').toLocaleLowerCase('pt-BR') ===
                    (client.login || '').toLocaleLowerCase('pt-BR'));
                portalButton.textContent = portalAccess
                  ? (portalAccess.active ? 'REENVIAR CONVITE DO PORTAL' : 'ACESSO AO PORTAL DESATIVADO')
                  : 'CRIAR ACESSO E ENVIAR CONVITE';
                portalButton.disabled = Boolean(portalAccess && !portalAccess.active);
                portalButton.addEventListener('click', () => {{
                  if (!client.uuid) {{
                    window.alert('Este cliente não possui identificador no MK-AUTH.');
                    return;
                  }}
                  const confirmation = portalAccess
                    ? `Gerar um novo convite do portal para ${{client.name}}? O convite anterior deixará de funcionar.`
                    : `Criar acesso ao portal e convite para ${{client.name}}?`;
                  if (!window.confirm(confirmation)) return;
                  const form = document.createElement('form');
                  form.method = 'post';
                  form.action = '/central/portal-customers/invite-from-mkauth';
                  const values = {{
                    name: client.name,
                    username: client.login,
                    external_login: client.login,
                    external_customer_id: client.uuid,
                  }};
                  Object.entries(values).forEach(([name, value]) => {{
                    const input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = name;
                    input.value = value;
                    form.appendChild(input);
                  }});
                  document.body.appendChild(form);
                  form.submit();
                }});
                actionCell.appendChild(portalButton);
                const diagnosticButton = document.createElement('button');
                diagnosticButton.type = 'button';
                diagnosticButton.textContent = 'VER PPPoE';
                diagnosticButton.addEventListener('click', () => {{
                  document.getElementById('routeros-username-filter').value = client.login;
                  activateModule('routeros-diagnostic');
                  loadRouterosDiagnostic(true, client.login);
                }});
                actionCell.appendChild(diagnosticButton);
                const financialButton = document.createElement('button');
                financialButton.type = 'button';
                financialButton.textContent = 'VER FINANCEIRO';
                financialButton.addEventListener('click', () => {{
                  document.getElementById('mkauth-titles-login-filter').value = client.login;
                  activateModule('mkauth-titles');
                  loadMkauthTitles(true, client.login);
                }});
                actionCell.appendChild(financialButton);
              }}
              row.appendChild(actionCell);
              body.appendChild(row);
            }});
            if (!items.length) {{
              const row = document.createElement('tr');
              const cell = document.createElement('td');
              cell.colSpan = allowPppoeDiagnostic ? 8 : 7;
              cell.textContent = emptyMessage;
              row.appendChild(cell);
              body.appendChild(row);
            }}
          }};
          renderActiveMkauthClients = () => {{
            const query = document.getElementById('mkauth-clients-filter').value.trim().toLocaleLowerCase('pt-BR');
            const visibleClients = query
              ? mkauthClientsCache.filter((client) =>
                  [client.name, client.login, client.city, client.state, client.uuid]
                    .some((value) => String(value || '').toLocaleLowerCase('pt-BR').includes(query)))
              : mkauthClientsCache;
            renderClients(visibleClients, clientsBody, 'mkauth-client', 'Nenhum cliente encontrado para esta busca.', true);
            clientsStatus.textContent = query
              ? `${{visibleClients.length}} de ${{mkauthClientsCache.length}} cliente(s) encontrado(s)`
              : `${{mkauthClientsCache.length}} cliente(s) ativo(s) • somente leitura`;
          }};
          renderActiveMkauthClients();
          renderClients(inactiveClients, inactiveBody, 'mkauth-inactive-client', 'Nenhum cliente desativado retornado pelo MK-AUTH.');
          inactiveStatus.textContent = `${{inactiveClients.length}} cliente(s) desativado(s) • somente leitura`;
          const clientSelect = document.getElementById('mkauth-client-select');
          clientSelect.replaceChildren(new Option('Cliente manual/fictício', ''));
          data.clients.forEach((client, index) => {{
            clientSelect.add(new Option(`${{client.name}} • ${{client.login}}`, String(index)));
          }});
          mkauthClientsLoaded = true;
        }} catch (_) {{
          clientsStatus.textContent = 'Não foi possível consultar os clientes. Confirme cliente.api → GET no MK-AUTH.';
          inactiveStatus.textContent = 'Não foi possível consultar os clientes desativados.';
        }}
      }};
      document.getElementById('load-mkauth-clients').addEventListener('click', () => loadMkauthClients(true));
      document.getElementById('load-mkauth-inactive-clients').addEventListener('click', () => loadMkauthClients(true));
      document.getElementById('mkauth-clients-filter').addEventListener('input', () => renderActiveMkauthClients());
      const loadMkauthAdditionalClients = async (force = false) => {{
        if (mkauthAdditionalClientsLoaded && !force) return;
        const additionalStatus = document.getElementById('mkauth-additional-clients-status');
        const additionalBody = document.getElementById('mkauth-additional-clients-body');
        additionalStatus.textContent = 'Consultando clientes adicionais no MK-AUTH...';
        try {{
          const response = await fetch('/api/v1/integrations/mkauth/additional-clients', {{ headers: {{ Accept: 'application/json' }} }});
          if (!response.ok) throw new Error('request_failed');
          const data = await response.json();
          if (data.status !== 'connected') throw new Error(data.reason || 'integration_unavailable');
          additionalBody.replaceChildren();
          data.additional_clients.forEach((client) => {{
            const row = document.createElement('tr');
            [client.name, client.login, client.main_login, client.plan, client.active ? 'Ativo' : 'Desativado', client.uuid || '-'].forEach((value) => {{
              const cell = document.createElement('td');
              cell.textContent = value;
              row.appendChild(cell);
            }});
            const actionCell = document.createElement('td');
            const pppoeButton = document.createElement('button');
            pppoeButton.type = 'button';
            pppoeButton.textContent = 'VER PPPoE';
            pppoeButton.addEventListener('click', () => {{
              document.getElementById('routeros-username-filter').value = client.login;
              activateModule('routeros-diagnostic');
              loadRouterosDiagnostic(true, client.login);
            }});
            actionCell.appendChild(pppoeButton);
            row.appendChild(actionCell);
            additionalBody.appendChild(row);
          }});
          if (!data.additional_clients.length) {{
            const row = document.createElement('tr');
            const cell = document.createElement('td');
            cell.colSpan = 7;
            cell.textContent = 'Nenhum cliente adicional retornado pelo MK-AUTH.';
            row.appendChild(cell);
            additionalBody.appendChild(row);
          }}
          additionalStatus.textContent = `${{data.count}} cliente(s) adicional(is) • somente leitura`;
          mkauthAdditionalClientsLoaded = true;
        }} catch (error) {{
          const reason = error instanceof Error ? error.message : 'integration_unavailable';
          additionalStatus.textContent = `Não foi possível consultar os clientes adicionais: ${{reason}}`;
        }}
      }};
      document.getElementById('load-mkauth-additional-clients').addEventListener('click', () => loadMkauthAdditionalClients(true));
      const renderMkauthTitles = () => {{
        const titlesBody = document.getElementById('mkauth-titles-body');
        const selectedStatus = document.getElementById('mkauth-titles-filter').value;
        const selectedLogin = document.getElementById('mkauth-titles-login-filter').value.trim().toLowerCase();
        const visibleTitles = mkauthTitlesCache.filter((title) => {{
          const matchesStatus = !selectedStatus || title.status === selectedStatus || (selectedStatus === 'pago' && title.status === 'liquidado');
          const matchesLogin = !selectedLogin || title.login.toLowerCase() === selectedLogin;
          return matchesStatus && matchesLogin;
        }});
        titlesBody.replaceChildren();
          visibleTitles.forEach((title) => {{
          const row = document.createElement('tr');
          [title.number, title.login, title.type, `R$ ${{title.amount}}`, title.status, title.due_date].forEach((value) => {{
            const cell = document.createElement('td');
            cell.textContent = value;
            row.appendChild(cell);
          }});
          const actionCell = document.createElement('td');
          const paidStatuses = ['pago', 'liquidado', 'recebido', 'baixado'];
          if (title.uuid && !paidStatuses.includes(title.status)) {{
            const pixButton = document.createElement('button');
            pixButton.type = 'button';
            pixButton.textContent = 'SIMULAR PIX';
            pixButton.addEventListener('click', async () => {{
              if (!window.confirm(`Simular o recebimento Pix do título ${{title.number}} de ${{title.login}}? Nenhuma baixa real será realizada.`)) return;
              pixButton.disabled = true;
              try {{
                const pixResponse = await fetch('/api/v1/integrations/mkauth/pix-simulations', {{
                  method: 'POST',
                  headers: {{ 'Content-Type': 'application/json', Accept: 'application/json' }},
                  body: JSON.stringify({{ title_uuid: title.uuid, login: title.login, confirmed: true }}),
                }});
                if (!pixResponse.ok) throw new Error('request_failed');
                const result = await pixResponse.json();
                if (result.status !== 'simulated') throw new Error(result.reason || result.status);
                window.alert('Pagamento Pix simulado e registrado. Nenhuma baixa real foi enviada ao MK-AUTH.');
                await loadPixSimulations(true);
              }} catch (error) {{
                const reasonText = error instanceof Error ? error.message : 'simulation_failed';
                window.alert(`Não foi possível simular o Pix: ${{reasonText}}`);
              }} finally {{
                pixButton.disabled = false;
              }}
            }});
            actionCell.appendChild(pixButton);
            const realPaymentButton = document.createElement('button');
            realPaymentButton.type = 'button';
            realPaymentButton.textContent = 'BAIXA REAL PIX';
            realPaymentButton.addEventListener('click', async () => {{
              const confirmationText = window.prompt(
                `ATENÇÃO: esta ação dará baixa REAL no título ${{title.number}}, no valor de R$ ${{title.amount}}. Digite BAIXAR para continuar:`,
              );
              if (String(confirmationText || '').trim().toUpperCase() !== 'BAIXAR') return;
              if (!window.confirm(`Última confirmação: dar baixa REAL via Pix no título ${{title.number}} de ${{title.login}}?`)) return;
              realPaymentButton.disabled = true;
              pixButton.disabled = true;
              try {{
                const paymentResponse = await fetch('/api/v1/integrations/mkauth/pix-payments', {{
                  method: 'POST',
                  headers: {{ 'Content-Type': 'application/json', Accept: 'application/json' }},
                  body: JSON.stringify({{
                    title_uuid: title.uuid,
                    login: title.login,
                    confirmation_text: confirmationText,
                    confirmed: true,
                  }}),
                }});
                if (!paymentResponse.ok) throw new Error('request_failed');
                const result = await paymentResponse.json();
                if (result.status !== 'paid') throw new Error(result.reason || result.status);
                const accessMessage = result.access_resolution === 'no_pending_titles'
                  ? ' Não restam títulos pendentes; a observação temporária foi encerrada.'
                  : ` Ainda restam ${{result.remaining_titles}} título(s) pendente(s); o acesso não foi alterado.`;
                window.alert(`Baixa real confirmada pelo MK-AUTH.${{accessMessage}} Notificação registrada no WhatsApp simulado.`);
                await loadMkauthTitles(true);
                await loadPixSimulations(true);
              }} catch (error) {{
                const reasonText = error instanceof Error ? error.message : 'payment_failed';
                window.alert(`Não foi possível realizar a baixa: ${{reasonText}}`);
                realPaymentButton.disabled = false;
                pixButton.disabled = false;
              }}
            }});
            actionCell.appendChild(realPaymentButton);
          }} else {{
            actionCell.textContent = '-';
          }}
          row.appendChild(actionCell);
          titlesBody.appendChild(row);
        }});
        if (!visibleTitles.length) {{
          const row = document.createElement('tr');
          const cell = document.createElement('td');
          cell.colSpan = 7;
          cell.textContent = 'Nenhum título encontrado para este filtro.';
          row.appendChild(cell);
          titlesBody.appendChild(row);
        }}
      }};
      const loadMkauthTitles = async (force = false, requestedLogin = '') => {{
        if (mkauthTitlesLoaded && !force) return;
        const titlesStatus = document.getElementById('mkauth-titles-status');
        if (requestedLogin) document.getElementById('mkauth-titles-login-filter').value = requestedLogin;
        titlesStatus.textContent = 'Consultando títulos no MK-AUTH...';
        try {{
          const loginFilter = document.getElementById('mkauth-titles-login-filter').value.trim();
          const query = loginFilter ? `?login=${{encodeURIComponent(loginFilter)}}` : '';
          const response = await fetch(`/api/v1/integrations/mkauth/titles${{query}}`, {{ headers: {{ Accept: 'application/json' }} }});
          if (!response.ok) throw new Error('request_failed');
          const data = await response.json();
          if (data.status !== 'connected') throw new Error(data.reason || 'integration_unavailable');
          mkauthTitlesCache = data.titles;
          renderMkauthTitles();
          const overdue = data.titles.filter((title) => title.status === 'vencido').length;
          const upcoming = data.titles.filter((title) => title.status === 'aberto').length;
          titlesStatus.textContent = `${{data.count}} título(s) pendente(s) • ${{overdue}} vencido(s) • ${{upcoming}} a vencer • somente leitura`;
          mkauthTitlesLoaded = true;
        }} catch (error) {{
          const reason = error instanceof Error ? error.message : 'integration_unavailable';
          titlesStatus.textContent = `Não foi possível consultar os títulos: ${{reason}}`;
        }}
      }};
      document.getElementById('load-mkauth-titles').addEventListener('click', () => loadMkauthTitles(true));
      document.getElementById('filter-mkauth-titles').addEventListener('click', () => loadMkauthTitles(true));
      let pixSimulationsLoaded = false;
      const loadPixSimulations = async (force = false) => {{
        if (pixSimulationsLoaded && !force) return;
        const body = document.getElementById('pix-simulations-body');
        try {{
          const response = await fetch('/api/v1/integrations/mkauth/pix-simulations', {{ headers: {{ Accept: 'application/json' }} }});
          if (!response.ok) throw new Error('request_failed');
          const data = await response.json();
          body.replaceChildren();
          data.records.forEach((record) => {{
            const row = document.createElement('tr');
            const paymentStatus = record.status === 'real_paid' ? 'Baixa real confirmada' : 'Simulado';
            [record.title_number, record.login, `R$ ${{record.amount}}`, record.simulated_at, paymentStatus].forEach((value) => {{
              const cell = document.createElement('td');
              cell.textContent = value;
              row.appendChild(cell);
            }});
            body.appendChild(row);
          }});
          if (!data.records.length) {{
            const row = document.createElement('tr');
            const cell = document.createElement('td');
            cell.colSpan = 5;
            cell.textContent = 'Nenhum pagamento Pix simulado.';
            row.appendChild(cell);
            body.appendChild(row);
          }}
          pixSimulationsLoaded = true;
        }} catch (_) {{
          body.innerHTML = '<tr><td colspan="5">Não foi possível carregar as simulações.</td></tr>';
        }}
      }};
      document.getElementById('load-pix-simulations').addEventListener('click', () => loadPixSimulations(true));
      const loadMkauthClientDetails = async (login, target = 'mkauth-client', clientUuid = '') => {{
        const detailsPanel = document.getElementById(`${{target}}-details`);
        const detailsStatus = document.getElementById(`${{target}}-details-status`);
        const detailsBody = document.getElementById(`${{target}}-details-body`);
        detailsPanel.hidden = false;
        detailsStatus.textContent = `Consultando dados técnicos de ${{login}}...`;
        detailsBody.replaceChildren();
        try {{
          const response = await fetch(
            `/api/v1/integrations/mkauth/client-details?login=${{encodeURIComponent(login)}}`,
            {{ headers: {{ Accept: 'application/json' }} }},
          );
          if (!response.ok) throw new Error('request_failed');
          const data = await response.json();
          if (data.status !== 'connected' || !data.client) throw new Error('integration_unavailable');
          const fields = [
            ['Cliente', data.client.name],
            ['Login PPPoE', data.client.login],
            ['Tipo de conexão', data.client.connection_type],
            ['Plano', data.client.plan],
            ['Ativado', data.client.activated],
            ['Bloqueado', data.client.blocked],
            ['Situação de corte', data.client.cut_status],
            ['IP', data.client.ip],
            ['MAC', data.client.mac],
            ['ONU/ONT', data.client.onu_ont],
            ['Porta OLT', data.client.olt_port],
            ['Coordenadas', data.client.coordinates],
          ];
          fields.forEach(([label, value]) => {{
            const row = document.createElement('tr');
            const labelCell = document.createElement('th');
            const valueCell = document.createElement('td');
            labelCell.textContent = label;
            valueCell.textContent = value || '-';
            row.append(labelCell, valueCell);
            detailsBody.appendChild(row);
          }});
          const blockedValue = String(data.client.blocked || '').trim().toLowerCase();
          const cutStatusValue = String(data.client.cut_status || '').trim().toLowerCase();
          const blockedIndicators = ['s', 'sim', '1', 'true', 'bloq', 'bloqueado'];
          const isBlocked = blockedIndicators.includes(blockedValue) || blockedIndicators.includes(cutStatusValue);
          if (target === 'mkauth-client' && clientUuid && isBlocked) {{
            const actionRow = document.createElement('tr');
            const actionLabel = document.createElement('th');
            const actionCell = document.createElement('td');
            const unlockButton = document.createElement('button');
            actionLabel.textContent = 'Desbloqueio de confiança';
            unlockButton.type = 'button';
            unlockButton.textContent = 'LIBERAR POR 48 HORAS';
            unlockButton.addEventListener('click', async () => {{
              const reason = window.prompt('Informe o motivo do desbloqueio (mínimo 5 caracteres):', 'Cliente solicitou desbloqueio de confiança');
              if (!reason || reason.trim().length < 5) return;
              if (!window.confirm(`Confirma o desbloqueio do login ${{login}} por 48 horas?`)) return;
              unlockButton.disabled = true;
              detailsStatus.textContent = `Desbloqueando ${{login}} no MK-AUTH...`;
              try {{
                const unlockResponse = await fetch('/api/v1/integrations/mkauth/trust-unlock', {{
                  method: 'POST',
                  headers: {{ 'Content-Type': 'application/json', Accept: 'application/json' }},
                  body: JSON.stringify({{ client_uuid: clientUuid, login, reason: reason.trim(), confirmed: true }}),
                }});
                if (!unlockResponse.ok) throw new Error('request_failed');
                const result = await unlockResponse.json();
                if (result.status !== 'unlocked') throw new Error(result.reason || result.status);
                detailsStatus.textContent = `Login ${{login}} desbloqueado • validade registrada por 48 horas`;
                actionRow.remove();
                loadTrustUnlocks(true);
              }} catch (error) {{
                const reasonText = error instanceof Error ? error.message : 'unlock_failed';
                detailsStatus.textContent = `Não foi possível desbloquear: ${{reasonText}}`;
                unlockButton.disabled = false;
              }}
            }});
            actionCell.appendChild(unlockButton);
            actionRow.append(actionLabel, actionCell);
            detailsBody.appendChild(actionRow);
          }}
          detailsStatus.textContent = 'Consulta concluída • somente leitura';
          detailsPanel.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
        }} catch (_) {{
          detailsStatus.textContent = 'Não foi possível consultar os detalhes deste cliente no MK-AUTH.';
        }}
      }};
      let trustUnlocksLoaded = false;
      const loadTrustUnlocks = async (force = false) => {{
        if (trustUnlocksLoaded && !force) return;
        const historyBody = document.getElementById('trust-unlocks-body');
        try {{
          const response = await fetch('/api/v1/integrations/mkauth/trust-unlocks', {{ headers: {{ Accept: 'application/json' }} }});
          if (!response.ok) throw new Error('request_failed');
          const data = await response.json();
          historyBody.replaceChildren();
          data.records.forEach((record) => {{
            const row = document.createElement('tr');
            const statusLabels = {{ active: 'Ativo', expired: 'Encerrado pelo prazo', cancelled: 'Encerrado manualmente', paid: 'Resolvido por pagamento' }};
            [record.login, record.reason, record.unlocked_at, record.expires_at, statusLabels[record.status] || record.status].forEach((value) => {{
              const cell = document.createElement('td');
              cell.textContent = value;
              row.appendChild(cell);
            }});
            const actionCell = document.createElement('td');
            if (record.status === 'active') {{
              const cancelButton = document.createElement('button');
              cancelButton.type = 'button';
              cancelButton.textContent = 'ENCERRAR AGORA';
              cancelButton.addEventListener('click', async () => {{
                if (!window.confirm(`Encerrar agora a liberação temporária de ${{record.login}}?`)) return;
                cancelButton.disabled = true;
                try {{
                  const cancelResponse = await fetch(`/api/v1/integrations/mkauth/trust-unlocks/${{encodeURIComponent(record.id)}}/cancel`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json', Accept: 'application/json' }},
                    body: JSON.stringify({{ confirmed: true }}),
                  }});
                  if (!cancelResponse.ok) throw new Error('request_failed');
                  const result = await cancelResponse.json();
                  if (result.status !== 'cancelled') throw new Error(result.reason || result.status);
                  await loadTrustUnlocks(true);
                }} catch (error) {{
                  const reasonText = error instanceof Error ? error.message : 'cancel_failed';
                  window.alert(`Não foi possível encerrar a liberação: ${{reasonText}}`);
                  cancelButton.disabled = false;
                }}
              }});
              actionCell.appendChild(cancelButton);
            }} else {{
              actionCell.textContent = '-';
            }}
            row.appendChild(actionCell);
            historyBody.appendChild(row);
          }});
          if (!data.records.length) {{
            const row = document.createElement('tr');
            const cell = document.createElement('td');
            cell.colSpan = 6;
            cell.textContent = 'Nenhum desbloqueio de confiança registrado.';
            row.appendChild(cell);
            historyBody.appendChild(row);
          }}
          trustUnlocksLoaded = true;
        }} catch (_) {{
          historyBody.replaceChildren();
          const row = document.createElement('tr');
          const cell = document.createElement('td');
          cell.colSpan = 6;
          cell.textContent = 'Não foi possível carregar o histórico.';
          row.appendChild(cell);
          historyBody.appendChild(row);
        }}
      }};
      document.getElementById('load-trust-unlocks').addEventListener('click', () => loadTrustUnlocks(true));
      document.getElementById('mkauth-client-select').addEventListener('change', (event) => {{
        const selectedIndex = event.target.value;
        if (selectedIndex === '') {{
          document.getElementById('order-external-customer-id').value = '';
          return;
        }}
        const client = mkauthClientsCache[Number(selectedIndex)];
        if (!client) return;
        document.getElementById('order-customer-name').value = client.name;
        document.getElementById('order-external-customer-id').value = client.uuid;
        document.getElementById('order-address').value = client.address || `${{client.city}}/${{client.state}}`;
        const coordinates = client.coordinates && client.coordinates !== '-'
          ? client.coordinates.split(',').map((value) => value.trim())
          : [];
        document.getElementById('order-latitude').value = coordinates[0] || '';
        document.getElementById('order-longitude').value = coordinates[1] || '';
        markDirty();
      }});
      const loadMkauthTickets = async (force = false) => {{
        if (mkauthTicketsLoaded && !force) return;
        const ticketsStatus = document.getElementById('mkauth-tickets-status');
        const ticketsBody = document.getElementById('mkauth-tickets-body');
        ticketsStatus.textContent = 'Consultando chamados no MK-AUTH...';
        try {{
          const response = await fetch('/api/v1/integrations/mkauth/tickets', {{ headers: {{ Accept: 'application/json' }} }});
          if (!response.ok) throw new Error('request_failed');
          const data = await response.json();
          if (data.status !== 'connected') throw new Error(data.reason || 'integration_unavailable');
          ticketsBody.replaceChildren();
          data.tickets.forEach((ticket) => {{
            const row = document.createElement('tr');
            [ticket.number, ticket.opened_at, ticket.login, ticket.subject, ticket.priority, ticket.status, ticket.uuid || '-'].forEach((value) => {{
              const cell = document.createElement('td');
              cell.textContent = value;
              row.appendChild(cell);
            }});
            const actionCell = document.createElement('td');
            const createButton = document.createElement('button');
            createButton.type = 'button';
            createButton.textContent = 'GERAR OS';
            createButton.addEventListener('click', async () => {{
              await loadMkauthClients();
              const clientIndex = mkauthClientsCache.findIndex((client) => client.login === ticket.login);
              if (clientIndex < 0) {{
                ticketsStatus.textContent = `Cliente com login ${{ticket.login}} não foi localizado na consulta do MK-AUTH.`;
                return;
              }}
              const client = mkauthClientsCache[clientIndex];
              const clientSelect = document.getElementById('mkauth-client-select');
              clientSelect.value = String(clientIndex);
              document.getElementById('order-customer-name').value = client.name;
              document.getElementById('order-address').value = client.address || `${{client.city}}/${{client.state}}`;
              document.getElementById('order-external-customer-id').value = client.uuid;
              document.getElementById('order-external-ticket-id').value = ticket.number;
              const coordinates = client.coordinates && client.coordinates !== '-'
                ? client.coordinates.split(',').map((value) => value.trim())
                : [];
              document.getElementById('order-latitude').value = coordinates[0] || '';
              document.getElementById('order-longitude').value = coordinates[1] || '';
              const priorityMap = {{ baixa: 'low', normal: 'normal', alta: 'high', urgente: 'urgent' }};
              document.getElementById('order-priority').value = priorityMap[ticket.priority.toLowerCase()] || 'normal';
              document.getElementById('order-source-status').textContent =
                `OS preparada a partir do chamado ${{ticket.number}} • ${{ticket.subject}}. Revise os dados e clique em CRIAR OS.`;
              markDirty();
              activateModule('work-orders');
              window.scrollTo({{ top: 0, behavior: 'smooth' }});
            }});
            actionCell.appendChild(createButton);
            row.appendChild(actionCell);
            ticketsBody.appendChild(row);
          }});
          if (!data.tickets.length) {{
            const row = document.createElement('tr');
            const cell = document.createElement('td');
            cell.colSpan = 8;
            cell.textContent = 'Nenhum chamado retornado pelo MK-AUTH.';
            row.appendChild(cell);
            ticketsBody.appendChild(row);
          }}
          ticketsStatus.textContent = `${{data.count}} chamado(s) carregado(s) • somente leitura`;
          mkauthTicketsLoaded = true;
        }} catch (error) {{
          const reason = error instanceof Error ? error.message : 'integration_unavailable';
          ticketsStatus.textContent = `Não foi possível consultar os chamados: ${{reason}}`;
        }}
      }};
      document.getElementById('load-mkauth-tickets').addEventListener('click', () => loadMkauthTickets(true));
      const activateModule = (moduleName, updateLocation = true) => {{
        const selected = moduleNames.has(moduleName) ? moduleName : 'work-orders';
        menuButtons.forEach((button) => {{
          const active = button.dataset.target === selected;
          button.classList.toggle('active', active);
          button.setAttribute('aria-current', active ? 'page' : 'false');
        }});
        document.querySelectorAll('.menu-category').forEach((category) => {{
          category.open = Boolean(category.querySelector(`.menu-button[data-target="${{selected}}"]`));
        }});
        modulePanels.forEach((panel) => {{
          panel.classList.toggle('active', panel.dataset.module === selected);
        }});
        localStorage.setItem('central-active-module', selected);
        if (updateLocation) history.replaceState(null, '', `#${{selected}}`);
        if (selected === 'mkauth') loadMkauthPlans();
        if (selected === 'routeros-diagnostic') loadRouterosDiagnostic();
        if (selected === 'mkauth-clients') loadMkauthClients();
        if (selected === 'mkauth-inactive-clients') loadMkauthClients();
        if (selected === 'mkauth-additional-clients') loadMkauthAdditionalClients();
        if (selected === 'mkauth-titles') loadMkauthTitles();
        if (selected === 'financial') {{ loadTrustUnlocks(); loadPixSimulations(); }}
        if (selected === 'mkauth-tickets') loadMkauthTickets();
        if (selected === 'work-orders') loadMkauthClients();
      }};
      menuButtons.forEach((button) => {{
        button.addEventListener('click', () => activateModule(button.dataset.target));
      }});
      activateModule(
        location.hash.slice(1) || localStorage.getItem('central-active-module') || 'work-orders',
        false,
      );
      const markDirty = () => {{
        status.textContent = 'Há dados preenchidos ainda não enviados.';
      }};
      document.querySelectorAll('form').forEach((form) => {{
        form.addEventListener('input', markDirty);
        form.addEventListener('change', markDirty);
        form.addEventListener('submit', () => {{ status.textContent = 'Enviando dados...'; }});
      }});
    }})();
  </script>
</body>
</html>"""


@router.get(
    "/central/work-orders/{work_order_id}/mkauth-close",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def central_confirm_mkauth_ticket_close(work_order_id: str) -> str:
    orders = await simulated_mkauth_gateway.list_work_orders(None)
    order = next((item for item in orders if item.id == work_order_id), None)
    if order is None:
        raise HTTPException(404, "work_order_not_found")
    if order.status.value != "completed":
        raise HTTPException(409, "work_order_must_be_completed")
    if not order.external_ticket_id:
        raise HTTPException(409, "work_order_has_no_mkauth_ticket")
    if order.external_ticket_closed_at is not None:
        raise HTTPException(409, "mkauth_ticket_already_closed")
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Fechar chamado MK-AUTH</title>
<style>body{{margin:0;background:#f3f8f7;color:#17332f;font:16px system-ui,sans-serif}}main{{width:min(720px,92vw);margin:40px auto}}section{{background:white;padding:24px;border-radius:14px;box-shadow:0 2px 10px #17332f18}}.warning{{background:#fff0c2;border-left:5px solid #e59b00;padding:14px}}label{{display:block;margin:16px 0}}textarea{{width:100%;min-height:130px;padding:10px;border:1px solid #aac0bb;border-radius:8px;font:inherit}}button,a{{display:inline-block;border:0;border-radius:8px;padding:10px 14px;background:#075e54;color:white;text-decoration:none;font:inherit;cursor:pointer}}a{{background:#456b65}}</style></head>
<body><main><section><h1>Fechar chamado no MK-AUTH</h1>
<p><b>OS:</b> {escape(order.code)} — {escape(order.customer_name)}</p>
<p><b>Referência do chamado:</b> {escape(order.external_ticket_id)}</p>
<p class="warning"><b>Atenção:</b> esta ação gravará no MK-AUTH real da bancada e não poderá ser repetida pelo aplicativo.</p>
<form method="post" action="/central/work-orders/{escape(order.id)}/mkauth-close">
<label>Motivo do fechamento<textarea name="reason" minlength="10" maxlength="2000" required placeholder="Descreva o serviço executado e a solução aplicada."></textarea></label>
<label><input name="confirmed" type="checkbox" value="yes" required> Confirmo que a OS foi concluída e desejo fechar o chamado no MK-AUTH.</label>
<button type="submit">CONFIRMAR FECHAMENTO</button> <a href="/central#work-orders">CANCELAR</a>
</form></section></main></body></html>"""


@router.post(
    "/central/work-orders/{work_order_id}/mkauth-close",
    include_in_schema=False,
)
async def central_close_mkauth_ticket(
    work_order_id: str, request: Request
) -> RedirectResponse:
    settings = get_integration_settings()
    if settings.mkauth_mode != "real" or not settings.mkauth_writes_enabled:
        raise HTTPException(403, "mkauth_writes_disabled")
    fields = parse_qs((await request.body()).decode("utf-8"))
    reason = fields.get("reason", [""])[0].strip()
    confirmed = fields.get("confirmed", [""])[0] == "yes"
    if not confirmed or not 10 <= len(reason) <= 2000:
        raise HTTPException(422, "mkauth_ticket_close_confirmation_required")
    orders = await simulated_mkauth_gateway.list_work_orders(None)
    order = next((item for item in orders if item.id == work_order_id), None)
    if order is None:
        raise HTTPException(404, "work_order_not_found")
    if order.status.value != "completed":
        raise HTTPException(409, "work_order_must_be_completed")
    if not order.external_ticket_id:
        raise HTTPException(409, "work_order_has_no_mkauth_ticket")
    if order.external_ticket_closed_at is not None:
        raise HTTPException(409, "mkauth_ticket_already_closed")
    client = MkAuthApiClient(
        settings.mkauth_base_url,
        settings.mkauth_client_id,
        settings.mkauth_client_secret,
        settings.mkauth_verify_ssl,
        settings.mkauth_allow_http and settings.app_env == "development",
    )
    try:
        ticket_number = await client.resolve_support_ticket_number(
            order.external_ticket_id
        )
        await client.close_support_ticket(ticket_number, reason)
        await simulated_mkauth_gateway.mark_external_ticket_closed(work_order_id)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    except httpx.HTTPError as error:
        raise HTTPException(502, "mkauth_ticket_close_failed") from error
    return RedirectResponse("/central#work-orders", status_code=303)


@router.post("/central/technicians", include_in_schema=False)
async def central_create_technician(
    request: Request,
    session: dict = Depends(require_central_roles("owner", "admin")),
) -> RedirectResponse:
    fields = parse_qs((await request.body()).decode("utf-8"))
    name = fields.get("name", [""])[0].strip()
    username = fields.get("username", [""])[0].strip().lower()
    password = fields.get("password", [""])[0]
    if len(name) < 3 or len(username) < 3 or len(password) < 8:
        raise HTTPException(422, "invalid_technician_data")
    organization_id = session["organization"]["id"]
    active_technicians = sum(
        bool(item["active"])
        for item in technician_store.list_all(organization_id)
    )
    try:
        subscription_store.ensure_capacity(
            organization_id, "technicians", active_technicians
        )
        technician_store.create(
            name, username, password, organization_id
        )
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    return RedirectResponse("/central", status_code=303)


@router.post("/central/users", include_in_schema=False)
async def central_create_user(
    request: Request,
    session: dict = Depends(require_central_roles("owner", "admin")),
) -> RedirectResponse:
    fields = parse_qs((await request.body()).decode("utf-8"))
    name = fields.get("name", [""])[0].strip()
    username = fields.get("username", [""])[0].strip().casefold()
    password = fields.get("password", [""])[0]
    role = fields.get("role", [""])[0]
    if (
        len(name) < 3
        or len(username) < 3
        or len(password) < 8
        or role not in CENTRAL_USER_ROLES
    ):
        raise HTTPException(422, "invalid_central_user_data")
    if session["user"]["role"] == "admin" and role == "owner":
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
        central_user_store.create(
            organization_id, name, username, password, role
        )
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    return RedirectResponse("/central#central-users", status_code=303)


@router.post("/central/portal-customers", include_in_schema=False)
async def central_create_portal_customer(
    request: Request,
    session: dict = Depends(require_central_roles("owner", "admin")),
) -> RedirectResponse:
    fields = parse_qs((await request.body()).decode("utf-8"))
    name = fields.get("name", [""])[0].strip()
    username = fields.get("username", [""])[0].strip().casefold()
    password = fields.get("password", [""])[0]
    external_login = fields.get("external_login", [""])[0].strip()
    external_customer_id = fields.get("external_customer_id", [""])[0].strip()
    if (
        len(name) < 3
        or len(username) < 3
        or len(password) < 8
        or not external_login
        or not external_customer_id
    ):
        raise HTTPException(422, "invalid_portal_customer_data")
    try:
        portal_customer_store.create(
            session["organization"]["id"],
            name,
            username,
            password,
            external_customer_id,
            external_login,
        )
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    return RedirectResponse("/central#portal-customers", status_code=303)


@router.post("/central/branding", include_in_schema=False)
async def central_update_branding(
    request: Request,
    session: dict = Depends(require_central_roles("owner", "admin")),
) -> RedirectResponse:
    fields = parse_qs((await request.body()).decode("utf-8"))
    name = fields.get("name", [""])[0].strip()
    primary_color = fields.get("primary_color", [""])[0].strip()
    support_email = fields.get("support_email", [""])[0].strip()
    support_phone = fields.get("support_phone", [""])[0].strip()
    if (
        len(name) < 3
        or not re.fullmatch(r"#[0-9a-fA-F]{6}", primary_color)
        or len(support_email) > 150
        or (support_email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", support_email))
        or len(support_phone) > 30
    ):
        raise HTTPException(422, "invalid_organization_branding")
    organization_store.update_branding(
        session["organization"]["id"],
        name,
        primary_color,
        support_email,
        support_phone,
    )
    return RedirectResponse("/central#branding", status_code=303)


@router.post(
    "/central/portal-customers/invite-from-mkauth", include_in_schema=False
)
async def central_invite_mkauth_customer_to_portal(
    request: Request,
    session: dict = Depends(require_central_roles("owner", "admin")),
) -> RedirectResponse:
    fields = parse_qs((await request.body()).decode("utf-8"))
    name = fields.get("name", [""])[0].strip()
    username = fields.get("username", [""])[0].strip().casefold()
    external_login = fields.get("external_login", [""])[0].strip()
    external_customer_id = fields.get("external_customer_id", [""])[0].strip()
    if (
        len(name) < 3
        or len(username) < 3
        or not external_login
        or not external_customer_id
    ):
        raise HTTPException(422, "invalid_mkauth_portal_invite_data")

    organization_id = session["organization"]["id"]
    customer = next(
        (
            item
            for item in portal_customer_store.list_all(organization_id)
            if item.get("external_customer_id") == external_customer_id
            or str(item.get("external_login") or "").casefold()
            == external_login.casefold()
        ),
        None,
    )
    if customer is None:
        try:
            customer = portal_customer_store.create(
                organization_id,
                name,
                username,
                secrets.token_urlsafe(32),
                external_customer_id,
                external_login,
            )
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
    if not customer["active"]:
        raise HTTPException(409, "portal_customer_inactive")

    invite = portal_invite_store.create(organization_id, customer["id"])
    invite_url = str(
        request.url_for(
            "portal_invite_page",
            organization_slug=session["organization"]["slug"],
            token=invite["token"],
        )
    )
    record_simulated_portal_invite_message(
        organization_id, external_login, invite_url
    )
    return RedirectResponse("/central#whatsapp", status_code=303)


@router.post(
    "/central/portal-customers/{customer_id}/link", include_in_schema=False
)
async def central_link_portal_customer(
    customer_id: str,
    request: Request,
    session: dict = Depends(require_central_roles("owner", "admin")),
) -> RedirectResponse:
    fields = parse_qs((await request.body()).decode("utf-8"))
    external_login = fields.get("external_login", [""])[0].strip()
    external_customer_id = fields.get("external_customer_id", [""])[0].strip()
    if not external_login or not external_customer_id:
        raise HTTPException(422, "invalid_portal_customer_link")
    try:
        portal_customer_store.set_external_customer(
            session["organization"]["id"],
            customer_id,
            external_customer_id,
            external_login,
        )
    except KeyError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    return RedirectResponse("/central#portal-customers", status_code=303)


@router.post(
    "/central/portal-customers/{customer_id}/invite", include_in_schema=False
)
async def central_invite_portal_customer(
    customer_id: str,
    request: Request,
    session: dict = Depends(require_central_roles("owner", "admin")),
) -> RedirectResponse:
    organization_id = session["organization"]["id"]
    customer = next(
        (
            item
            for item in portal_customer_store.list_all(organization_id)
            if item["id"] == customer_id and item["active"]
        ),
        None,
    )
    if customer is None:
        raise HTTPException(404, "portal_customer_not_found")
    invite = portal_invite_store.create(organization_id, customer_id)
    organization_slug = session["organization"]["slug"]
    invite_url = str(
        request.url_for(
            "portal_invite_page",
            organization_slug=organization_slug,
            token=invite["token"],
        )
    )
    record_simulated_portal_invite_message(
        organization_id,
        customer["external_login"] or customer["username"],
        invite_url,
    )
    return RedirectResponse("/central#whatsapp", status_code=303)


@router.post(
    "/central/portal-customers/{customer_id}/toggle", include_in_schema=False
)
async def central_toggle_portal_customer(
    customer_id: str,
    request: Request,
    session: dict = Depends(require_central_roles("owner", "admin")),
) -> RedirectResponse:
    fields = parse_qs((await request.body()).decode("utf-8"))
    active = fields.get("active", ["0"])[0] == "1"
    try:
        portal_customer_store.set_active(
            session["organization"]["id"], customer_id, active
        )
    except KeyError as error:
        raise HTTPException(404, str(error)) from error
    return RedirectResponse("/central#portal-customers", status_code=303)


@router.post(
    "/central/portal-customers/{customer_id}/password", include_in_schema=False
)
async def central_reset_portal_customer_password(
    customer_id: str,
    request: Request,
    session: dict = Depends(require_central_roles("owner", "admin")),
) -> RedirectResponse:
    fields = parse_qs((await request.body()).decode("utf-8"))
    password = fields.get("password", [""])[0]
    if len(password) < 8:
        raise HTTPException(422, "invalid_portal_customer_password")
    try:
        portal_customer_store.reset_password(
            session["organization"]["id"], customer_id, password
        )
    except KeyError as error:
        raise HTTPException(404, str(error)) from error
    return RedirectResponse("/central#portal-customers", status_code=303)


@router.post("/central/subscription/simulate-plan", include_in_schema=False)
async def central_simulate_plan_change(
    request: Request,
    session: dict = Depends(require_central_roles("owner")),
) -> RedirectResponse:
    fields = parse_qs((await request.body()).decode("utf-8"))
    plan_code = fields.get("plan_code", [""])[0]
    try:
        plan = SAAS_PLANS.get(plan_code)
        if plan is None:
            raise ValueError("invalid_saas_plan")
        organization_id = session["organization"]["id"]
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
            raise ValueError("saas_plan_below_current_usage")
        subscription_store.simulate_plan_change(
            organization_id, plan_code
        )
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    return RedirectResponse("/central#subscription", status_code=303)


@router.post("/central/users/{user_id}/toggle", include_in_schema=False)
async def central_toggle_user(
    user_id: str,
    request: Request,
    session: dict = Depends(require_central_roles("owner", "admin")),
) -> RedirectResponse:
    if user_id == session["user"]["id"]:
        raise HTTPException(409, "cannot_disable_current_user")
    organization_id = session["organization"]["id"]
    target = next(
        (
            item
            for item in central_user_store.list_all(organization_id)
            if item["id"] == user_id
        ),
        None,
    )
    if target is None:
        raise HTTPException(404, "central_user_not_found")
    if session["user"]["role"] == "admin" and target["role"] == "owner":
        raise HTTPException(403, "admin_cannot_manage_owner")
    fields = parse_qs((await request.body()).decode("utf-8"))
    active = fields.get("active", ["0"])[0] == "1"
    if active and not target["active"]:
        active_users = sum(
            bool(item["active"])
            for item in central_user_store.list_all(organization_id)
        )
        try:
            subscription_store.ensure_capacity(
                organization_id, "central_users", active_users
            )
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
    central_user_store.set_active(user_id, organization_id, active)
    return RedirectResponse("/central#central-users", status_code=303)


@router.post(
    "/central/work-orders/{work_order_id}/archive", include_in_schema=False
)
async def central_archive_work_order(work_order_id: str) -> RedirectResponse:
    try:
        await simulated_mkauth_gateway.set_work_order_archived(work_order_id, True)
    except KeyError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    return RedirectResponse("/central#work-orders", status_code=303)


@router.get(
    "/central/work-orders/{work_order_id}/delete",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def central_confirm_work_order_delete(work_order_id: str) -> str:
    orders = await simulated_mkauth_gateway.list_work_orders(None)
    order = next((item for item in orders if item.id == work_order_id), None)
    if order is None or order.deleted_at is not None:
        raise HTTPException(404, "work_order_not_found")
    if order.status.value != "assigned":
        raise HTTPException(409, "only_unstarted_work_orders_can_be_deleted")
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Excluir OS</title>
<style>body{{margin:0;background:#f3f8f7;color:#17332f;font:16px system-ui,sans-serif}}main{{width:min(720px,92vw);margin:40px auto}}section{{background:white;padding:24px;border-radius:14px;box-shadow:0 2px 10px #17332f18}}.warning{{background:#fee4e2;border-left:5px solid #b42318;padding:14px}}label{{display:block;margin:16px 0}}textarea{{width:100%;min-height:120px;padding:10px;border:1px solid #aac0bb;border-radius:8px;font:inherit}}button,a{{display:inline-block;border:0;border-radius:8px;padding:10px 14px;color:white;text-decoration:none;font:inherit;cursor:pointer}}button{{background:#b42318}}a{{background:#456b65}}</style></head>
<body><main><section><h1>Excluir ordem de serviço</h1>
<p><b>{escape(order.code)}</b> — {escape(order.customer_name)}</p>
<p class="warning"><b>Atenção:</b> a OS desaparecerá da operação e do celular. O chamado MK-AUTH, caso exista, não será alterado.</p>
<form method="post" action="/central/work-orders/{escape(order.id)}/delete">
<label>Motivo da exclusão<textarea name="reason" minlength="10" maxlength="500" required placeholder="Ex.: problema resolvido remotamente, sem necessidade de visita."></textarea></label>
<label><input name="confirmed" type="checkbox" value="yes" required> Confirmo a exclusão desta OS ainda não iniciada.</label>
<button type="submit">CONFIRMAR EXCLUSÃO</button> <a href="/central#work-orders">CANCELAR</a>
</form></section></main></body></html>"""


@router.post(
    "/central/work-orders/{work_order_id}/delete", include_in_schema=False
)
async def central_delete_work_order(
    work_order_id: str, request: Request
) -> RedirectResponse:
    fields = parse_qs((await request.body()).decode("utf-8"))
    reason = fields.get("reason", [""])[0].strip()
    confirmed = fields.get("confirmed", [""])[0] == "yes"
    if not confirmed or not 10 <= len(reason) <= 500:
        raise HTTPException(422, "work_order_deletion_confirmation_required")
    try:
        await simulated_mkauth_gateway.delete_unstarted_work_order(
            work_order_id, reason
        )
    except KeyError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    return RedirectResponse("/central#work-orders", status_code=303)


@router.post(
    "/central/work-orders/{work_order_id}/restore", include_in_schema=False
)
async def central_restore_work_order(work_order_id: str) -> RedirectResponse:
    try:
        await simulated_mkauth_gateway.set_work_order_archived(work_order_id, False)
    except KeyError as error:
        raise HTTPException(404, str(error)) from error
    return RedirectResponse("/central#archived-orders", status_code=303)


@router.post("/central/work-orders/{work_order_id}/assign", include_in_schema=False)
async def central_assign_work_order(
    work_order_id: str,
    request: Request,
    session: dict = Depends(require_central_session),
) -> RedirectResponse:
    fields = parse_qs((await request.body()).decode("utf-8"))
    technician_id = fields.get("technician_id", [""])[0]
    active_ids = {
        item["id"]
        for item in technician_store.list_all(session["organization"]["id"])
        if item["active"]
    }
    if technician_id not in active_ids:
        raise HTTPException(422, "invalid_or_inactive_technician")
    try:
        order = await simulated_mkauth_gateway.assign_work_order(
            work_order_id, technician_id
        )
    except KeyError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    from app.core.sync_store import SyncOperationStore
    from app.core.config import get_settings

    SyncOperationStore(get_settings().database_url).append_change(
        {
            "entity_type": "work_order",
            "entity_id": order.id,
            "kind": "upsert",
            "payload": order.model_dump(mode="json"),
        }
    )
    return RedirectResponse("/central", status_code=303)


@router.post("/central/work-orders/{work_order_id}/planning", include_in_schema=False)
async def central_update_work_order_planning(
    work_order_id: str, request: Request
) -> RedirectResponse:
    fields = parse_qs((await request.body()).decode("utf-8"), keep_blank_values=True)
    priority = fields.get("priority", ["normal"])[0]
    scheduled_text = fields.get("scheduled_at", [""])[0].strip()
    if priority not in {"low", "normal", "high", "urgent"}:
        raise HTTPException(422, "invalid_priority")
    try:
        from datetime import timedelta

        scheduled_at = (
            datetime.fromisoformat(scheduled_text).replace(
                tzinfo=timezone(timedelta(hours=-3))
            )
            if scheduled_text
            else None
        )
        order = await simulated_mkauth_gateway.update_work_order_planning(
            work_order_id, priority, scheduled_at
        )
    except KeyError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    from app.core.sync_store import SyncOperationStore
    from app.core.config import get_settings

    SyncOperationStore(get_settings().database_url).append_change(
        {
            "entity_type": "work_order",
            "entity_id": order.id,
            "kind": "upsert",
            "payload": order.model_dump(mode="json"),
        }
    )
    return RedirectResponse("/central", status_code=303)


@router.post("/central/technicians/{technician_id}/toggle", include_in_schema=False)
async def central_toggle_technician(
    technician_id: str,
    request: Request,
    session: dict = Depends(require_central_roles("owner", "admin")),
) -> RedirectResponse:
    fields = parse_qs((await request.body()).decode("utf-8"))
    active = fields.get("active", ["0"])[0] == "1"
    organization_id = session["organization"]["id"]
    technicians = technician_store.list_all(organization_id)
    target = next(
        (item for item in technicians if item["id"] == technician_id), None
    )
    if target is None:
        raise HTTPException(404, "technician_not_found")
    if active and not target["active"]:
        active_technicians = sum(bool(item["active"]) for item in technicians)
        try:
            subscription_store.ensure_capacity(
                organization_id, "technicians", active_technicians
            )
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
    try:
        technician_store.set_active(
            technician_id, active, organization_id
        )
    except KeyError as error:
        raise HTTPException(404, str(error)) from error
    return RedirectResponse("/central", status_code=303)


@router.get("/central/work-orders/{work_order_id}/evidence", response_class=HTMLResponse)
async def central_evidence_gallery(
    work_order_id: str,
    session: dict = Depends(require_central_session),
) -> str:
    organization_id = session["organization"]["id"]
    orders = await simulated_mkauth_gateway.list_work_orders(
        None, organization_id
    )
    order = next((item for item in orders if item.id == work_order_id), None)
    if order is None:
        raise HTTPException(404, "work_order_not_found")
    files = list_evidence(work_order_id, organization_id)
    equipment = list_equipment(work_order_id, organization_id)
    gallery = "".join(
        f"<figure><a href='{escape(item['url'])}' target='_blank'>"
        f"<img src='{escape(item['url'])}' alt='{escape(item['category'])}'></a>"
        f"<figcaption>{'Assinatura do cliente' if item['category'] == 'customer_signature' else 'Foto da instalação'}</figcaption></figure>"
        for item in files
    ) or "<p>Nenhuma foto ou assinatura sincronizada.</p>"
    equipment_rows = "".join(
        f"<tr><td>{escape(item['serial'])}</td><td>{escape(item['id'])}</td></tr>"
        for item in equipment
    ) or "<tr><td colspan='2'>Nenhum equipamento sincronizado.</td></tr>"
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Comprovações {escape(order.code)}</title>
<style>body{{margin:0;background:#f3f8f7;color:#17332f;font:16px system-ui,sans-serif}}header{{background:#075e54;color:white;padding:22px 5vw}}main{{width:min(1050px,92vw);margin:24px auto}}a{{color:#075e54}}.back{{display:inline-block;margin-bottom:18px}}section{{background:white;padding:18px;border-radius:14px;margin-bottom:18px;box-shadow:0 2px 10px #17332f18}}.gallery{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:15px}}figure{{margin:0}}img{{width:100%;height:260px;object-fit:contain;background:#e8f0ee;border-radius:10px}}figcaption{{padding:8px 0}}table{{width:100%;border-collapse:collapse}}th,td{{padding:10px;border-bottom:1px solid #dce8e5;text-align:left}}.simulation{{background:#fff0c2;padding:12px;border-left:5px solid #e59b00}}</style></head>
<body><header><h1>Comprovações da {escape(order.code)}</h1><div>{escape(order.customer_name)} • {escape(order.address)}</div></header>
<main><a class="back" href="/central">← Voltar ao painel</a><p class="simulation"><b>MODO SIMULADO</b> — dados exclusivos da bancada.</p>
<p><a href="/central/work-orders/{escape(order.id)}/report">Abrir relatório técnico da OS</a></p>
<section><h2>Fotos e assinatura</h2><div class="gallery">{gallery}</div></section>
<section><h2>Equipamentos lidos por QR Code</h2><table><thead><tr><th>Número de série</th><th>Identificador</th></tr></thead><tbody>{equipment_rows}</tbody></table></section></main></body></html>"""


@router.get("/central/work-orders/{work_order_id}/report", response_class=HTMLResponse)
async def central_work_order_report(
    work_order_id: str,
    session: dict = Depends(require_central_session),
) -> str:
    organization_id = session["organization"]["id"]
    orders = await simulated_mkauth_gateway.list_work_orders(
        None, organization_id
    )
    order = next((item for item in orders if item.id == work_order_id), None)
    if order is None:
        raise HTTPException(404, "work_order_not_found")
    files = list_evidence(work_order_id, organization_id)
    equipment = list_equipment(work_order_id, organization_id)
    provisioning = provisioning_store.list_for_work_order(
        work_order_id, organization_id
    )
    material_movements = simulated_inventory_gateway.list_movements(
        work_order_id, session["organization"]["id"]
    )
    photos = [item for item in files if item["category"] == "installation_photo"]
    signatures = [item for item in files if item["category"] == "customer_signature"]
    checklist = (
        ("Foto da instalação", bool(photos)),
        ("Assinatura do cliente", bool(signatures)),
        ("Equipamento por QR Code", bool(equipment)),
        ("Provisionamento de ONU", bool(provisioning)),
    )
    checklist_rows = "".join(
        f"<tr><td>{escape(label)}</td><td class='{'ok' if ready else 'pending'}'>{'OK' if ready else 'PENDENTE'}</td></tr>"
        for label, ready in checklist
    )
    evidence_cards = "".join(
        f"<figure><img src='{escape(item['url'])}' alt='{escape(item['category'])}'>"
        f"<figcaption>{'Assinatura' if item['category'] == 'customer_signature' else 'Foto da instalação'}</figcaption></figure>"
        for item in files
    ) or "<p>Nenhuma imagem sincronizada.</p>"
    equipment_rows = "".join(
        f"<tr><td>{escape(item['serial'])}</td><td>{escape(item['id'])}</td></tr>"
        for item in equipment
    ) or "<tr><td colspan='2'>Nenhum equipamento sincronizado.</td></tr>"
    provisioning_rows = "".join(
        f"<tr><td>{escape(str(item.get('serial', '-')))}</td>"
        f"<td>{escape(str(item.get('profile', '-')))}</td>"
        f"<td>{escape(str(item.get('signal_dbm', '-')))} dBm</td>"
        f"<td>{escape(str(item.get('created_at', '-')))}</td></tr>"
        for item in provisioning
    ) or "<tr><td colspan='4'>Nenhum provisionamento registrado.</td></tr>"
    material_rows = "".join(
        f"<tr><td>{escape(item['description'])}</td>"
        f"<td>{item['quantity']:g} {escape(item['unit'])}</td>"
        f"<td>{escape(item['created_at'])}</td></tr>"
        for item in material_movements
        if item["kind"] == "consume"
    ) or "<tr><td colspan='3'>Nenhum material consumido nesta OS.</td></tr>"
    generated_at = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Relatório {escape(order.code)}</title>
<style>body{{margin:0;background:#eef5f3;color:#17332f;font:15px system-ui,sans-serif}}main{{width:min(950px,94vw);margin:22px auto}}header,section{{background:white;padding:20px;border-radius:12px;margin-bottom:15px}}header{{border-top:8px solid #075e54}}h1{{margin:0 0 6px}}h2{{font-size:19px;border-bottom:1px solid #ccdcd8;padding-bottom:8px}}.actions{{display:flex;gap:10px;margin-bottom:15px}}button,a.button{{border:0;border-radius:8px;padding:10px 14px;background:#075e54;color:white;text-decoration:none;font:inherit;cursor:pointer}}.simulation{{background:#fff0c2;border-left:5px solid #e59b00;padding:10px}}.meta{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}}table{{width:100%;border-collapse:collapse}}th,td{{padding:9px;border-bottom:1px solid #dce8e5;text-align:left}}.ok{{color:#08785d;font-weight:bold}}.pending{{color:#b05c00;font-weight:bold}}.gallery{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}}figure{{margin:0;break-inside:avoid}}img{{width:100%;height:280px;object-fit:contain;border:1px solid #dce8e5}}figcaption{{padding:6px}}footer{{text-align:center;color:#627773;margin:18px}}@media(max-width:650px){{.meta,.gallery{{grid-template-columns:1fr}}}}@media print{{body{{background:white}}main{{width:100%;margin:0}}.actions,.simulation{{display:none}}header,section{{box-shadow:none;border-radius:0;break-inside:avoid}}a{{color:inherit;text-decoration:none}}}}</style></head>
<body><main><div class="actions"><a class="button" href="/central">Voltar à central</a><button onclick="window.print()">Imprimir ou salvar em PDF</button></div>
<p class="simulation"><b>MODO SIMULADO</b> — relatório gerado exclusivamente com dados da bancada.</p>
<header><h1>Relatório técnico — {escape(order.code)}</h1><div>Gerado em {generated_at}</div></header>
<section><h2>Dados da ordem de serviço</h2><div class="meta"><div><b>Cliente:</b><br>{escape(order.customer_name)}</div><div><b>Situação:</b><br>{escape(order.status.value)}</div><div><b>Endereço:</b><br>{escape(order.address)}</div><div><b>Versão:</b><br>{order.version}</div></div></section>
<section><h2>Checklist das comprovações</h2><table><tbody>{checklist_rows}</tbody></table></section>
<section><h2>Fotos e assinatura</h2><div class="gallery">{evidence_cards}</div></section>
<section><h2>Equipamentos vinculados</h2><table><thead><tr><th>Número de série</th><th>Identificador</th></tr></thead><tbody>{equipment_rows}</tbody></table></section>
<section><h2>Materiais utilizados</h2><table><thead><tr><th>Item</th><th>Quantidade</th><th>Data UTC</th></tr></thead><tbody>{material_rows}</tbody></table></section>
<section><h2>Provisionamento de ONU</h2><table><thead><tr><th>Serial</th><th>Perfil</th><th>Sinal</th><th>Data UTC</th></tr></thead><tbody>{provisioning_rows}</tbody></table></section>
<footer>ISP Field • {escape(session['organization']['name'])} • Documento de ambiente simulado</footer></main></body></html>"""
