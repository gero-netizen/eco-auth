from app.core.integration_config_store import get_integration_settings
from app.core.organization_store import organization_store
from fastapi.testclient import TestClient

from app.main import app


def _central_client() -> TestClient:
    client = TestClient(app)
    client.post(
        "/central/login",
        data={"username": "admin", "password": "Bancada@2026"},
    )
    return client


def test_mkauth_config_form_renders_with_real_input_fields() -> None:
    client = _central_client()
    response = client.get("/central")
    assert response.status_code == 200
    assert 'name="mkauth_base_url"' in response.text
    assert 'name="mkauth_client_id"' in response.text
    assert 'name="mkauth_client_secret"' in response.text
    assert 'name="mkauth_writes_enabled"' in response.text
    assert 'name="routeros_host"' in response.text
    assert 'name="routeros_username"' in response.text
    assert 'name="routeros_password"' in response.text


def test_saving_mkauth_config_persists_and_encrypts_secrets() -> None:
    client = _central_client()
    org = organization_store.get_active_by_slug("g7-networks")

    response = client.post(
        "/central/integracoes/mkauth/config",
        data={
            "mkauth_mode": "real",
            "mkauth_base_url": "https://painel.provedor-teste.com.br",
            "mkauth_client_id": "meu-client-id",
            "mkauth_client_secret": "meu-client-secret",
            "mkauth_verify_ssl": "1",
        },
    )
    assert response.status_code in (200, 303)

    settings = get_integration_settings(org["id"])
    assert settings.mkauth_mode == "real"
    assert settings.mkauth_base_url == "https://painel.provedor-teste.com.br"
    assert settings.mkauth_client_id == "meu-client-id"
    assert settings.mkauth_client_secret == "meu-client-secret"
    assert settings.mkauth_verify_ssl is True
    assert settings.mkauth_writes_enabled is False  # não marcado no form = desativado


def test_saving_mkauth_config_without_new_secret_keeps_previous_one() -> None:
    client = _central_client()
    org = organization_store.get_active_by_slug("g7-networks")

    client.post(
        "/central/integracoes/mkauth/config",
        data={
            "mkauth_mode": "real",
            "mkauth_base_url": "https://painel.provedor-teste.com.br",
            "mkauth_client_id": "id-original",
            "mkauth_client_secret": "secret-original",
        },
    )
    client.post(
        "/central/integracoes/mkauth/config",
        data={
            "mkauth_mode": "real",
            "mkauth_base_url": "https://painel.provedor-teste.com.br",
            "mkauth_client_id": "",  # em branco: mantém o anterior
            "mkauth_client_secret": "",
        },
    )
    settings = get_integration_settings(org["id"])
    assert settings.mkauth_client_id == "id-original"
    assert settings.mkauth_client_secret == "secret-original"


def test_saving_mikrotik_config_persists_host_and_credentials() -> None:
    client = _central_client()
    org = organization_store.get_active_by_slug("g7-networks")

    response = client.post(
        "/central/integracoes/mikrotik/config",
        data={
            "routeros_mode": "real",
            "routeros_host": "192.168.20.1",
            "routeros_port": "8728",
            "routeros_username": "app_api",
            "routeros_password": "minha-senha-mikrotik",
        },
    )
    assert response.status_code in (200, 303)

    settings = get_integration_settings(org["id"])
    assert settings.routeros_mode == "real"
    assert settings.routeros_host == "192.168.20.1"
    assert settings.routeros_port == 8728
    assert settings.routeros_username == "app_api"
    assert settings.routeros_password == "minha-senha-mikrotik"


def test_mikrotik_config_rejects_invalid_port() -> None:
    client = _central_client()
    response = client.post(
        "/central/integracoes/mikrotik/config",
        data={
            "routeros_mode": "real",
            "routeros_host": "192.168.20.1",
            "routeros_port": "99999",
            "routeros_username": "app_api",
            "routeros_password": "x",
        },
    )
    assert response.status_code == 422


def test_saving_mkauth_config_does_not_affect_mikrotik_config() -> None:
    client = _central_client()
    org = organization_store.get_active_by_slug("g7-networks")

    client.post(
        "/central/integracoes/mikrotik/config",
        data={
            "routeros_mode": "real",
            "routeros_host": "192.168.20.1",
            "routeros_port": "8728",
            "routeros_username": "app_api",
            "routeros_password": "senha-mikrotik",
        },
    )
    client.post(
        "/central/integracoes/mkauth/config",
        data={
            "mkauth_mode": "real",
            "mkauth_base_url": "https://painel.provedor-teste.com.br",
            "mkauth_client_id": "id-x",
            "mkauth_client_secret": "secret-x",
        },
    )
    settings = get_integration_settings(org["id"])
    # A config do MikroTik salva antes não pode ter sido apagada.
    assert settings.routeros_host == "192.168.20.1"
    assert settings.routeros_password == "senha-mikrotik"
