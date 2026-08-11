import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.core.trust_unlock_orchestrator import request_trust_unlock
from app.core.trust_unlock_rules_store import TrustUnlockRulesStore
from app.core.trust_unlock_store import TrustUnlockStore
from app.core.tenant_context import set_current_organization


def test_rules_store_is_isolated_and_defaults_are_sane(tmp_path) -> None:
    store = TrustUnlockRulesStore(f"sqlite:///{tmp_path / 'rules.db'}")
    defaults = store.get("provedor-sem-config")
    assert defaults.duration_hours == 48
    assert defaults.max_unlocks_per_month == 2

    store.save(
        "provedor-um", duration_hours=24, max_unlocks_per_month=1,
        max_debt_amount=100.0, max_overdue_titles=1, min_interval_hours=48,
        notify_before_relock_minutes=30,
    )
    updated = store.get("provedor-um")
    assert updated.duration_hours == 24
    assert updated.max_unlocks_per_month == 1

    untouched = store.get("provedor-dois")
    assert untouched.duration_hours == 48  # não afetado pelo provedor-um


def test_rules_store_rejects_invalid_values(tmp_path) -> None:
    store = TrustUnlockRulesStore(f"sqlite:///{tmp_path / 'rules.db'}")
    with pytest.raises(ValueError):
        store.save(
            "provedor-x", duration_hours=0, max_unlocks_per_month=1,
            max_debt_amount=100.0, max_overdue_titles=1, min_interval_hours=1,
            notify_before_relock_minutes=1,
        )


class _StubClient:
    def __init__(self, details: dict, overdue_titles: list[dict] | None = None) -> None:
        self._details = details
        self._overdue_titles = overdue_titles or []
        self.writes: list[tuple] = []

    async def get_client_details(self, login: str) -> dict:
        return self._details

    async def list_titles_by_situation(self, login: str, situation: str) -> list[dict]:
        return self._overdue_titles if situation == "vencido" else []

    async def set_client_trust_observation(self, client_uuid: str, enabled: bool, expires_at=None) -> dict:
        self.writes.append((client_uuid, enabled))
        self._details = {**self._details, "observacao": "sim" if enabled else "nao"}
        return {"status": "sucesso"}


def _rules_store(tmp_path, **overrides) -> TrustUnlockRulesStore:
    store = TrustUnlockRulesStore(f"sqlite:///{tmp_path / 'rules.db'}")
    defaults = dict(
        duration_hours=48, max_unlocks_per_month=2, max_debt_amount=400.0,
        max_overdue_titles=3, min_interval_hours=72, notify_before_relock_minutes=120,
    )
    defaults.update(overrides)
    store.save("provedor-x", **defaults)
    return store


def test_disabled_client_is_never_unlocked(tmp_path, monkeypatch) -> None:
    rules_store = _rules_store(tmp_path)
    monkeypatch.setattr(
        "app.core.trust_unlock_orchestrator.trust_unlock_rules_store", rules_store
    )
    client = _StubClient({"uuid": "u1", "bloqueado": "sim", "ativo": "nao"})
    unlock_store = TrustUnlockStore(f"sqlite:///{tmp_path / 'unlocks.db'}")
    set_current_organization("provedor-x")

    result = asyncio.run(
        request_trust_unlock("provedor-x", unlock_store, client, "cliente.pppoe", "motivo")
    )
    assert result["status"] == "client_disabled"
    assert client.writes == []


def test_not_blocked_client_is_rejected(tmp_path, monkeypatch) -> None:
    rules_store = _rules_store(tmp_path)
    monkeypatch.setattr(
        "app.core.trust_unlock_orchestrator.trust_unlock_rules_store", rules_store
    )
    client = _StubClient({"uuid": "u1", "bloqueado": "nao", "status_corte": "-", "ativo": "sim"})
    unlock_store = TrustUnlockStore(f"sqlite:///{tmp_path / 'unlocks.db'}")
    set_current_organization("provedor-x")

    result = asyncio.run(
        request_trust_unlock("provedor-x", unlock_store, client, "cliente.pppoe", "motivo")
    )
    assert result["status"] == "not_blocked"


def test_too_many_overdue_titles_blocks_unlock(tmp_path, monkeypatch) -> None:
    rules_store = _rules_store(tmp_path, max_overdue_titles=2)
    monkeypatch.setattr(
        "app.core.trust_unlock_orchestrator.trust_unlock_rules_store", rules_store
    )
    overdue = [{"valor": "10.00"} for _ in range(3)]
    client = _StubClient({"uuid": "u1", "bloqueado": "sim", "ativo": "sim"}, overdue)
    unlock_store = TrustUnlockStore(f"sqlite:///{tmp_path / 'unlocks.db'}")
    set_current_organization("provedor-x")

    result = asyncio.run(
        request_trust_unlock("provedor-x", unlock_store, client, "cliente.pppoe", "motivo")
    )
    assert result["status"] == "too_many_overdue_titles"
    assert result["count"] == 3


