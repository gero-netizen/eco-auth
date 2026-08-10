import base64
import json
import re
import time
from datetime import datetime
from typing import Any
from urllib.parse import quote

import httpx


class MkAuthApiClient:
    """Read-only MK-AUTH API client. Mutating endpoints are intentionally absent."""

    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        verify_ssl: bool = True,
        allow_http: bool = False,
    ) -> None:
        if not base_url.lower().startswith("https://") and not (
            allow_http and base_url.lower().startswith("http://")
        ):
            raise ValueError("mkauth_https_required")
        if not client_id or not client_secret:
            raise ValueError("mkauth_credentials_not_configured")
        self._base_url = base_url.rstrip("/")
        self._client_id = client_id
        self._client_secret = client_secret
        self._verify_ssl = verify_ssl
        self._allow_http = allow_http

    async def _token(self) -> str:
        async with httpx.AsyncClient(
            base_url=self._base_url,
            verify=self._verify_ssl,
            timeout=10,
        ) as client:
            response = await client.get(
                "/api/",
                auth=(self._client_id, self._client_secret),
            )
            response.raise_for_status()
            raw = response.text.strip()
            try:
                payload: Any = response.json()
            except ValueError:
                payload = raw
        if isinstance(payload, str):
            token = payload
        elif isinstance(payload, dict):
            if "error" in payload or payload.get("status") in {"error", "erro"}:
                detail = (
                    payload.get("error")
                    or payload.get("message")
                    or payload.get("mensagem")
                    or "unknown_error"
                )
                raise ValueError(f"mkauth_token_error:{str(detail)[:200]}")
            token = (
                payload.get("token")
                or payload.get("access_token")
                or payload.get("jwt")
            )
        else:
            token = None
        if not isinstance(token, str) or not token:
            raise ValueError("mkauth_token_not_found")
        token = token.strip().lstrip("\ufeff").strip().strip('"')
        if token.lower().startswith("bearer "):
            token = token[7:].strip()
        if not token or token.startswith("<") or "<html" in token.lower():
            raise ValueError("mkauth_token_endpoint_returned_html")
        if token.count(".") != 2:
            embedded_jwt = re.search(
                r"(?<![A-Za-z0-9_-])"
                r"([A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)"
                r"(?![A-Za-z0-9_-])",
                token,
            )
            if embedded_jwt:
                token = embedded_jwt.group(1)
            else:
                normalized = token.casefold()
                if "https" in normalized:
                    raise ValueError("mkauth_token_requires_https")
                if "autoriz" in normalized or "credencia" in normalized:
                    raise ValueError("mkauth_token_credentials_rejected")
        self._validate_token(token)
        return token

    @staticmethod
    def _validate_token(token: str) -> None:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("mkauth_token_response_is_not_jwt")
        try:
            encoded_payload = parts[1] + "=" * (-len(parts[1]) % 4)
            claims = json.loads(base64.urlsafe_b64decode(encoded_payload))
        except (ValueError, TypeError, json.JSONDecodeError):
            raise ValueError("mkauth_token_payload_invalid") from None

        now = int(time.time())
        issued_at = claims.get("iat")
        expires_at = claims.get("exp")
        if isinstance(expires_at, (int, float)) and expires_at <= now:
            raise ValueError("mkauth_token_already_expired_check_server_clock")
        if isinstance(issued_at, (int, float)) and issued_at > now + 300:
            raise ValueError("mkauth_token_issued_in_future_check_clocks")

    async def list_plans(self) -> list[dict[str, Any]]:
        token = await self._token()
        return await self.list_plans_with_token(token)

    async def list_clients(self) -> list[dict[str, Any]]:
        token = await self._token()
        async with httpx.AsyncClient(
            base_url=self._base_url,
            verify=self._verify_ssl,
            timeout=10,
            headers={"Authorization": f"Bearer {token}"},
        ) as client:
            response = await client.get("/api/cliente/listar/pagina=1&limite=500")
            response.raise_for_status()
            payload = response.json()
        if isinstance(payload, dict) and "error" in payload:
            raise ValueError("mkauth_clients_api_error")
        clients = payload.get("clientes") if isinstance(payload, dict) else None
        if not isinstance(clients, list):
            raise ValueError("mkauth_invalid_clients_response")
        return clients

    async def get_client_details(self, login: str) -> dict[str, Any]:
        token = await self._token()
        safe_login = quote(login, safe="")
        async with httpx.AsyncClient(
            base_url=self._base_url,
            verify=self._verify_ssl,
            timeout=10,
            headers={"Authorization": f"Bearer {token}"},
        ) as client:
            response = await client.get(f"/api/cliente/show/{safe_login}")
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("mkauth_invalid_client_details_response")
        if "error" in payload:
            raise ValueError("mkauth_client_details_api_error")
        details = payload.get("cliente") or payload.get("dados") or payload
        if not isinstance(details, dict):
            raise ValueError("mkauth_invalid_client_details_response")
        return details

    async def list_additional_clients(self) -> list[dict[str, Any]]:
        token = await self._token()
        paths = (
            "/api/adicional/listar/pagina=1&limite=500",
            "/api/adicionais/listar/pagina=1&limite=500",
            "/api/cliente/adicional/listar/pagina=1&limite=500",
        )
        async with httpx.AsyncClient(
            base_url=self._base_url,
            verify=self._verify_ssl,
            timeout=10,
            headers={"Authorization": f"Bearer {token}"},
        ) as client:
            for path in paths:
                response = await client.get(path)
                if response.status_code in {404, 405}:
                    continue
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    continue
                collection = (
                    payload.get("adicionais")
                    or payload.get("adicional")
                    or payload.get("clientes")
                    or payload.get("dados")
                )
                if isinstance(collection, list):
                    return [item for item in collection if isinstance(item, dict)]
                message = str(payload.get("mensagem") or payload.get("message") or "")
                if "nenhum" in message.casefold():
                    return []
        raise ValueError("mkauth_additional_clients_endpoint_not_found")

    async def list_titles(self) -> list[dict[str, Any]]:
        token = await self._token()
        async with httpx.AsyncClient(
            base_url=self._base_url,
            verify=self._verify_ssl,
            timeout=10,
            headers={"Authorization": f"Bearer {token}"},
        ) as client:
            response = await client.get("/api/titulo/listar/pagina=1&limite=500")
            response.raise_for_status()
            payload = response.json()
        titles = payload.get("titulos") if isinstance(payload, dict) else None
        if not isinstance(titles, list):
            message = str(payload.get("mensagem") or "") if isinstance(payload, dict) else ""
            if "nenhum" in message.casefold():
                return []
            raise ValueError("mkauth_invalid_titles_response")
        return [item for item in titles if isinstance(item, dict)]

    async def list_titles_by_situation(self, login: str, situation: str) -> list[dict[str, Any]]:
        if situation not in {"aberto", "vencido"}:
            raise ValueError("mkauth_invalid_title_situation")
        token = await self._token()
        safe_login = quote(login, safe="")
        async with httpx.AsyncClient(
            base_url=self._base_url,
            verify=self._verify_ssl,
            timeout=10,
            headers={"Authorization": f"Bearer {token}"},
        ) as client:
            response = await client.get(f"/api/titulo/{situation}/{safe_login}")
            response.raise_for_status()
            payload = response.json()
        titles = payload.get("titulos") if isinstance(payload, dict) else None
        if isinstance(titles, list):
            return [item for item in titles if isinstance(item, dict)]
        message = str(payload.get("mensagem") or "") if isinstance(payload, dict) else ""
        empty_messages = {"registro não encontrado", "registro nao encontrado"}
        if (
            "nenhum" in message.casefold()
            or message.strip().casefold() in empty_messages
            or payload.get("Total") == 0
        ):
            return []
        raise ValueError(f"mkauth_invalid_{situation}_titles_response")

    async def list_payable_titles(self, login: str) -> list[dict[str, Any]]:
        open_titles = await self.list_titles_by_situation(login, "aberto")
        overdue_titles = await self.list_titles_by_situation(login, "vencido")
        unique: dict[str, dict[str, Any]] = {}
        for item in [*overdue_titles, *open_titles]:
            key = str(item.get("uuid") or item.get("titulo") or item.get("numero") or "")
            if key:
                unique[key] = item
        return list(unique.values())

    async def get_title(self, title_uuid: str) -> dict[str, Any]:
        token = await self._token()
        safe_uuid = quote(title_uuid, safe="")
        async with httpx.AsyncClient(
            base_url=self._base_url,
            verify=self._verify_ssl,
            timeout=10,
            headers={"Authorization": f"Bearer {token}"},
        ) as client:
            response = await client.get(f"/api/titulo/show/{safe_uuid}")
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict) or "error" in payload:
            raise ValueError("mkauth_invalid_title_details_response")
        return payload.get("titulo") or payload.get("dados") or payload

    async def receive_title(
        self,
        title_uuid: str,
        amount: str,
        collector: str = "API",
        payment_method: str = "pix",
    ) -> dict[str, Any]:
        token = await self._token()
        async with httpx.AsyncClient(
            base_url=self._base_url,
            verify=self._verify_ssl,
            timeout=10,
            headers={"Authorization": f"Bearer {token}"},
        ) as client:
            response = await client.put(
                "/api/titulo/receber",
                json={
                    "coletor": collector,
                    "valor": amount,
                    "forma": payment_method,
                    "uuid": title_uuid,
                },
            )
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("mkauth_invalid_title_receive_response")
        status = str(payload.get("status") or "").strip().casefold()
        if status in {"erro", "error", "falha", "failed"} or payload.get("error"):
            raise ValueError(str(payload.get("mensagem") or payload.get("message") or "mkauth_title_receive_failed"))
        return payload

    async def set_client_blocked(self, client_uuid: str, blocked: bool) -> dict[str, Any]:
        return await self.update_client(
            client_uuid,
            {"bloqueado": "sim" if blocked else "nao"},
        )

    async def set_client_trust_observation(
        self,
        client_uuid: str,
        enabled: bool,
        expires_at: datetime | None = None,
    ) -> dict[str, Any]:
        fields: dict[str, Any] = {"observacao": "sim" if enabled else "nao"}
        if expires_at is not None:
            fields["data_desbloq"] = expires_at.strftime("%Y-%m-%d %H:%M:%S")
        return await self.update_client(client_uuid, fields)

    async def update_client(
        self,
        client_uuid: str,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        token = await self._token()
        async with httpx.AsyncClient(
            base_url=self._base_url,
            verify=self._verify_ssl,
            timeout=10,
            headers={"Authorization": f"Bearer {token}"},
        ) as client:
            response = await client.put(
                "/api/cliente/editar",
                json={"uuid": client_uuid, **fields},
            )
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("mkauth_invalid_client_update_response")
        status = str(payload.get("status") or "").casefold()
        if status in {"erro", "error", "falha", "failed"} or payload.get("error"):
            raise ValueError(str(payload.get("mensagem") or payload.get("message") or "mkauth_client_update_failed"))
        return payload

    async def list_support_tickets(self) -> list[dict[str, Any]]:
        token = await self._token()
        async with httpx.AsyncClient(
            base_url=self._base_url,
            verify=self._verify_ssl,
            timeout=10,
            headers={"Authorization": f"Bearer {token}"},
        ) as client:
            response = await client.get("/api/chamado/listar/pagina=1&limite=500")
            response.raise_for_status()
            payload = response.json()
        if isinstance(payload, dict) and "error" in payload:
            error_payload = payload["error"]
            if isinstance(error_payload, dict):
                detail = (
                    error_payload.get("text")
                    or error_payload.get("message")
                    or error_payload.get("mensagem")
                )
            else:
                detail = error_payload
            safe_detail = str(detail or "unknown_error").replace("\n", " ")[:200]
            raise ValueError(f"mkauth_tickets_api_error:{safe_detail}")
        tickets = payload.get("chamados") if isinstance(payload, dict) else None
        if tickets is None and isinstance(payload, dict) and "mensagem" in payload:
            message = str(payload.get("mensagem") or "").replace("\n", " ")[:200]
            normalized_message = (
                message.casefold()
                .replace("ã", "a")
                .replace("á", "a")
                .replace("é", "e")
            )
            if any(
                marker in normalized_message
                for marker in ("nenhum", "nao encontrado", "sem registro")
            ):
                return []
            status = str(payload.get("status") or "unknown")[:40]
            raise ValueError(f"mkauth_tickets_api_response:{status}:{message}")
        if not isinstance(tickets, list):
            keys = (
                ",".join(sorted(str(key) for key in payload.keys()))
                if isinstance(payload, dict)
                else type(payload).__name__
            )
            raise ValueError(f"mkauth_invalid_tickets_response:{keys}")
        return tickets

    async def resolve_support_ticket_number(self, reference: str) -> str:
        tickets = await self.list_support_tickets()
        for ticket in tickets:
            if str(ticket.get("uuid") or "") == reference or str(
                ticket.get("chamado") or ""
            ) == reference:
                number = str(ticket.get("chamado") or "").strip()
                if number:
                    return number
        raise ValueError("mkauth_ticket_reference_not_found")

    async def close_support_ticket(self, number: str, reason: str) -> dict[str, Any]:
        token = await self._token()
        async with httpx.AsyncClient(
            base_url=self._base_url,
            verify=self._verify_ssl,
            timeout=10,
            headers={"Authorization": f"Bearer {token}"},
        ) as client:
            response = await client.put(
                "/api/chamado/fechar",
                json={"chamado": number, "motivo": reason},
            )
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("mkauth_invalid_ticket_close_response")
        status = str(payload.get("status") or "").casefold()
        if status not in {"sucesso", "success"}:
            message = str(payload.get("mensagem") or "unknown_error")[:200]
            raise ValueError(f"mkauth_ticket_close_failed:{message}")
        return payload

    async def diagnose(self) -> dict[str, Any]:
        token = await self._token()
        plans = await self.list_plans_with_token(token)
        return {
            "authentication": "ok",
            "plans_endpoint": "ok",
            "plans_path": "/api/plano/listar/pagina=1&limite=500",
            "plans_found": len(plans),
        }

    async def list_plans_with_token(self, token: str) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(
            base_url=self._base_url,
            verify=self._verify_ssl,
            timeout=10,
            headers={"Authorization": f"Bearer {token}"},
        ) as client:
            response = await client.get("/api/plano/listar/pagina=1&limite=500")
            response.raise_for_status()
            payload = response.json()
        if isinstance(payload, list):
            plans = payload
        elif isinstance(payload, dict):
            if "error" in payload:
                error_payload = payload["error"]
                if isinstance(error_payload, dict):
                    detail = (
                        error_payload.get("text")
                        or error_payload.get("message")
                        or error_payload.get("mensagem")
                    )
                else:
                    detail = error_payload
                safe_detail = str(detail or "unknown_error").replace("\n", " ")[:200]
                raise ValueError(f"mkauth_api_error:{safe_detail}")
            plans = payload.get("planos")
            if plans is None:
                for key in ("dados", "data", "items", "results"):
                    candidate = payload.get(key)
                    if isinstance(candidate, list):
                        plans = candidate
                        break
            if plans is None:
                raise ValueError(
                    "mkauth_plans_collection_not_found:"
                    + ",".join(sorted(str(key) for key in payload.keys()))
                )
        else:
            plans = None
        if not isinstance(plans, list):
            raise ValueError("mkauth_invalid_plans_response")
        return plans
