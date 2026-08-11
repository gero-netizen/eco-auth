import asyncio
import hashlib
import hmac
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.routes import integrations
from app.core.financial_payment_store import FinancialPaymentStore
from app.core.mercado_pago_config_store import MercadoPagoConfigStore
from app.core.organization_store import organization_store
from app.integrations.mercado_pago.client import validate_webhook_signature
from app.main import app


def test_mercado_pago_config_is_isolated_and_encrypted(tmp_path) -> None:
    db_path = tmp_path / "mp-config.db"
    store = MercadoPagoConfigStore(f"sqlite:///{db_path}")
    store.save(
        "provedor-um", enabled=True,
        access_token="APP_USR-super-secret", webhook_secret="webhook-secret-value",
    )
    raw_bytes = db_path.read_bytes()
    assert b"APP_USR-super-secret" not in raw_bytes
    assert b"webhook-secret-value" not in raw_bytes

    fetched = store.get("provedor-um")
    assert fetched.access_token == "APP_USR-super-secret"

    untouched = store.get("provedor-dois")
    assert untouched.enabled is False
    assert untouched.access_token == ""


def test_financial_payment_store_enforces_idempotent_confirmation(tmp_path) -> None:
    store = FinancialPaymentStore(f"sqlite:///{tmp_path / 'payments.db'}")
    payment = store.create(
        "provedor-x", "title-uuid-1", "cliente.pppoe", "120.00", "ref-1",
        mp_payment_id="mp-1",
    )
    first = store.mark_confirmed("provedor-x", payment["id"], "mp-1")
    assert first["status"] == "confirmed"
    # Reentrega do webhook: não deve alterar nada nem levantar erro.
    second = store.mark_confirmed("provedor-x", payment["id"], "mp-1")
    assert second["status"] == "confirmed"
    assert second["confirmed_at"] == first["confirmed_at"]


def test_financial_payment_store_is_isolated_by_organization(tmp_path) -> None:
    store = FinancialPaymentStore(f"sqlite:///{tmp_path / 'payments.db'}")
    store.create("provedor-um", "t1", "cliente-a", "50.00", "ref-a")
    store.create("provedor-dois", "t2", "cliente-b", "60.00", "ref-b")
    assert len(store.list_recent("provedor-um")) == 1
    assert len(store.list_recent("provedor-dois")) == 1
    assert store.get_by_external_reference("provedor-um", "ref-b") is None


def _sign(secret: str, data_id: str, ts: int | None = None) -> str:
    timestamp = ts or int(datetime.now(UTC).timestamp())
    manifest = f"id:{data_id.lower()};ts:{timestamp};"
    signature = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return f"ts={timestamp},v1={signature}"


def test_validate_webhook_signature_accepts_correct_signature() -> None:
    header = _sign("my-secret", "12345")
    assert validate_webhook_signature(
        x_signature=header, x_request_id=None, data_id="12345", secret="my-secret"
    ) is True


def test_validate_webhook_signature_rejects_wrong_secret() -> None:
    header = _sign("my-secret", "12345")
    assert validate_webhook_signature(
        x_signature=header, x_request_id=None, data_id="12345", secret="wrong-secret"
    ) is False


def test_validate_webhook_signature_rejects_old_timestamp() -> None:
    old_ts = int(datetime.now(UTC).timestamp()) - 3600  # 1h atrás
    header = _sign("my-secret", "12345", ts=old_ts)
    assert validate_webhook_signature(
        x_signature=header, x_request_id=None, data_id="12345", secret="my-secret"
    ) is False


def test_confirm_title_payment_blocks_duplicate_baixa(monkeypatch) -> None:
    class StubStore:
        def has_real_payment(self, title_uuid: str) -> bool:
            return True  # já foi pago antes

    monkeypatch.setattr(integrations, "_pix_simulation_store", lambda: StubStore())
    result = asyncio.run(
        integrations.confirm_title_payment(
            "provedor-x", SimpleNamespace(), object(), "title-1", "cliente.pppoe"
        )
    )
    assert result["status"] == "duplicate_blocked"


def test_confirm_title_payment_blocks_owner_mismatch(monkeypatch) -> None:
    class StubStore:
        def has_real_payment(self, title_uuid: str) -> bool:
            return False

    class StubClient:
        async def get_title(self, title_uuid: str) -> dict:
            return {"login": "outro.cliente", "valor": "50.00", "status": "vencido"}

    monkeypatch.setattr(integrations, "_pix_simulation_store", lambda: StubStore())
    result = asyncio.run(
        integrations.confirm_title_payment(
            "provedor-x", SimpleNamespace(), StubClient(), "title-1", "cliente.pppoe"
        )
    )
    assert result["status"] == "title_owner_mismatch"


def test_confirm_title_payment_blocks_already_paid(monkeypatch) -> None:
    class StubStore:
        def has_real_payment(self, title_uuid: str) -> bool:
            return False

    class StubClient:
        async def get_title(self, title_uuid: str) -> dict:
            return {"login": "cliente.pppoe", "valor": "50.00", "status": "pago"}

    monkeypatch.setattr(integrations, "_pix_simulation_store", lambda: StubStore())
    result = asyncio.run(
        integrations.confirm_title_payment(
            "provedor-x", SimpleNamespace(), StubClient(), "title-1", "cliente.pppoe"
        )
    )
    assert result["status"] == "title_already_paid"


# --- Webhook ---

def _webhook_client() -> TestClient:
    return TestClient(app)


def _configure_financial_webhook(client: TestClient) -> None:
    client.post(
        "/central/login",
        data={"username": "admin", "password": "Bancada@2026"},
    )
    client.post(
        "/central/financeiro/mercadopago/config",
        data={
            "enabled": "1",
            "access_token": "test-mp-token",
            "webhook_secret": "test-mp-webhook-secret",
        },
    )


def test_financial_webhook_rejects_bad_signature() -> None:
    client = _webhook_client()
    _configure_financial_webhook(client)
    org = organization_store.get_active_by_slug("g7-networks")
    response = client.post(
        f"/api/v1/financial/webhook/{org['slug']}?data.id=999",
        headers={"x-signature": "ts=1,v1=deadbeef"},
    )
    assert response.status_code == 401


def test_financial_webhook_ignores_unknown_payment_with_valid_signature() -> None:
    client = _webhook_client()
    _configure_financial_webhook(client)
    org = organization_store.get_active_by_slug("g7-networks")
    header = _sign("test-mp-webhook-secret", "unknown-payment-id")
    response = client.post(
        f"/api/v1/financial/webhook/{org['slug']}?data.id=unknown-payment-id",
        headers={"x-signature": header},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


def test_financial_webhook_second_delivery_is_idempotent(monkeypatch) -> None:
    """Simula reentrega do mesmo webhook: a segunda chamada não deve tentar
    confirmar de novo (o que arriscaria uma baixa duplicada)."""
    from app.core.financial_payment_store import financial_payment_store

    org = organization_store.get_active_by_slug("g7-networks")
    payment = financial_payment_store.create(
        org["id"], "title-idem-1", "cliente.idem", "77.00",
        f"{org['id']}:title-idem-1:ref-idem", mp_payment_id="mp-idem-1",
    )
    financial_payment_store.mark_confirmed(org["id"], payment["id"], "mp-idem-1")

    client = _webhook_client()
    _configure_financial_webhook(client)
    header = _sign("test-mp-webhook-secret", "mp-idem-1")
    response = client.post(
        f"/api/v1/financial/webhook/{org['slug']}?data.id=mp-idem-1",
        headers={"x-signature": header},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "already_confirmed"
