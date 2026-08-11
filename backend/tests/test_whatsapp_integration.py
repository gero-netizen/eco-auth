import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from app.core.ai_support_store import ai_support_store
from app.core.organization_store import organization_store
from app.core.whatsapp_config_store import WhatsappConfigStore
from app.core.whatsapp_consent_store import WhatsappConsentStore
from app.core.whatsapp_contact_store import WhatsappContactStore
from app.core.whatsapp_message_store import WhatsappMessageStore
from app.core.whatsapp_orchestrator import send_whatsapp_message
from app.integrations.whatsapp.client import WhatsappSendResult, WhatsappUnavailableError
from app.main import app


def test_whatsapp_config_is_isolated_and_secrets_are_encrypted(tmp_path) -> None:
    db_path = tmp_path / "wa-config.db"
    store = WhatsappConfigStore(f"sqlite:///{db_path}")
    store.save(
        "provedor-um",
        enabled=True,
        phone_number_id="1234567890",
        business_account_id="999",
        verify_token="minha-palavra-secreta",
        access_token="EAAG-super-secret-token",
        app_secret="app-secret-value",
    )

    raw_bytes = db_path.read_bytes()
    assert b"EAAG-super-secret-token" not in raw_bytes
    assert b"app-secret-value" not in raw_bytes

    fetched = store.get("provedor-um")
    assert fetched.access_token == "EAAG-super-secret-token"
    assert fetched.app_secret == "app-secret-value"

    untouched = store.get("provedor-dois")
    assert untouched.enabled is False
    assert untouched.access_token == ""


def test_get_by_verify_token_finds_the_right_provider(tmp_path) -> None:
    store = WhatsappConfigStore(f"sqlite:///{tmp_path / 'wa-config.db'}")
    store.save(
        "provedor-um", enabled=True, phone_number_id="1", business_account_id="1",
        verify_token="token-um", access_token="x", app_secret="y",
    )
    store.save(
        "provedor-dois", enabled=True, phone_number_id="2", business_account_id="2",
        verify_token="token-dois", access_token="x", app_secret="y",
    )
    found = store.get_by_verify_token("token-dois")
    assert found.organization_id == "provedor-dois"
    assert store.get_by_verify_token("token-inexistente") is None


def test_consent_store_blocks_and_unblocks(tmp_path) -> None:
    store = WhatsappConsentStore(f"sqlite:///{tmp_path / 'wa-consent.db'}")
    assert store.is_blocked("provedor-um", "5511999990000") is False
    store.block("provedor-um", "5511999990000", "opt_out")
    assert store.is_blocked("provedor-um", "5511999990000") is True
    assert store.is_blocked("provedor-dois", "5511999990000") is False  # isolado
    store.unblock("provedor-um", "5511999990000")
    assert store.is_blocked("provedor-um", "5511999990000") is False


@pytest.mark.parametrize("text", ["parar", "PARAR", "  Sair  ", "stop", "cancelar"])
def test_is_opt_out_message_recognizes_common_phrasings(text: str) -> None:
    assert WhatsappConsentStore.is_opt_out_message(text) is True


def test_is_opt_out_message_ignores_ordinary_text() -> None:
    assert WhatsappConsentStore.is_opt_out_message("minha internet caiu") is False


def test_orchestrator_simulates_when_no_real_phone_is_known(tmp_path, monkeypatch) -> None:
    config_store = WhatsappConfigStore(f"sqlite:///{tmp_path / 'cfg.db'}")
    message_store = WhatsappMessageStore(f"sqlite:///{tmp_path / 'msg.db'}")
    config_store.save(
        "provedor-x", enabled=True, phone_number_id="1", business_account_id="1",
        verify_token="t", access_token="tok", app_secret="s",
    )
    monkeypatch.setattr("app.core.whatsapp_orchestrator.whatsapp_config_store", config_store)
    monkeypatch.setattr("app.core.whatsapp_orchestrator.whatsapp_message_store", message_store)

    result = send_whatsapp_message("provedor-x", "Olá", "test", phone=None)
    assert result["status"] == "simulated_sent"

    result_placeholder = send_whatsapp_message(
        "provedor-x", "Olá", "test", phone="+55 (00) 00000-0000"
    )
    assert result_placeholder["status"] == "simulated_sent"


