import pytest

from app.core.cto_store import CtoStore
from app.core.geo import GeocodingError, geocode_address, haversine_meters


def test_cto_creation_and_isolation_by_organization(tmp_path) -> None:
    store = CtoStore(f"sqlite:///{tmp_path / 'ctos.db'}")
    cto = store.create(
        "provedor-um", "CTO-01", latitude=-12.25, longitude=-38.95,
        total_ports=8, splitter_ratio="1:8",
    )
    assert cto["code"] == "CTO-01"
    assert cto["available_ports"] == 8
    assert cto["occupied_ports"] == 0

    assert store.list_active("provedor-um") == [cto]
    assert store.list_active("provedor-dois") == []


def test_cto_rejects_invalid_coordinates_and_port_count(tmp_path) -> None:
    store = CtoStore(f"sqlite:///{tmp_path / 'ctos.db'}")
    with pytest.raises(ValueError):
        store.create("provedor-x", "CTO-BAD", latitude=200, longitude=0, total_ports=8)
    with pytest.raises(ValueError):
        store.create("provedor-x", "CTO-BAD", latitude=0, longitude=0, total_ports=0)


def test_port_assignment_updates_occupancy_and_prevents_double_booking(tmp_path) -> None:
    store = CtoStore(f"sqlite:///{tmp_path / 'ctos.db'}")
    cto = store.create("provedor-x", "CTO-02", latitude=-12.25, longitude=-38.95, total_ports=4)

    updated = store.assign_port("provedor-x", cto["id"], 1, "cliente.pppoe", work_order_id="wo-1")
    assert updated["occupied_ports"] == 1
    assert updated["available_ports"] == 3

    with pytest.raises(ValueError):
        store.assign_port("provedor-x", cto["id"], 1, "outro.cliente")  # porta ja ocupada

    with pytest.raises(ValueError):
        store.assign_port("provedor-x", cto["id"], 99, "cliente.pppoe")  # porta fora da faixa


def test_releasing_a_port_frees_it_for_reassignment(tmp_path) -> None:
    store = CtoStore(f"sqlite:///{tmp_path / 'ctos.db'}")
    cto = store.create("provedor-x", "CTO-03", latitude=-12.25, longitude=-38.95, total_ports=4)
    store.assign_port("provedor-x", cto["id"], 1, "cliente.pppoe")
    store.release_port("provedor-x", cto["id"], 1)

    updated = store.assign_port("provedor-x", cto["id"], 1, "outro.cliente")
    assert updated["assignments"][0]["login"] == "outro.cliente"


def test_deactivated_cto_no_longer_appears_in_active_list(tmp_path) -> None:
    store = CtoStore(f"sqlite:///{tmp_path / 'ctos.db'}")
    cto = store.create("provedor-x", "CTO-04", latitude=-12.25, longitude=-38.95, total_ports=4)
    store.deactivate("provedor-x", cto["id"])
    assert store.list_active("provedor-x") == []


def test_haversine_distance_between_known_points() -> None:
    # Feira de Santana ao centro de Salvador: aproximadamente 100km em linha reta.
    feira_de_santana = (-12.2664, -38.9663)
    salvador = (-12.9777, -38.5016)
    distance_km = haversine_meters(*feira_de_santana, *salvador) / 1000
    assert 90 < distance_km < 110


def test_haversine_distance_zero_for_same_point() -> None:
    assert haversine_meters(-12.25, -38.95, -12.25, -38.95) == 0


def test_geocode_address_rejects_empty_address() -> None:
    with pytest.raises(GeocodingError):
        geocode_address("")


def test_geocode_address_raises_on_network_failure(monkeypatch) -> None:
    import httpx

    class _FailingClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, *args, **kwargs):
            raise httpx.ConnectError("no network")

    monkeypatch.setattr("app.core.geo.httpx.Client", lambda **kwargs: _FailingClient())
    with pytest.raises(GeocodingError):
        geocode_address("Rua Exemplo, 123")
