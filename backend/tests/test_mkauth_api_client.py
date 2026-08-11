import base64
import asyncio
import json
import time

import pytest
from types import SimpleNamespace

from app.integrations.mkauth.api_client import MkAuthApiClient
from app.api.routes import integrations


def _jwt(claims: dict) -> str:
    def encode(value: dict) -> str:
        raw = json.dumps(value).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    return f"{encode({'alg': 'none'})}.{encode(claims)}.signature"


def test_accepts_current_jwt() -> None:
    now = int(time.time())
    MkAuthApiClient._validate_token(_jwt({"iat": now, "exp": now + 600}))


def test_routeros_diagnostic_is_normalized_and_read_only(monkeypatch) -> None:
    settings = SimpleNamespace(
        routeros_mode="real",
        routeros_host="192.168.20.1",
        routeros_port=8728,
        routeros_username="app_api",
        routeros_password="secret",
        mkauth_base_url="https://172.31.255.2",
    )

    class StubClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def diagnose(self) -> dict:
            return {
                "router": {"board": "hEX", "version": "7.23.2"},
                "ppp_aaa": {"use_radius": True, "accounting": True},
                "radius": [{"address": "172.31.255.2", "services": "ppp", "disabled": False}],
                "sessions": [{"username": "cliente.pppoe"}],
            }

    monkeypatch.setattr(integrations, "get_settings", lambda: settings)
    monkeypatch.setattr(integrations, "RouterOsReadOnlyClient", StubClient)
    response = asyncio.run(integrations.diagnose_routeros())

    assert response["status"] == "connected"
    assert response["read_only"] is True
    assert response["sessions"][0]["username"] == "cliente.pppoe"
    assert all(check["status"] == "ok" for check in response["checks"])
    assert "routeros_password" not in response


def test_rejects_non_jwt_response() -> None:
    with pytest.raises(ValueError, match="mkauth_token_response_is_not_jwt"):
        MkAuthApiClient._validate_token("Nao autorizado")


def test_reports_expired_jwt_as_clock_problem() -> None:
    now = int(time.time())
    with pytest.raises(ValueError, match="mkauth_token_already_expired"):
        MkAuthApiClient._validate_token(_jwt({"iat": now - 1200, "exp": now - 600}))


def test_accepts_jwt_payload_with_utf8_bom() -> None:
    now = int(time.time())
    token = "\ufeff" + _jwt({"iat": now, "exp": now + 600})
    MkAuthApiClient._validate_token(token.lstrip("\ufeff"))


def test_plans_endpoint_normalizes_read_only_data(monkeypatch) -> None:
    settings = SimpleNamespace(
        mkauth_mode="real",
        mkauth_base_url="https://mkauth.test",
        mkauth_client_id="client",
        mkauth_client_secret="secret",
        mkauth_verify_ssl=False,
        mkauth_allow_http=False,
        app_env="development",
    )

    class StubClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def list_plans(self) -> list[dict]:
            return [
                {
                    "uuid": "plan-1",
                    "nome": "120M",
                    "valor": "55.00",
                    "veldown": "125M",
                    "velup": "125M",
                }
            ]

    monkeypatch.setattr(integrations, "get_settings", lambda: settings)
    monkeypatch.setattr(integrations, "MkAuthApiClient", StubClient)
    response = asyncio.run(integrations.list_mkauth_plans())

    assert response["status"] == "connected"
    assert response["read_only"] is True
    assert response["count"] == 1
    assert response["plans"][0]["name"] == "120M"


def test_clients_endpoint_excludes_sensitive_fields(monkeypatch) -> None:
    settings = SimpleNamespace(
        mkauth_mode="real",
        mkauth_base_url="https://mkauth.test",
        mkauth_client_id="client",
        mkauth_client_secret="secret",
        mkauth_verify_ssl=False,
        mkauth_allow_http=False,
        app_env="development",
    )

    class StubClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def list_clients(self) -> list[dict]:
            return [
                {
                    "uuid": "customer-1",
                    "nome": "Cliente Bancada",
                    "login": "cliente.pppoe",
                    "senha": "must-not-leak",
                    "cpf_cnpj": "00000000000",
                    "tipo": "pppoe",
                    "cli_ativado": "s",
                    "status_corte": "bloq",
                    "cidade": "Salvador",
                    "estado": "BA",
                    "endereco": "Rua da Bancada",
                    "numero": "20",
                    "coordenadas": "-12.9,-38.5",
                }
            ]

    monkeypatch.setattr(integrations, "get_settings", lambda: settings)
    monkeypatch.setattr(integrations, "MkAuthApiClient", StubClient)
    response = asyncio.run(integrations.list_mkauth_clients())

    assert response["count"] == 1
    assert response["clients"][0]["login"] == "cliente.pppoe"
    assert response["clients"][0]["active"] is True
    assert response["clients"][0]["blocked"] is True
    assert response["clients"][0]["address"] == "Rua da Bancada, 20, Salvador, BA"
    assert "senha" not in response["clients"][0]
    assert "cpf_cnpj" not in response["clients"][0]


