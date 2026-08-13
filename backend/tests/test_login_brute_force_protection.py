from fastapi.testclient import TestClient

from app.core.login_attempt_store import LoginAttemptStore
from app.main import app

client = TestClient(app)


def test_login_attempt_store_locks_out_after_threshold(tmp_path) -> None:
    store = LoginAttemptStore(f"sqlite:///{tmp_path / 'attempts.db'}")
    for _ in range(7):
        store.record_failure("central:provedor-x", "admin")
    assert store.is_locked_out("central:provedor-x", "admin") is False

    store.record_failure("central:provedor-x", "admin")
    assert store.is_locked_out("central:provedor-x", "admin") is True


def test_login_attempt_store_success_resets_lockout(tmp_path) -> None:
    store = LoginAttemptStore(f"sqlite:///{tmp_path / 'attempts.db'}")
    for _ in range(8):
        store.record_failure("central:provedor-x", "admin")
    assert store.is_locked_out("central:provedor-x", "admin") is True

    store.record_success("central:provedor-x", "admin")
    assert store.is_locked_out("central:provedor-x", "admin") is False


def test_login_attempt_store_is_isolated_by_scope_and_identifier(tmp_path) -> None:
    store = LoginAttemptStore(f"sqlite:///{tmp_path / 'attempts.db'}")
    for _ in range(8):
        store.record_failure("central:provedor-x", "admin")

    assert store.is_locked_out("central:provedor-x", "outro.usuario") is False
    assert store.is_locked_out("central:provedor-y", "admin") is False
    assert store.is_locked_out("technician:provedor-x", "admin") is False


def test_central_login_locks_out_after_repeated_wrong_password() -> None:
    from app.core.central_user_store import central_user_store

    central_user_store.create(
        "g7-networks", "Central Teste Bloqueio", "central.bloqueio.teste",
        "SenhaCorreta@1", "admin",
    )
    for _ in range(8):
        response = client.post(
            "/central/login",
            data={
                "organization_slug": "g7-networks",
                "username": "central.bloqueio.teste",
                "password": "senha-errada",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
    # A tentativa seguinte, mesmo com a senha certa, deve ser bloqueada.
    locked_response = client.post(
        "/central/login",
        data={
            "organization_slug": "g7-networks",
            "username": "central.bloqueio.teste",
            "password": "SenhaCorreta@1",
        },
        follow_redirects=False,
    )
    assert locked_response.status_code == 303
    assert "locked=true" in locked_response.headers["location"]


def test_technician_login_locks_out_after_repeated_wrong_password() -> None:
    from app.core.technician_store import technician_store

    technician_store.create(
        "Técnico Teste Bloqueio", "tecnico.bloqueio.teste", "SenhaCorreta@1"
    )
    for _ in range(8):
        response = client.post(
            "/api/v1/auth/technician/login",
            json={"username": "tecnico.bloqueio.teste", "password": "senha-errada"},
        )
        assert response.status_code == 401
    locked_response = client.post(
        "/api/v1/auth/technician/login",
        json={"username": "tecnico.bloqueio.teste", "password": "SenhaCorreta@1"},
    )
    assert locked_response.status_code == 429


def test_responses_include_basic_security_headers() -> None:
    response = client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "geolocation=()" in response.headers["Permissions-Policy"]
    # HSTS só faz sentido em produção (exige HTTPS já estabelecido).
    assert "Strict-Transport-Security" not in response.headers
