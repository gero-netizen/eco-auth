from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from app.api.routes.central_auth import require_central_access
from app.core.tenant_context import get_current_organization

router = APIRouter(
    prefix="/notifications",
    tags=["whatsapp-simulator"],
    dependencies=[Depends(require_central_access)],
)

simulated_messages: list[dict] = []

_templates = {
    "invoice_reminder": "Lembrete simulado: sua fatura de bancada está disponível.",
    "maintenance": "Aviso simulado: haverá manutenção programada na rede de bancada.",
}


def record_simulated_payment_message(
    login: str,
    title_number: str,
    amount: str,
    remaining_titles: int,
) -> dict:
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
    message = {
        "organization_id": get_current_organization(),
        "id": str(uuid4()),
        "channel": "whatsapp",
        "recipient": "+55 (00) 00000-0000",
        "login": login,
        "template": template,
        "message": message_text,
        "status": "simulated_sent",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "simulated": True,
    }
    simulated_messages.append(message)
    return message


def list_simulated_messages(organization_id: str | None = None) -> list[dict]:
    current_organization_id = organization_id or get_current_organization()
    return list(
        reversed(
            [
                item for item in simulated_messages
                if item.get("organization_id") == current_organization_id
            ]
        )
    )


@router.get("/messages")
async def list_messages() -> list[dict]:
    return list_simulated_messages()


@router.post("/simulate/{template}")
async def simulate_message(template: str, redirect: bool = False):
    message_text = _templates.get(template)
    if message_text is None:
        raise HTTPException(404, "simulated_template_not_found")
    message = {
        "organization_id": get_current_organization(),
        "id": str(uuid4()),
        "channel": "whatsapp",
        "recipient": "+55 (00) 00000-0000",
        "template": template,
        "message": message_text,
        "status": "simulated_sent",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "simulated": True,
    }
    simulated_messages.append(message)
    if redirect:
        return RedirectResponse("/central", status_code=303)
    return message