def test_clients_endpoint_marks_inactive_clients(monkeypatch) -> None:
    settings = SimpleNamespace(
        mkauth_mode="real",
        mkauth_base_url="https://mkauth.test",
        mkauth_client_id="client",
        mkauth_client_secret="secret",
        mkauth_verify_ssl=False,
        mkauth_allow_http=False,
        app_env="development",
    )

    class StubClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def list_clients(self) -> list[dict]:
            return [{"uuid": "inactive-1", "nome": "Desativado", "login": "off", "cli_ativado": "n"}]

    monkeypatch.setattr(integrations, "get_settings", lambda: settings)
    monkeypatch.setattr(integrations, "MkAuthApiClient", StubClient)
    response = asyncio.run(integrations.list_mkauth_clients())

    assert response["clients"][0]["active"] is False


def test_client_details_endpoint_excludes_sensitive_fields(monkeypatch) -> None:
    settings = SimpleNamespace(
        mkauth_mode="real",
        mkauth_base_url="https://mkauth.test",
        mkauth_client_id="client",
        mkauth_client_secret="secret",
        mkauth_verify_ssl=False,
        mkauth_allow_http=False,
        app_env="development",
    )

    class StubClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def get_client_details(self, login: str) -> dict:
            assert login == "cliente.pppoe"
            return {
                "nome": "Cliente Bancada",
                "login": login,
                "senha": "must-not-leak",
                "cpf_cnpj": "00000000000",
                "email": "must-not-leak@example.test",
                "tipo": "pppoe",
                "plano": "120M",
                "cli_ativado": "s",
                "bloqueado": "n",
                "ip": "10.0.0.10",
                "mac": "00:11:22:33:44:55",
            }

    monkeypatch.setattr(integrations, "get_settings", lambda: settings)
    monkeypatch.setattr(integrations, "MkAuthApiClient", StubClient)
    response = asyncio.run(integrations.get_mkauth_client_details("cliente.pppoe"))

    assert response["status"] == "connected"
    assert response["read_only"] is True
    assert response["client"]["plan"] == "120M"
    assert response["client"]["ip"] == "10.0.0.10"
    assert "senha" not in response["client"]
    assert "cpf_cnpj" not in response["client"]
    assert "email" not in response["client"]


def test_additional_clients_endpoint_normalizes_safe_fields(monkeypatch) -> None:
    settings = SimpleNamespace(
        mkauth_mode="real",
        mkauth_base_url="https://mkauth.test",
        mkauth_client_id="client",
        mkauth_client_secret="secret",
        mkauth_verify_ssl=False,
        mkauth_allow_http=False,
        app_env="development",
    )

    class StubClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def list_additional_clients(self) -> list[dict]:
            return [{
                "uuid": "additional-1",
                "nome": "Ponto adicional",
                "login": "cliente.principal",
                "usuario": "cliente.adicional",
                "plano": "120M",
                "cli_ativado": "s",
                "senha": "must-not-leak",
            }]

    monkeypatch.setattr(integrations, "get_settings", lambda: settings)
    monkeypatch.setattr(integrations, "MkAuthApiClient", StubClient)
    response = asyncio.run(integrations.list_mkauth_additional_clients())

    assert response["status"] == "connected"
    assert response["count"] == 1
    assert response["additional_clients"][0]["login"] == "cliente.adicional"
    assert response["additional_clients"][0]["main_login"] == "cliente.principal"
    assert "senha" not in response["additional_clients"][0]


