import asyncio
from types import SimpleNamespace

from app.api.routes import network as network_routes
from app.core import network_monitor
from app.core.network_metrics_store import NetworkMetricsStore
from app.core.tenant_context import set_current_organization


class _StubRouterClient:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def diagnose(self) -> dict:
        return {
            "router": {"cpu_load": "5%"},
            "ppp_aaa": {"use_radius": True, "accounting": True},
            "radius": [{"address": "10.0.0.1", "disabled": False}],
            "sessions": [{"username": f"cliente{i}"} for i in range(10)],
        }


class _StubRouterClientDown:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def diagnose(self) -> dict:
        raise TimeoutError("no response")


class _StubRouterClientRadiusDisabled(_StubRouterClient):
    def diagnose(self) -> dict:
        data = super().diagnose()
        data["radius"] = [{"address": "10.0.0.1", "disabled": True}]
        return data


def _real_settings(**overrides) -> SimpleNamespace:
    defaults = dict(routeros_mode="real", routeros_host="192.168.20.1", routeros_port=8728,
                     routeros_username="app_api", routeros_password="secret")
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_skips_when_routeros_not_in_real_mode(monkeypatch) -> None:
    monkeypatch.setattr(
        network_monitor, "get_integration_settings",
        lambda organization_id=None: SimpleNamespace(routeros_mode="simulated", routeros_username=""),
    )
    result = asyncio.run(network_monitor.check_network_health("provedor-x"))
    assert result["status"] == "skipped"


def test_router_down_opens_incident_and_notifies(tmp_path, monkeypatch) -> None:
    metrics_store = NetworkMetricsStore(f"sqlite:///{tmp_path / 'metrics.db'}")
    notified = []

    monkeypatch.setattr(network_monitor, "get_integration_settings", lambda organization_id=None: _real_settings())
    monkeypatch.setattr(network_monitor, "network_metrics_store", metrics_store)
    monkeypatch.setattr(network_monitor, "RouterOsReadOnlyClient", _StubRouterClientDown)
    monkeypatch.setattr(network_monitor, "_notify_affected_customers", lambda org, msg: notified.append((org, msg)))
    set_current_organization("provedor-down")

    result = asyncio.run(network_monitor.check_network_health("provedor-down"))
    assert result["status"] == "router_down"

    incident = network_routes.get_active_incident_by_kind("provedor-down", "router_down")
    assert incident is not None
    assert incident["auto_detected"] == 1
    assert len(notified) == 1

    # Uma segunda checagem enquanto ainda está fora do ar não deve duplicar o incidente.
    asyncio.run(network_monitor.check_network_health("provedor-down"))
    assert len(notified) == 1


def test_router_recovering_resolves_the_incident(tmp_path, monkeypatch) -> None:
    metrics_store = NetworkMetricsStore(f"sqlite:///{tmp_path / 'metrics.db'}")
    monkeypatch.setattr(network_monitor, "get_integration_settings", lambda organization_id=None: _real_settings())
    monkeypatch.setattr(network_monitor, "network_metrics_store", metrics_store)
    monkeypatch.setattr(network_monitor, "_notify_affected_customers", lambda org, msg: None)
    set_current_organization("provedor-recovery")

    monkeypatch.setattr(network_monitor, "RouterOsReadOnlyClient", _StubRouterClientDown)
    asyncio.run(network_monitor.check_network_health("provedor-recovery"))
    assert network_routes.get_active_incident_by_kind("provedor-recovery", "router_down") is not None

    monkeypatch.setattr(network_monitor, "RouterOsReadOnlyClient", _StubRouterClient)
    asyncio.run(network_monitor.check_network_health("provedor-recovery"))
    assert network_routes.get_active_incident_by_kind("provedor-recovery", "router_down") is None


def test_radius_disabled_opens_and_recovery_closes_incident(tmp_path, monkeypatch) -> None:
    metrics_store = NetworkMetricsStore(f"sqlite:///{tmp_path / 'metrics.db'}")
    monkeypatch.setattr(network_monitor, "get_integration_settings", lambda organization_id=None: _real_settings())
    monkeypatch.setattr(network_monitor, "network_metrics_store", metrics_store)
    monkeypatch.setattr(network_monitor, "_notify_affected_customers", lambda org, msg: None)
    set_current_organization("provedor-radius")

    monkeypatch.setattr(network_monitor, "RouterOsReadOnlyClient", _StubRouterClientRadiusDisabled)
    asyncio.run(network_monitor.check_network_health("provedor-radius"))
    assert network_routes.get_active_incident_by_kind("provedor-radius", "radius_down") is not None

    monkeypatch.setattr(network_monitor, "RouterOsReadOnlyClient", _StubRouterClient)
    asyncio.run(network_monitor.check_network_health("provedor-radius"))
    assert network_routes.get_active_incident_by_kind("provedor-radius", "radius_down") is None


def test_disconnection_spike_is_detected_against_baseline(tmp_path, monkeypatch) -> None:
    metrics_store = NetworkMetricsStore(f"sqlite:///{tmp_path / 'metrics.db'}")
    monkeypatch.setattr(network_monitor, "get_integration_settings", lambda organization_id=None: _real_settings())
    monkeypatch.setattr(network_monitor, "network_metrics_store", metrics_store)
    monkeypatch.setattr(network_monitor, "_notify_affected_customers", lambda org, msg: None)
    set_current_organization("provedor-spike")

    # Estabelece uma base histórica de 10 sessões ativas.
    for _ in range(3):
        metrics_store.record("provedor-spike", router_reachable=True, active_sessions=10, cpu_load=5, radius_ok=True)

    class _StubClientFewSessions(_StubRouterClient):
        def diagnose(self) -> dict:
            data = super().diagnose()
            data["sessions"] = [{"username": "cliente1"}]  # só 1, era ~10
            return data

    monkeypatch.setattr(network_monitor, "RouterOsReadOnlyClient", _StubClientFewSessions)
    result = asyncio.run(network_monitor.check_network_health("provedor-spike"))
    assert result["status"] == "ok"

    incident = network_routes.get_active_incident_by_kind("provedor-spike", "disconnection_spike")
    assert incident is not None


def test_no_spike_incident_when_sessions_are_normal(tmp_path, monkeypatch) -> None:
    metrics_store = NetworkMetricsStore(f"sqlite:///{tmp_path / 'metrics.db'}")
    monkeypatch.setattr(network_monitor, "get_integration_settings", lambda organization_id=None: _real_settings())
    monkeypatch.setattr(network_monitor, "network_metrics_store", metrics_store)
    monkeypatch.setattr(network_monitor, "_notify_affected_customers", lambda org, msg: None)
    monkeypatch.setattr(network_monitor, "RouterOsReadOnlyClient", _StubRouterClient)
    set_current_organization("provedor-normal")

    for _ in range(3):
        asyncio.run(network_monitor.check_network_health("provedor-normal"))

    assert network_routes.get_active_incident_by_kind("provedor-normal", "disconnection_spike") is None
