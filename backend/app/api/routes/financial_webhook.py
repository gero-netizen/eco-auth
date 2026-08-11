from fastapi import APIRouter, HTTPException, Request

from app.api.routes.integrations import confirm_title_payment
from app.core.financial_payment_store import financial_payment_store
from app.core.integration_config_store import get_integration_settings
from app.core.mercado_pago_config_store import mercado_pago_config_store
from app.core.organization_store import organization_store
from app.core.tenant_context import set_current_organization
from app.integrations.mercado_pago.client import (
    MercadoPagoUnavailableError,
    mercado_pago_client,
    validate_webhook_signature,
)
from app.integrations.mkauth.api_client import MkAuthApiClient

router = APIRouter(prefix="/api/v1/financial", tags=["financial-webhook"])


@router.post("/webhook/{organization_slug}")
async def receive_pix_webhook(organization_slug: str, request: Request) -> dict:
    organization = organization_store.get_active_by_slug(organization_slug)
    if organization is None:
        raise HTTPException(404, "organization_not_found")
    organization_id = organization["id"]
    config = mercado_pago_config_store.get(organization_id)

    data_id = request.query_params.get("data.id") or request.query_params.get("id")
    if not data_id:
        try:
            body = await request.json()
            data_id = str(
                body.get("data", {}).get("id") or body.get("id") or ""
            )
        except ValueError:
            data_id = ""
    if not data_id:
        raise HTTPException(400, "missing_payment_id")

    if not validate_webhook_signature(
        x_signature=request.headers.get("x-signature", ""),
        x_request_id=request.headers.get("x-request-id"),
        data_id=data_id,
        secret=config.webhook_secret,
    ):
        raise HTTPException(401, "invalid_webhook_signature")

    payment_record = financial_payment_store.get_by_mp_payment_id(organization_id, data_id)
    if payment_record is None:
        # Notificação de um pagamento que não fomos nós que geramos
        # (ou já foi limpo) — nada a fazer, mas confirmamos recebimento.
        return {"status": "ignored"}
    if payment_record["status"] == "confirmed":
        return {"status": "already_confirmed"}  # idempotência: webhook reentregue

    try:
        remote = mercado_pago_client.get_payment(config.access_token, data_id)
    except MercadoPagoUnavailableError as error:
        raise HTTPException(502, str(error)) from error

    if str(remote.get("external_reference")) != payment_record["external_reference"]:
        financial_payment_store.mark_error(
            organization_id, payment_record["id"], "external_reference_mismatch"
        )
        raise HTTPException(409, "external_reference_mismatch")

    remote_amount = float(remote.get("transaction_amount") or 0)
    expected_amount = float(payment_record["amount"])
    if abs(remote_amount - expected_amount) > 0.01:
        financial_payment_store.mark_error(
            organization_id, payment_record["id"], "amount_mismatch"
        )
        raise HTTPException(409, "amount_mismatch")

    status = remote.get("status")
    if status != "approved":
        return {"status": "not_approved_yet", "mercado_pago_status": status}

    settings = get_integration_settings(organization_id)
    if settings.mkauth_mode != "real" or not settings.mkauth_writes_enabled:
        financial_payment_store.mark_error(
            organization_id, payment_record["id"], "mkauth_writes_disabled"
        )
        return {"status": "payment_approved_but_mkauth_writes_disabled"}

    set_current_organization(organization_id)
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
        audit_action="title_payment_confirmed_automatic_pix",
    )
    if result["status"] == "paid":
        financial_payment_store.mark_confirmed(
            organization_id, payment_record["id"], data_id
        )
    else:
        financial_payment_store.mark_error(
            organization_id, payment_record["id"], result.get("status", "unknown_error")
        )
    return {"status": "processed", "mkauth_result": result["status"]}