def test_debt_too_high_blocks_unlock(tmp_path, monkeypatch) -> None:
    rules_store = _rules_store(tmp_path, max_debt_amount=50.0, max_overdue_titles=5)
    monkeypatch.setattr(
        "app.core.trust_unlock_orchestrator.trust_unlock_rules_store", rules_store
    )
    overdue = [{"valor": "40.00"}, {"valor": "30.00"}]  # soma 70 > limite 50
    client = _StubClient({"uuid": "u1", "bloqueado": "sim", "ativo": "sim"}, overdue)
    unlock_store = TrustUnlockStore(f"sqlite:///{tmp_path / 'unlocks.db'}")
    set_current_organization("provedor-x")

    result = asyncio.run(
        request_trust_unlock("provedor-x", unlock_store, client, "cliente.pppoe", "motivo")
    )
    assert result["status"] == "debt_too_high"
    assert result["amount"] == 70.0


def test_monthly_unlock_limit_is_enforced(tmp_path, monkeypatch) -> None:
    rules_store = _rules_store(tmp_path, max_unlocks_per_month=1, min_interval_hours=0)
    monkeypatch.setattr(
        "app.core.trust_unlock_orchestrator.trust_unlock_rules_store", rules_store
    )
    client = _StubClient({"uuid": "u1", "bloqueado": "sim", "ativo": "sim"})
    unlock_store = TrustUnlockStore(f"sqlite:///{tmp_path / 'unlocks.db'}")
    set_current_organization("provedor-x")

    first = asyncio.run(
        request_trust_unlock("provedor-x", unlock_store, client, "cliente.pppoe", "motivo 1")
    )
    assert first["status"] == "unlocked"

    second = asyncio.run(
        request_trust_unlock("provedor-x", unlock_store, client, "cliente.pppoe", "motivo 2")
    )
    assert second["status"] == "monthly_limit_reached"


def test_minimum_interval_between_requests_is_enforced(tmp_path, monkeypatch) -> None:
    rules_store = _rules_store(tmp_path, max_unlocks_per_month=10, min_interval_hours=48)
    monkeypatch.setattr(
        "app.core.trust_unlock_orchestrator.trust_unlock_rules_store", rules_store
    )
    client = _StubClient({"uuid": "u1", "bloqueado": "sim", "ativo": "sim"})
    unlock_store = TrustUnlockStore(f"sqlite:///{tmp_path / 'unlocks.db'}")
    set_current_organization("provedor-x")

    first = asyncio.run(
        request_trust_unlock("provedor-x", unlock_store, client, "cliente.pppoe", "motivo")
    )
    assert first["status"] == "unlocked"

    second = asyncio.run(
        request_trust_unlock("provedor-x", unlock_store, client, "cliente.pppoe", "motivo de novo")
    )
    assert second["status"] == "interval_not_elapsed"


def test_all_rules_pass_grants_unlock_for_configured_duration(tmp_path, monkeypatch) -> None:
    rules_store = _rules_store(tmp_path, duration_hours=12)
    monkeypatch.setattr(
        "app.core.trust_unlock_orchestrator.trust_unlock_rules_store", rules_store
    )
    client = _StubClient(
        {"uuid": "u1", "bloqueado": "sim", "ativo": "sim"},
        [{"valor": "10.00"}],
    )
    unlock_store = TrustUnlockStore(f"sqlite:///{tmp_path / 'unlocks.db'}")
    set_current_organization("provedor-x")

    result = asyncio.run(
        request_trust_unlock("provedor-x", unlock_store, client, "cliente.pppoe", "motivo")
    )
    assert result["status"] == "unlocked"
    assert result["valid_hours"] == 12
    assert client.writes == [("u1", True)]


def test_trust_unlock_store_count_since_and_recent_are_isolated_by_org(tmp_path) -> None:
    store = TrustUnlockStore(f"sqlite:///{tmp_path / 'unlocks.db'}")
    set_current_organization("provedor-um")
    store.create("uuid-1", "cliente.pppoe", "motivo")
    since = datetime.now(UTC) - timedelta(days=1)
    assert store.count_since("cliente.pppoe", since) == 1

    set_current_organization("provedor-dois")
    assert store.count_since("cliente.pppoe", since) == 0
    assert store.get_most_recent_by_login("cliente.pppoe") is None
