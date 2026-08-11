from dataclasses import dataclass

import httpx

from app.core.config import get_settings

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"


class AiUnavailableError(Exception):
    """Raised for any condition where the real AI call could not complete
    (timeout, network failure, bad credentials, provider error). Callers
    must treat this as a signal to fall back to the local knowledge-base
    matching, never as something to surface raw to the customer."""


@dataclass(frozen=True)
class AiCompletion:
    text: str
    input_tokens: int
    output_tokens: int
    model: str


class AiClient:
    """Thin wrapper around the Anthropic Messages API. Stateless: every call
    takes its own API key and model, since each provider organization has
    its own configuration."""

    def __init__(self, timeout_seconds: float | None = None) -> None:
        self._timeout = timeout_seconds or get_settings().ai_request_timeout_seconds

    async def complete(
        self,
        api_key: str,
        model: str,
        system_instructions: str,
        user_message: str,
        max_tokens: int = 400,
    ) -> AiCompletion:
        if not api_key:
            raise AiUnavailableError("ai_not_configured")
        payload = self._build_payload(model, system_instructions, user_message, max_tokens)
        headers = self._build_headers(api_key)
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    ANTHROPIC_API_URL, json=payload, headers=headers
                )
        except httpx.TimeoutException as error:
            raise AiUnavailableError("ai_request_timeout") from error
        except httpx.HTTPError as error:
            raise AiUnavailableError("ai_network_error") from error
        return self._parse_response(response, model)

    def complete_sync(
        self,
        api_key: str,
        model: str,
        system_instructions: str,
        user_message: str,
        max_tokens: int = 400,
    ) -> AiCompletion:
        """Same as complete(), but blocking — for call sites that are not
        (yet) async, such as ticket creation on the portal."""
        if not api_key:
            raise AiUnavailableError("ai_not_configured")
        payload = self._build_payload(model, system_instructions, user_message, max_tokens)
        headers = self._build_headers(api_key)
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(ANTHROPIC_API_URL, json=payload, headers=headers)
        except httpx.TimeoutException as error:
            raise AiUnavailableError("ai_request_timeout") from error
        except httpx.HTTPError as error:
            raise AiUnavailableError("ai_network_error") from error
        return self._parse_response(response, model)

    @staticmethod
    def _build_payload(
        model: str, system_instructions: str, user_message: str, max_tokens: int
    ) -> dict:
        return {
            "model": model,
            "max_tokens": max_tokens,
            "system": system_instructions,
            "messages": [{"role": "user", "content": user_message}],
        }

    @staticmethod
    def _build_headers(api_key: str) -> dict:
        return {
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_API_VERSION,
            "content-type": "application/json",
        }

    @staticmethod
    def _parse_response(response: httpx.Response, model: str) -> AiCompletion:
        if response.status_code != 200:
            raise AiUnavailableError(f"ai_provider_error_{response.status_code}")
        try:
            data = response.json()
            text = "".join(
                block.get("text", "")
                for block in data.get("content", [])
                if block.get("type") == "text"
            )
            usage = data.get("usage", {})
            if not text:
                raise AiUnavailableError("ai_empty_response")
            return AiCompletion(
                text=text,
                input_tokens=int(usage.get("input_tokens", 0)),
                output_tokens=int(usage.get("output_tokens", 0)),
                model=model,
            )
        except (KeyError, ValueError, TypeError) as error:
            raise AiUnavailableError("ai_malformed_response") from error


ai_client = AiClient()