def test_titles_endpoint_excludes_payment_secrets(monkeypatch) -> None:
    settings = SimpleNamespace(
        mkauth_mode="real",
        mkauth_base_url="https://mkauth.test",
        mkauth_client_id="client",
        mkauth_client_secret="secret",
        mkauth_verify_ssl=False,
        mkauth_allow_http=False,
        app_env="development",
    )

    class StubClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def list_titles(self) -> list[dict]:
            return [{
                "uuid": "title-1",
                "login": "cliente.pppoe",
                "titulo": "101",
                "status": "aberto",
                "tipo": "mensalidade",
                "valor": "120.00",
                "datavenc": "2026-08-01 00:00:00",
                "linhadig": "must-not-leak",
                "cpf_cnpj": "00000000000",
                "qrcode": "must-not-leak",
            }]

        async def list_clients(self) -> list[dict]:
            return [{"login": "cliente.pppoe", "cli_ativado": "s"}]

    monkeypatch.setattr(integrations, "get_settings", lambda: settings)
    monkeypatch.setattr(integrations, "MkAuthApiClient", StubClient)
    response = asyncio.run(integrations.list_mkauth_titles())

    assert response["status"] == "connected"
    assert response["titles"][0]["status"] == "aberto"
    assert response["titles"][0]["amount"] == "120.00"
    assert "linhadig" not in response["titles"][0]
    assert "cpf_cnpj" not in response["titles"][0]
    assert "qrcode" not in response["titles"][0]


def test_titles_for_login_use_open_endpoint_and_hide_inactive_clients(monkeypatch) -> None:
    settings = SimpleNamespace(
        mkauth_mode="real",
        mkauth_base_url="https://mkauth.test",
        mkauth_client_id="client",
        mkauth_client_secret="secret",
        mkauth_verify_ssl=False,
        mkauth_allow_http=False,
        app_env="development",
    )
    requested = []

    class StubClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def list_clients(self) -> list[dict]:
            return [
                {"login": "ativo", "cli_ativado": "s"},
                {"login": "desativado", "cli_ativado": "n"},
            ]

        async def list_payable_titles(self, login: str) -> list[dict]:
            requested.append(login)
            return [
                {"uuid": "title-open-1", "login": login, "status": "aberto", "valor": "54.99", "datavenc": "2026-10-05"},
                {"uuid": "title-overdue-1", "login": login, "status": "vencido", "valor": "54.99", "datavenc": "2026-08-05"},
            ]

    monkeypatch.setattr(integrations, "get_settings", lambda: settings)
    monkeypatch.setattr(integrations, "MkAuthApiClient", StubClient)

    active = asyncio.run(integrations.list_mkauth_titles("ativo"))
    inactive = asyncio.run(integrations.list_mkauth_titles("desativado"))

    assert active["count"] == 2
    assert [title["status"] for title in active["titles"]] == ["vencido", "aberto"]
    assert inactive["count"] == 0
    assert requested == ["ativo"]


def test_missing_title_situation_is_treated_as_empty(monkeypatch) -> None:
    responses = iter([
        {"mensagem": "Registro não encontrado"},
        {"Total": 0, "titulos": None},
    ])

    class Response:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return next(responses)

    class HttpClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args) -> None:
            pass

        async def get(self, path: str) -> Response:
            return Response()

    async def token(self) -> str:
        return "token"

    monkeypatch.setattr("app.integrations.mkauth.api_client.httpx.AsyncClient", lambda **kwargs: HttpClient())
    monkeypatch.setattr(MkAuthApiClient, "_token", token)
    client = MkAuthApiClient("https://mkauth.test", "client", "secret", False, False)

    assert asyncio.run(client.list_titles_by_situation("cliente", "aberto")) == []
    assert asyncio.run(client.list_titles_by_situation("cliente", "vencido")) == []


def test_trust_unlock_requires_blocked_client_and_records_audit(monkeypatch) -> None:
    settings = SimpleNamespace(
        mkauth_mode="real",
        mkauth_writes_enabled=True,
        mkauth_base_url="https://mkauth.test",
        mkauth_client_id="client",
        mkauth_client_secret="secret",
        mkauth_verify_ssl=False,
        mkauth_allow_http=False,
        app_env="development",
    )
    writes = []
    reads = 0

    class StubClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def get_client_details(self, login: str) -> dict:
            nonlocal reads
            reads += 1
            return {
                "login": login,
                "bloqueado": "-",
                "status_corte": "bloq",
                "observacao": "nao" if reads == 1 else "sim",
            }

        async def set_client_trust_observation(self, client_uuid: str, enabled: bool, expires_at=None) -> dict:
            writes.append((client_uuid, enabled, expires_at is not None))
            return {"status": "sucesso"}

    class StubStore:
        def create(self, client_uuid: str, login: str, reason: str) -> dict:
            return {"client_uuid": client_uuid, "login": login, "reason": reason, "status": "active"}

    monkeypatch.setattr(integrations, "get_settings", lambda: settings)
    monkeypatch.setattr(integrations, "MkAuthApiClient", StubClient)
    monkeypatch.setattr(integrations, "_trust_unlock_store", lambda: StubStore())
    request = integrations.TrustUnlockRequest(
        client_uuid="customer-uuid-1",
        login="cliente.pppoe",
        reason="Solicitação do cliente",
        confirmed=True,
    )
    response = asyncio.run(integrations.create_mkauth_trust_unlock(request))

    assert response["status"] == "unlocked"
    assert response["valid_hours"] == 48
    assert writes == [("customer-uuid-1", True, True)]


