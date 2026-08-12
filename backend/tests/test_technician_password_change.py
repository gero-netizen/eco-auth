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
