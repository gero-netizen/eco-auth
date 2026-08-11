from dataclasses import dataclass

import httpx

from app.core.config import get_settings

GRAPH_API_VERSION = "v20.0"


class WhatsappUnavailableError(Exception):
    """Raised whenever a real send could not be confirmed (timeout, network
    failure, bad credentials, provider error). Callers must record this as a
    FAILED send — never pretend the message went out."""


@dataclass(frozen=True)
class WhatsappSendResult:
    wa_message_id: str


class WhatsappClient:
    def __init__(self, timeout_seconds: float | None = None) -> None:
        self._timeout = timeout_seconds or get_settings().ai_request_timeout_seconds

    def _post(self, phone_number_id: str, access_token: str, payload: dict) -> WhatsappSendResult:
        url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as error:
            raise WhatsappUnavailableError("whatsapp_request_timeout") from error
        except httpx.HTTPError as error:
            raise WhatsappUnavailableError("whatsapp_network_error") from error
        if response.status_code != 200:
            raise WhatsappUnavailableError(f"whatsapp_provider_error_{response.status_code}")
        try:
            data = response.json()
            wa_message_id = data["messages"][0]["id"]
        except (KeyError, IndexError, ValueError, TypeError) as error:
            raise WhatsappUnavailableError("whatsapp_malformed_response") from error
        return WhatsappSendResult(wa_message_id=wa_message_id)

    def send_text(
        self, phone_number_id: str, access_token: str, to: str, body: str
    ) -> WhatsappSendResult:
        if not phone_number_id or not access_token:
            raise WhatsappUnavailableError("whatsapp_not_configured")
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body},
        }
        return self._post(phone_number_id, access_token, payload)

    def send_template(
        self,
        phone_number_id: str,
        access_token: str,
        to: str,
        template_name: str,
        language_code: str,
        parameters: list[str] | None = None,
    ) -> WhatsappSendResult:
        if not phone_number_id or not access_token:
            raise WhatsappUnavailableError("whatsapp_not_configured")
        components = (
            [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": value} for value in parameters],
                }
            ]
            if parameters
            else []
        )
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": components,
            },
        }
        return self._post(phone_number_id, access_token, payload)


whatsapp_client = WhatsappClient()