def test_expired_trust_unlock_is_reblocked_and_marked_expired(monkeypatch) -> None:
    settings = SimpleNamespace(
        mkauth_mode="real",
        mkauth_writes_enabled=True,
        mkauth_base_url="https://mkauth.test",
        mkauth_client_id="client",
        mkauth_client_secret="secret",
        mkauth_verify_ssl=False,
        mkauth_allow_http=False,
        app_env="development",
    )
    writes = []
    marked = []

    class StubClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def set_client_trust_observation(self, client_uuid: str, enabled: bool) -> dict:
            writes.append((client_uuid, enabled))
            return {"status": "sucesso"}

    class StubStore:
        def list_expired_active(self) -> list[dict]:
            return [{"id": "unlock-1", "client_uuid": "customer-uuid-1"}]

        def mark_expired(self, record_id: str) -> None:
            marked.append(record_id)

    monkeypatch.setattr(integrations, "get_settings", lambda: settings)
    monkeypatch.setattr(integrations, "MkAuthApiClient", StubClient)
    monkeypatch.setattr(integrations, "_trust_unlock_store", lambda: StubStore())
    completed = asyncio.run(integrations.reconcile_expired_trust_unlocks())

    assert completed == 1
    assert writes == [("customer-uuid-1", False)]
    assert marked == ["unlock-1"]


def test_active_trust_unlock_can_be_cancelled(monkeypatch) -> None:
    settings = SimpleNamespace(
        mkauth_mode="real",
        mkauth_writes_enabled=True,
        mkauth_base_url="https://mkauth.test",
        mkauth_client_id="client",
        mkauth_client_secret="secret",
        mkauth_verify_ssl=False,
        mkauth_allow_http=False,
        app_env="development",
    )
    writes = []
    cancelled = []

    class StubClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def set_client_trust_observation(self, client_uuid: str, enabled: bool) -> dict:
            writes.append((client_uuid, enabled))
            return {"status": "sucesso"}

        async def get_client_details(self, login: str) -> dict:
            return {"login": login, "observacao": "nao"}

    class StubStore:
        def get_active(self, record_id: str) -> dict | None:
            return {
                "id": record_id,
                "client_uuid": "customer-uuid-1",
                "login": "cliente.pppoe",
            }

        def mark_cancelled(self, record_id: str) -> None:
            cancelled.append(record_id)

    monkeypatch.setattr(integrations, "get_settings", lambda: settings)
    monkeypatch.setattr(integrations, "MkAuthApiClient", StubClient)
    monkeypatch.setattr(integrations, "_trust_unlock_store", lambda: StubStore())
    request = integrations.TrustUnlockCancelRequest(confirmed=True)
    response = asyncio.run(integrations.cancel_mkauth_trust_unlock("unlock-1", request))

    assert response["status"] == "cancelled"
    assert writes == [("customer-uuid-1", False)]
    assert cancelled == ["unlock-1"]


def test_pix_simulation_validates_real_title_without_writing_to_mkauth(monkeypatch) -> None:
    settings = SimpleNamespace(
        mkauth_mode="real",
        mkauth_base_url="https://mkauth.test",
        mkauth_client_id="client",
        mkauth_client_secret="secret",
        mkauth_verify_ssl=False,
        mkauth_allow_http=False,
        app_env="development",
    )
    saved = []

    class StubClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def list_titles(self) -> list[dict]:
            return [{
                "uuid": "title-uuid-1234",
                "login": "cliente.pppoe",
                "titulo": "101",
                "valor": "120.00",
                "status": "vencido",
            }]

    class StubStore:
        def create(self, title_uuid: str, title_number: str, login: str, amount: str) -> dict:
            saved.append((title_uuid, title_number, login, amount))
            return {"id": "pix-1", "status": "simulated"}

    monkeypatch.setattr(integrations, "get_settings", lambda: settings)
    monkeypatch.setattr(integrations, "MkAuthApiClient", StubClient)
    monkeypatch.setattr(integrations, "_pix_simulation_store", lambda: StubStore())
    request = integrations.PixSimulationRequest(
        title_uuid="title-uuid-1234",
        login="cliente.pppoe",
        confirmed=True,
    )
    response = asyncio.run(integrations.create_mkauth_pix_simulation(request))

    assert response["status"] == "simulated"
    assert response["write_performed"] is False
    assert saved == [("title-uuid-1234", "101", "cliente.pppoe", "120.00")]


