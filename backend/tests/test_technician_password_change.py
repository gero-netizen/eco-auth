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


def _central_login() -> TestClient:
    admin_client = TestClient(app)
    response = admin_client.post(
        "/central/login",
        data={"username": "admin", "password": "Bancada@2026"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return admin_client


def test_deleting_an_active_technician_is_rejected() -> None:
    from app.core.technician_store import technician_store

    created = technician_store.create(
        "Técnico Teste Exclusão Ativo", "tecnico.exclusao.ativo", "SenhaForte@1"
    )
    admin_client = _central_login()
    response = admin_client.post(f"/central/technicians/{created['id']}/delete")
    assert response.status_code == 409

    # Continua existindo e ativo — a exclusão não teve efeito nenhum.
    remaining = [
        item
        for item in technician_store.list_all("g7-networks")
        if item["id"] == created["id"]
    ]
    assert len(remaining) == 1
    assert remaining[0]["active"] == 1


def test_deleting_an_inactive_technician_removes_it() -> None:
    from app.core.technician_store import technician_store

    created = technician_store.create(
        "Técnico Teste Exclusão Inativo", "tecnico.exclusao.inativo", "SenhaForte@1"
    )
    technician_store.set_active(created["id"], False, "g7-networks")

    admin_client = _central_login()
    response = admin_client.post(
        f"/central/technicians/{created['id']}/delete", follow_redirects=False
    )
    assert response.status_code == 303

    remaining = [
        item
        for item in technician_store.list_all("g7-networks")
        if item["id"] == created["id"]
    ]
    assert remaining == []


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
