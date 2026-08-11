import asyncio
from uuid import uuid4

from app.core.customer_location_store import CustomerLocationStore
from app.core.work_order_history_store import WorkOrderHistoryStore
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
technician_login = client.post(
    "/api/v1/auth/technician/login",
    json={"username": "tecnico", "password": "Campo@2026"},
)
client.headers.update(
    {"Authorization": f"Bearer {technician_login.json()['access_token']}"}
)


def _create_work_order() -> dict:
    response = client.post(
        "/api/v1/work-orders",
        json={
            "customer_name": "Cliente Localização",
            "address": "Rua da Localização, 123",
        },
    )
    assert response.status_code == 201
    return response.json()


def _push_transition(work_order: dict, to_status: str, **payload_extra) -> dict:
    operation = {
        "device_id": str(uuid4()),
        "operations": [{
            "operation_id": str(uuid4()),
            "entity_type": "work_order",
            "entity_id": work_order["id"],
            "kind": "transition",
            "base_version": work_order["version"],
            "occurred_at": "2026-08-11T12:00:00Z",
            "payload": {"to_status": to_status, **payload_extra},
        }],
    }
    response = client.post("/api/v1/sync/push", json=operation)
    assert response.status_code == 200
    return response.json()["results"][0]


def test_completing_with_gps_updates_the_work_orders_own_location() -> None:
    order = _create_work_order()
    result = _push_transition(
        order, "completed", latitude=-12.2664, longitude=-38.9663,
        note="Instalação concluída",
    )
    assert result["status"] == "accepted"

    pulled = client.get("/api/v1/sync/pull", params={"cursor": "0"})
    updated_order = [
        change["payload"]
        for change in pulled.json()["changes"]
        if change["entity_id"] == order["id"]
    ][-1]
    assert updated_order["latitude"] == -12.2664
    assert updated_order["longitude"] == -38.9663


def test_transitioning_without_gps_does_not_crash() -> None:
    order = _create_work_order()
    result = _push_transition(order, "completed")
    assert result["status"] == "accepted"


def test_transition_history_is_persisted() -> None:
    order = _create_work_order()
    _push_transition(order, "traveling")
    from app.core.work_order_history_store import work_order_history_store

    history = work_order_history_store.list_for_work_order("g7-networks", order["id"])
    assert any(entry["to_status"] == "traveling" for entry in history)
    assert any(entry["from_status"] == "assigned" for entry in history)


def test_customer_location_store_is_isolated_and_upserts(tmp_path) -> None:
    store = CustomerLocationStore(f"sqlite:///{tmp_path / 'locations.db'}")
    store.confirm("provedor-um", "cliente-a", -12.25, -38.95, source_work_order_id="wo-1")
    assert store.get("provedor-um", "cliente-a")["latitude"] == -12.25
    assert store.get("provedor-dois", "cliente-a") is None

    store.confirm("provedor-um", "cliente-a", -12.30, -38.90, source_work_order_id="wo-2")
    updated = store.get("provedor-um", "cliente-a")
    assert updated["latitude"] == -12.30
    assert updated["source_work_order_id"] == "wo-2"


def test_work_order_history_store_orders_entries_chronologically(tmp_path) -> None:
    store = WorkOrderHistoryStore(f"sqlite:///{tmp_path / 'history.db'}")
    store.record("provedor-x", "wo-1", "traveling", from_status="assigned")
    store.record("provedor-x", "wo-1", "arrived", from_status="traveling")
    store.record("provedor-x", "wo-1", "completed", from_status="arrived")

    history = store.list_for_work_order("provedor-x", "wo-1")
    assert [entry["to_status"] for entry in history] == [
        "traveling", "arrived", "completed"
    ]


def test_new_work_order_prefills_location_from_confirmed_customer_location() -> None:
    from app.api.routes.work_orders import create_simulated_work_order
    from app.core.customer_location_store import customer_location_store

    customer_location_store.confirm(
        "g7-networks", "mk-customer-prefill-1", -12.4, -38.4,
    )
    result = asyncio.run(
        create_simulated_work_order(
            "Cliente Prefill",
            "Endereço qualquer",
            external_customer_id="mk-customer-prefill-1",
            organization_id="g7-networks",
        )
    )
    assert result.latitude == -12.4
    assert result.longitude == -38.4


def test_explicit_coordinates_are_not_overridden_by_confirmed_location() -> None:
    from app.api.routes.work_orders import create_simulated_work_order
    from app.core.customer_location_store import customer_location_store

    customer_location_store.confirm(
        "g7-networks", "mk-customer-prefill-2", -12.4, -38.4,
    )
    result = asyncio.run(
        create_simulated_work_order(
            "Cliente com coordenada manual",
            "Endereço qualquer",
            latitude=-13.0,
            longitude=-39.0,
            external_customer_id="mk-customer-prefill-2",
            organization_id="g7-networks",
        )
    )
    assert result.latitude == -13.0
    assert result.longitude == -39.0