def test_orchestrator_simulates_when_not_configured(tmp_path, monkeypatch) -> None:
    config_store = WhatsappConfigStore(f"sqlite:///{tmp_path / 'cfg.db'}")
    message_store = WhatsappMessageStore(f"sqlite:///{tmp_path / 'msg.db'}")
    monkeypatch.setattr("app.core.whatsapp_orchestrator.whatsapp_config_store", config_store)
    monkeypatch.setattr("app.core.whatsapp_orchestrator.whatsapp_message_store", message_store)

    result = send_whatsapp_message("provedor-sem-config", "Olá", "test", phone="5511999990000")
    assert result["status"] == "simulated_sent"


def test_orchestrator_blocks_send_to_opted_out_number(tmp_path, monkeypatch) -> None:
    config_store = WhatsappConfigStore(f"sqlite:///{tmp_path / 'cfg.db'}")
    message_store = WhatsappMessageStore(f"sqlite:///{tmp_path / 'msg.db'}")
    consent_store = WhatsappConsentStore(f"sqlite:///{tmp_path / 'consent.db'}")
    config_store.save(
        "provedor-x", enabled=True, phone_number_id="1", business_account_id="1",
        verify_token="t", access_token="tok", app_secret="s",
    )
    consent_store.block("provedor-x", "5511999990000")
    monkeypatch.setattr("app.core.whatsapp_orchestrator.whatsapp_config_store", config_store)
    monkeypatch.setattr("app.core.whatsapp_orchestrator.whatsapp_message_store", message_store)
    monkeypatch.setattr("app.core.whatsapp_orchestrator.whatsapp_consent_store", consent_store)

    result = send_whatsapp_message("provedor-x", "Olá", "test", phone="5511999990000")
    assert result["status"] == "blocked"


def test_orchestrator_records_failure_without_faking_success(tmp_path, monkeypatch) -> None:
    config_store = WhatsappConfigStore(f"sqlite:///{tmp_path / 'cfg.db'}")
    message_store = WhatsappMessageStore(f"sqlite:///{tmp_path / 'msg.db'}")
    config_store.save(
        "provedor-x", enabled=True, phone_number_id="1", business_account_id="1",
        verify_token="t", access_token="tok", app_secret="s",
    )
    monkeypatch.setattr("app.core.whatsapp_orchestrator.whatsapp_config_store", config_store)
    monkeypatch.setattr("app.core.whatsapp_orchestrator.whatsapp_message_store", message_store)

    class _FlakyClient:
        def send_text(self, **kwargs):
            raise WhatsappUnavailableError("whatsapp_request_timeout")

    monkeypatch.setattr("app.core.whatsapp_orchestrator.whatsapp_client", _FlakyClient())

    result = send_whatsapp_message("provedor-x", "Olá", "test", phone="5511999990000")
    assert result["status"] == "failed"
    assert result["error_reason"] == "whatsapp_request_timeout"


def test_orchestrator_records_real_success(tmp_path, monkeypatch) -> None:
    config_store = WhatsappConfigStore(f"sqlite:///{tmp_path / 'cfg.db'}")
    message_store = WhatsappMessageStore(f"sqlite:///{tmp_path / 'msg.db'}")
    config_store.save(
        "provedor-x", enabled=True, phone_number_id="1", business_account_id="1",
        verify_token="t", access_token="tok", app_secret="s",
    )
    monkeypatch.setattr("app.core.whatsapp_orchestrator.whatsapp_config_store", config_store)
    monkeypatch.setattr("app.core.whatsapp_orchestrator.whatsapp_message_store", message_store)

    class _StubClient:
        def send_text(self, **kwargs):
            return WhatsappSendResult(wa_message_id="wamid.abc123")

    monkeypatch.setattr("app.core.whatsapp_orchestrator.whatsapp_client", _StubClient())

    result = send_whatsapp_message("provedor-x", "Olá", "test", phone="5511999990000")
    assert result["status"] == "sent"
    assert result["wa_message_id"] == "wamid.abc123"


def test_contact_store_merges_partial_updates(tmp_path) -> None:
    store = WhatsappContactStore(f"sqlite:///{tmp_path / 'contacts.db'}")
    store.upsert("provedor-x", "5511999990000", login="cliente.pppoe")
    store.upsert("provedor-x", "5511999990000", display_name="João da Silva")
    contact = store.get("provedor-x", "5511999990000")
    assert contact["login"] == "cliente.pppoe"
    assert contact["display_name"] == "João da Silva"


