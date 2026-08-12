from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _technician_login(username="tecnico", password="Campo@2026") -> dict:
    response = client.post(
        "/api/v1/auth/technician/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()


def test_change_password_requires_correct_current_password() -> None:
    login = _technician_login()
    response = client.post(
        "/api/v1/auth/technician/change-password",
        json={"current_password": "senha-errada", "new_password": "NovaSenh@123"},
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )
    assert response.status_code == 422


def test_change_password_rejects_short_new_password() -> None:
    login = _technician_login()
    response = client.post(
        "/api/v1/auth/technician/change-password",
        json={"current_password": "Campo@2026", "new_password": "curta"},
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )
    assert response.status_code == 422


def test_change_password_requires_authentication() -> None:
    response = client.post(
        "/api/v1/auth/technician/change-password",
        json={"current_password": "Campo@2026", "new_password": "NovaSenh@123"},
    )
    assert response.status_code == 401


def test_change_password_updates_login_credentials() -> None:
    from app.core.technician_store import technician_store

    technician_store.create("Técnico Teste Senha", "tecnico.senha.teste", "SenhaAntiga@1")
    login = _technician_login(username="tecnico.senha.teste", password="SenhaAntiga@1")

    changed = client.post(
        "/api/v1/auth/technician/change-password",
        json={"current_password": "SenhaAntiga@1", "new_password": "SenhaNova@2"},
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )
    assert changed.status_code == 200

    old_password_login = client.post(
        "/api/v1/auth/technician/login",
        json={"username": "tecnico.senha.teste", "password": "SenhaAntiga@1"},
    )
    assert old_password_login.status_code == 401

    new_password_login = client.post(
        "/api/v1/auth/technician/login",
        json={"username": "tecnico.senha.teste", "password": "SenhaNova@2"},
    )
    assert new_password_login.status_code == 200


def test_reset_password_invalidates_old_password_and_flags_must_change() -> None:
    from app.core.technician_store import technician_store

    created = technician_store.create(
        "Técnico Teste Reset", "tecnico.reset.teste", "SenhaOriginal@1"
    )

    temporary_password = technician_store.reset_password(
        created["id"], "g7-networks"
    )

    old_password_login = client.post(
        "/api/v1/auth/technician/login",
        json={"username": "tecnico.reset.teste", "password": "SenhaOriginal@1"},
    )
    assert old_password_login.status_code == 401

    new_login = client.post(
        "/api/v1/auth/technician/login",
        json={"username": "tecnico.reset.teste", "password": temporary_password},
    )
    assert new_login.status_code == 200
    assert new_login.json()["technician"]["must_change_password"] is True


def test_changing_password_after_reset_clears_the_must_change_flag() -> None:
    from app.core.technician_store import technician_store

    created = technician_store.create(
        "Técnico Teste Flag", "tecnico.flag.teste", "SenhaOriginal@1"
    )
    temporary_password = technician_store.reset_password(created["id"], "g7-networks")

    login = _technician_login(
        username="tecnico.flag.teste", password=temporary_password
    )
    assert login["technician"]["must_change_password"] is True

    client.post(
        "/api/v1/auth/technician/change-password",
        json={
            "current_password": temporary_password,
            "new_password": "SenhaDefinitiva@1",
        },
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )

    relogin = _technician_login(
        username="tecnico.flag.teste", password="SenhaDefinitiva@1"
    )
    assert relogin["technician"]["must_change_password"] is False


def test_admin_reset_shows_temporary_password_once_in_central() -> None:
    from app.core.technician_store import technician_store

    created = technician_store.create(
        "Técnico Teste Painel", "tecnico.painel.teste", "SenhaOriginal@1"
    )

    central_client = TestClient(app)
    central_client.post(
        "/central/login", data={"username": "admin", "password": "Bancada@2026"}
    )
    reset_response = central_client.post(
        f"/central/technicians/{created['id']}/reset-password"
    )
    assert reset_response.status_code == 200
    # O TestClient segue o redirecionamento automaticamente, então a página
    # já vem com a senha temporária exibida nesta mesma resposta.
    assert "Senha temporária gerada para Técnico Teste Painel" in reset_response.text

    # Não repete numa consulta seguinte — já foi consumida.
    dashboard_again = central_client.get("/central")
    assert "Senha temporária gerada" not in dashboard_again.text