def test_real_pix_payment_requires_confirmation_and_verifies_mkauth(monkeypatch) -> None:
    settings = SimpleNamespace(
        mkauth_mode="real",
        mkauth_writes_enabled=True,
        mkauth_base_url="https://mkauth.test",
        mkauth_client_id="client",
        mkauth_client_secret="secret",
        mkauth_verify_ssl=False,
        mkauth_allow_http=False,
        app_env="development",
    )
    reads = 0
    received = []
    saved = []

    class StubClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def get_title(self, title_uuid: str) -> dict:
            nonlocal reads
            reads += 1
            return {
                "uuid": title_uuid,
                "id": "101",
                "login": "cliente.pppoe",
                "valor": "120.00",
                "status": "vencido" if reads == 1 else "pago",
                "datapag": None if reads == 1 else "2026-08-06 12:00:00",
            }

        async def receive_title(self, title_uuid: str, amount: str, collector: str, payment_method: str) -> dict:
            received.append((title_uuid, amount, collector, payment_method))
            return {"status": "sucesso"}

        async def list_payable_titles(self, login: str) -> list[dict]:
            return [{"uuid": "another-title", "login": login, "status": "vencido"}]

    class StubStore:
        def has_real_payment(self, title_uuid: str) -> bool:
            return False

        def create(self, title_uuid: str, title_number: str, login: str, amount: str, status: str = "simulated") -> dict:
            saved.append((title_uuid, title_number, login, amount, status))
            return {"id": "pix-real-1", "status": status}

    monkeypatch.setattr(integrations, "get_settings", lambda: settings)
    monkeypatch.setattr(integrations, "MkAuthApiClient", StubClient)
    monkeypatch.setattr(integrations, "_pix_simulation_store", lambda: StubStore())
    request = integrations.PixRealPaymentRequest(
        title_uuid="title-uuid-1234",
        login="cliente.pppoe",
        confirmation_text="BAIXAR",
        confirmed=True,
    )
    fake_session = {
        "organization": {"id": "g7-networks"},
        "user": {"id": "admin-1", "name": "Admin", "username": "admin", "role": "owner"},
    }
    response = asyncio.run(
        integrations.create_mkauth_pix_payment(request, session=fake_session)
    )

    assert response["status"] == "paid"
    assert response["write_performed"] is True
    assert response["access_resolution"] == "pending_titles_remain"
    assert response["remaining_titles"] == 1
    assert response["notification"]["status"] == "simulated_sent"
    assert response["notification"]["template"] == "payment_confirmed_pending_titles"
    assert received == [("title-uuid-1234", "120.00", "API", "pix")]
    assert saved == [("title-uuid-1234", "101", "cliente.pppoe", "120.00", "real_paid")]


def test_tickets_endpoint_normalizes_read_only_data(monkeypatch) -> None:
    settings = SimpleNamespace(
        mkauth_mode="real",
        mkauth_base_url="https://mkauth.test",
        mkauth_client_id="client",
        mkauth_client_secret="secret",
        mkauth_verify_ssl=False,
        mkauth_allow_http=False,
        app_env="development",
    )

    class StubClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def list_support_tickets(self) -> list[dict]:
            return [
                {
                    "uuid": "ticket-uuid-1",
                    "chamado": "06082612000001",
                    "abertura": "2026-08-06 12:00:00",
                    "login": "cliente.pppoe",
                    "prioridade": "alta",
                    "status": "aberto",
                    "assunto": "Conexão",
                },
                {
                    "uuid": "ticket-uuid-closed",
                    "chamado": "06082612000002",
                    "abertura": "2026-08-06 12:10:00",
                    "login": "cliente.pppoe",
                    "prioridade": "normal",
                    "status": "fechado",
                    "assunto": "Financeiro",
                },
            ]

    monkeypatch.setattr(integrations, "get_settings", lambda: settings)
    monkeypatch.setattr(integrations, "MkAuthApiClient", StubClient)
    response = asyncio.run(integrations.list_mkauth_tickets())

    assert response["count"] == 1
    assert response["tickets"][0]["number"] == "06082612000001"
    assert response["tickets"][0]["status"] == "aberto"


def test_empty_ticket_message_is_treated_as_empty_collection() -> None:
    message = "Nenhum registro encontrado"
    normalized = message.casefold().replace("ã", "a").replace("á", "a").replace("é", "e")
    assert any(marker in normalized for marker in ("nenhum", "nao encontrado", "sem registro"))