# --- Webhook ---

def _webhook_client() -> TestClient:
    return TestClient(app)


def _configure_webhook_provider(client: TestClient) -> None:
    client.post(
        "/central/login",
        data={"username": "admin", "password": "Bancada@2026"},
    )
    client.post(
        "/central/whatsapp/config",
        data={
            "enabled": "1",
            "phone_number_id": "1234567890",
            "business_account_id": "999",
            "access_token": "test-access-token",
            "app_secret": "test-app-secret",
            "verify_token": "verify-me-123",
        },
    )


def test_webhook_verification_challenge_succeeds_with_correct_token() -> None:
    client = _webhook_client()
    _configure_webhook_provider(client)
    org = organization_store.get_active_by_slug("g7-networks")
    response = client.get(
        f"/api/v1/whatsapp/webhook/{org['slug']}",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "verify-me-123",
            "hub.challenge": "challenge-value-xyz",
        },
    )
    assert response.status_code == 200
    assert response.text == "challenge-value-xyz"


def test_webhook_verification_challenge_fails_with_wrong_token() -> None:
    client = _webhook_client()
    _configure_webhook_provider(client)
    org = organization_store.get_active_by_slug("g7-networks")
    response = client.get(
        f"/api/v1/whatsapp/webhook/{org['slug']}",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong-token",
            "hub.challenge": "challenge-value-xyz",
        },
    )
    assert response.status_code == 403


def test_webhook_rejects_unsigned_payload() -> None:
    client = _webhook_client()
    _configure_webhook_provider(client)
    org = organization_store.get_active_by_slug("g7-networks")
    response = client.post(
        f"/api/v1/whatsapp/webhook/{org['slug']}",
        json={"entry": []},
    )
    assert response.status_code == 401


def test_webhook_accepts_correctly_signed_payload_and_creates_a_draft() -> None:
    client = _webhook_client()
    _configure_webhook_provider(client)
    org = organization_store.get_active_by_slug("g7-networks")

    body = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "contacts": [
                                {"wa_id": "5511988887777", "profile": {"name": "Maria"}}
                            ],
                            "messages": [
                                {
                                    "from": "5511988887777",
                                    "id": "wamid.xyz",
                                    "type": "text",
                                    "text": {"body": "Minha internet caiu de novo"},
                                }
                            ],
                        }
                    }
                ]
            }
        ]
    }
    raw = json.dumps(body).encode("utf-8")
    signature = hmac.new(b"test-app-secret", raw, hashlib.sha256).hexdigest()

    response = client.post(
        f"/api/v1/whatsapp/webhook/{org['slug']}",
        content=raw,
        headers={
            "content-type": "application/json",
            "x-hub-signature-256": f"sha256={signature}",
        },
    )
    assert response.status_code == 200
    assert response.json()["messages"] == 1

    draft = ai_support_store.get_draft_for_request(org["id"], "whatsapp:5511988887777")
    assert draft is not None
    assert draft["status"] == "pending"


def test_webhook_opt_out_message_blocks_without_creating_a_draft() -> None:
    client = _webhook_client()
    _configure_webhook_provider(client)
    org = organization_store.get_active_by_slug("g7-networks")

    body = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "5511977776666",
                                    "id": "wamid.stop1",
                                    "type": "text",
                                    "text": {"body": "PARAR"},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    raw = json.dumps(body).encode("utf-8")
    signature = hmac.new(b"test-app-secret", raw, hashlib.sha256).hexdigest()

    response = client.post(
        f"/api/v1/whatsapp/webhook/{org['slug']}",
        content=raw,
        headers={
            "content-type": "application/json",
            "x-hub-signature-256": f"sha256={signature}",
        },
    )
    assert response.status_code == 200

    draft = ai_support_store.get_draft_for_request(org["id"], "whatsapp:5511977776666")
    assert draft is None

    from app.core.whatsapp_consent_store import whatsapp_consent_store
    assert whatsapp_consent_store.is_blocked(org["id"], "5511977776666") is True
    whatsapp_consent_store.unblock(org["id"], "5511977776666")  # limpeza
