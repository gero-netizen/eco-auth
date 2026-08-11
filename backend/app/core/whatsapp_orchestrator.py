from app.core.whatsapp_config_store import whatsapp_config_store
from app.core.whatsapp_consent_store import whatsapp_consent_store
from app.core.whatsapp_contact_store import whatsapp_contact_store
from app.core.whatsapp_message_store import whatsapp_message_store
from app.integrations.whatsapp.client import WhatsappUnavailableError, whatsapp_client

PLACEHOLDER_PHONE = "+55 (00) 00000-0000"


def send_whatsapp_message(
    organization_id: str,
    body: str,
    template: str,
    phone: str | None = None,
    login: str | None = None,
) -> dict:
    """Ponto único de envio. Sem telefone real conhecido, ou sem IA real
    configurada e ativa, o envio é simulado (rotulado como tal, nunca
    disfarçado de real). Com telefone real e configuração ativa, tenta o
    envio de verdade — se falhar, grava como 'failed', nunca como enviado."""
    config = whatsapp_config_store.get(organization_id)
    has_real_target = bool(phone) and phone != PLACEHOLDER_PHONE

    if login and phone:
        whatsapp_contact_store.upsert(organization_id, phone, login=login)

    if not has_real_target or not config.enabled or not config.access_token:
        return whatsapp_message_store.record(
            organization_id=organization_id,
            direction="outbound",
            phone=phone or PLACEHOLDER_PHONE,
            body=body,
            status="simulated_sent",
            template=template,
            login=login,
        )

    if whatsapp_consent_store.is_blocked(organization_id, phone):
        return whatsapp_message_store.record(
            organization_id=organization_id,
            direction="outbound",
            phone=phone,
            body=body,
            status="blocked",
            template=template,
            login=login,
            error_reason="customer_opted_out",
        )

    try:
        result = whatsapp_client.send_text(
            phone_number_id=config.phone_number_id,
            access_token=config.access_token,
            to=phone,
            body=body,
        )
    except WhatsappUnavailableError as error:
        return whatsapp_message_store.record(
            organization_id=organization_id,
            direction="outbound",
            phone=phone,
            body=body,
            status="failed",
            template=template,
            login=login,
            error_reason=str(error),
        )

    return whatsapp_message_store.record(
        organization_id=organization_id,
        direction="outbound",
        phone=phone,
        body=body,
        status="sent",
        template=template,
        login=login,
        wa_message_id=result.wa_message_id,
    )
