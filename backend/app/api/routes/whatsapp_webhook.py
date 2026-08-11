import hashlib
import hmac

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from app.core.ai_orchestrator import create_draft_for_ticket
from app.core.organization_store import organization_store
from app.core.tenant_context import set_current_organization
from app.core.whatsapp_config_store import whatsapp_config_store
from app.core.whatsapp_consent_store import whatsapp_consent_store
from app.core.whatsapp_contact_store import whatsapp_contact_store
from app.core.whatsapp_message_store import whatsapp_message_store

router = APIRouter(prefix="/api/v1/whatsapp", tags=["whatsapp-webhook"])


def conversation_reference(phone: str) -> str:
    """Identificador usado para vincular o rascunho de IA a uma conversa de
    WhatsApp, no mesmo formato que os chamados usam para os próprios ids."""
    return f"whatsapp:{phone}"


def _verify_signature(app_secret: str, raw_body: bytes, signature_header: str | None) -> bool:
    if not app_secret or not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    provided = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, provided)


@router.get("/webhook/{organization_slug}")
async def verify_whatsapp_webhook(organization_slug: str, request: Request):
    organization = organization_store.get_active_by_slug(organization_slug)
    if organization is None:
        raise HTTPException(404, "organization_not_found")
    config = whatsapp_config_store.get(organization["id"])
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge", "")
    if mode == "subscribe" and config.verify_token and hmac.compare_digest(
        token or "", config.verify_token
    ):
        return PlainTextResponse(challenge)
    raise HTTPException(403, "webhook_verification_failed")


@router.post("/webhook/{organization_slug}")
async def receive_whatsapp_webhook(organization_slug: str, request: Request) -> dict:
    organization = organization_store.get_active_by_slug(organization_slug)
    if organization is None:
        raise HTTPException(404, "organization_not_found")
    organization_id = organization["id"]
    config = whatsapp_config_store.get(organization_id)

    raw_body = await request.body()
    if not _verify_signature(
        config.app_secret, raw_body, request.headers.get("x-hub-signature-256")
    ):
        raise HTTPException(401, "invalid_webhook_signature")

    payload = await request.json()
    set_current_organization(organization_id)
    processed = 0
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            contacts = {
                contact.get("wa_id"): contact.get("profile", {}).get("name")
                for contact in value.get("contacts", [])
            }
            for message in value.get("messages", []):
                phone = message.get("from")
                if not phone:
                    continue
                if message.get("type") == "text":
                    body = message.get("text", {}).get("body", "")
                else:
                    body = f"[mensagem do tipo {message.get('type', 'desconhecido')} recebida]"
                whatsapp_contact_store.upsert(
                    organization_id, phone, display_name=contacts.get(phone)
                )
                whatsapp_message_store.record(
                    organization_id=organization_id,
                    direction="inbound",
                    phone=phone,
                    body=body,
                    status="received",
                    wa_message_id=message.get("id"),
                )
                processed += 1
                if whatsapp_consent_store.is_opt_out_message(body):
                    whatsapp_consent_store.block(organization_id, phone, "customer_requested_stop")
                    continue
                if whatsapp_consent_store.is_blocked(organization_id, phone):
                    continue
                create_draft_for_ticket(
                    organization_id, body, conversation_reference(phone)
                )
    return {"status": "processed", "messages": processed}
