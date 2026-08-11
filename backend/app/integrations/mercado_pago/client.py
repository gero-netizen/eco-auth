import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from app.core.config import get_settings

PAYMENTS_API_URL = "https://api.mercadopago.com/v1/payments"


class MercadoPagoUnavailableError(Exception):
    """Levantado sempre que não foi possível confirmar uma chamada real ao
    Mercado Pago (timeout, rede, credenciais inválidas, erro do provedor)."""


@dataclass(frozen=True)
class PixCharge:
    payment_id: str
    status: str
    qr_code: str
    qr_code_base64: str
    ticket_url: str | None


class MercadoPagoClient:
    def __init__(self, timeout_seconds: float | None = None) -> None:
        self._timeout = timeout_seconds or get_settings().ai_request_timeout_seconds

    def create_pix_charge(
        self,
        access_token: str,
        amount: float,
        description: str,
        external_reference: str,
        payer_email: str,
        notification_url: str,
        idempotency_key: str,
    ) -> PixCharge:
        if not access_token:
            raise MercadoPagoUnavailableError("mercado_pago_not_configured")
        payload = {
            "transaction_amount": round(amount, 2),
            "description": description,
            "payment_method_id": "pix",
            "external_reference": external_reference,
            "notification_url": notification_url,
            "payer": {"email": payer_email},
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": idempotency_key,
        }
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(PAYMENTS_API_URL, json=payload, headers=headers)
        except httpx.TimeoutException as error:
            raise MercadoPagoUnavailableError("mercado_pago_request_timeout") from error
        except httpx.HTTPError as error:
            raise MercadoPagoUnavailableError("mercado_pago_network_error") from error
        if response.status_code not in (200, 201):
            raise MercadoPagoUnavailableError(
                f"mercado_pago_provider_error_{response.status_code}"
            )
        try:
            data = response.json()
            transaction_data = data["point_of_interaction"]["transaction_data"]
            return PixCharge(
                payment_id=str(data["id"]),
                status=data["status"],
                qr_code=transaction_data["qr_code"],
                qr_code_base64=transaction_data["qr_code_base64"],
                ticket_url=transaction_data.get("ticket_url"),
            )
        except (KeyError, ValueError, TypeError) as error:
            raise MercadoPagoUnavailableError("mercado_pago_malformed_response") from error

    def get_payment(self, access_token: str, payment_id: str) -> dict:
        if not access_token:
            raise MercadoPagoUnavailableError("mercado_pago_not_configured")
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(f"{PAYMENTS_API_URL}/{payment_id}", headers=headers)
        except httpx.TimeoutException as error:
            raise MercadoPagoUnavailableError("mercado_pago_request_timeout") from error
        except httpx.HTTPError as error:
            raise MercadoPagoUnavailableError("mercado_pago_network_error") from error
        if response.status_code != 200:
            raise MercadoPagoUnavailableError(
                f"mercado_pago_provider_error_{response.status_code}"
            )
        return response.json()


def validate_webhook_signature(
    *, x_signature: str, x_request_id: str | None, data_id: str, secret: str
) -> bool:
    """Mesmo esquema de assinatura (ts + v1, HMAC-SHA256) usado pelo
    Mercado Pago em todos os produtos — valida a janela de tempo (15 min)
    além do HMAC em si."""
    if not x_signature or not secret:
        return False
    parts = dict(
        item.strip().split("=", 1) for item in x_signature.split(",") if "=" in item
    )
    timestamp = parts.get("ts")
    received = parts.get("v1")
    if not timestamp or not received:
        return False
    try:
        timestamp_value = int(timestamp)
    except ValueError:
        return False
    timestamp_seconds = (
        timestamp_value / 1000 if timestamp_value > 10_000_000_000 else timestamp_value
    )
    if abs(datetime.now(UTC).timestamp() - timestamp_seconds) > 900:
        return False
    manifest = f"id:{data_id.lower()};"
    if x_request_id:
        manifest += f"request-id:{x_request_id};"
    manifest += f"ts:{timestamp};"
    expected = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received)


mercado_pago_client = MercadoPagoClient()
