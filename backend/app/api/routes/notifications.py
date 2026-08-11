from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from app.api.routes.central_auth import require_central_access
from app.core.portal_customer_store import portal_customer_store
from app.core.tenant_context import get_current_organization
from app.core.whatsapp_message_store import whatsapp_message_store
from app.core.whatsapp_orchestrator import send_whatsapp_message

router = APIRouter(
    prefix="/notifications",
    tags=["whatsapp-simulator"],
    dependencies=[Depends(require_central_access)],
)

_templates = {
    "invoice_reminder": "Lembrete simulado: sua fatura de bancada está disponível.",
    "maintenance": "Aviso simulado: haverá manutenção programada na rede de bancada.",
}


def _phone_for_login(organization_id: str, login: str | None) -> str | None:
    """Busca o telefone real cadastrado do cliente pelo login do MK-AUTH, se
    existir. Sem isso, o envio permanece simulado — nunca inventamos um
    número."""
    if not login:
        return None
    customer = portal_customer_store.get_by_external_login(organization_id, login)
    return customer["phone"] if customer and customer.get("phone") else None


def record_simulated_payment_message(
    login: str,
    title_number: str,
    amount: str,
    remaining_titles: int,
) -> dict:
    organization_id = get_current_organization()
    access_released = remaining_titles == 0
    template = (
        "payment_confirmed_access_released"
        if access_released
        else "payment_confirmed_pending_titles"
    )
    if access_released:
        message_text = (
            f"Pagamento Pix confirmado para o login {login}, título {title_number}, "
            f"no valor de R$ {amount}. Não restam títulos pendentes e o acesso foi normalizado."
        )
    else:
        message_text = (
            f"Pagamento Pix confirmado para o login {login}, título {title_number}, "
            f"no valor de R$ {amount}. Ainda existem {remaining_titles} título(s) pendente(s)."
        )
    phone = _phone_for_login(organization_id, login)
    return send_whatsapp_message(
        organization_id, message_text, template, phone=phone, login=login
    )


def record_simulated_portal_invite_message(
    organization_id: str,
    login: str,
    invite_url: str,
) -> dict:
    message_text = (
        "Seu acesso ao Portal do Cliente foi criado. "
        f"Defina sua senha usando este link temporário: {invite_url}"
    )
    phone = _phone_for_login(organization_id, login)
    return send_whatsapp_message(
        organization_id,
        message_text,
        "portal_access_invite",
        phone=phone,
        login=login,
    )


def list_simulated_messages(organization_id: str | None = None) -> list[dict]:
    return whatsapp_message_store.list_recent(organization_id, limit=200)


@router.get("/messages")
async def list_messages() -> list[dict]:
    return list_simulated_messages()


@router.post("/simulate/{template}")
async def simulate_message(template: str, redirect: bool = False):
    message_text = _templates.get(template)
    if message_text is None:
        raise HTTPException(404, "simulated_template_not_found")
    message = send_whatsapp_message(get_current_organization(), message_text, template)
    if redirect:
        return RedirectResponse("/central", status_code=303)
    return message
