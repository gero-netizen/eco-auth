from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/notifications", tags=["whatsapp-simulator"])

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


@router.get("/messages")
async def list_messages() -> list[dict]:
    return list(reversed(simulated_messages))


@router.post("/simulate/{template}")
async def simulate_message(template: str, redirect: bool = False):
    message_text = _templates.get(template)
    if message_text is None:
        raise HTTPException(404, "simulated_template_not_found")
    message = {
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
