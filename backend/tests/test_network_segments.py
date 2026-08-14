import pytest
from fastapi.testclient import TestClient

from app.core.network_segment_store import NetworkSegmentStore
from app.main import app

client = TestClient(app)


def test_segment_between_two_ctos(tmp_path) -> None:
    store = NetworkSegmentStore(f"sqlite:///{tmp_path / 'segments.db'}")
    segment = store.create(
        "provedor-um",
        {"cto_id": "cto-a", "latitude": -12.25, "longitude": -38.95},
        {"cto_id": "cto-b", "latitude": -12.26, "longitude": -38.96},
        "distribuicao",
        4,
        None,
    )
    assert segment["from_cto_id"] == "cto-a"
    assert segment["to_cto_id"] == "cto-b"
    assert segment["cable_type"] == "distribuicao"
    assert segment["fiber_count"] == 4

    active = store.list_active("provedor-um")
    assert len(active) == 1
    assert active[0]["id"] == segment["id"]


def test_segment_with_a_free_point_like_a_pop(tmp_path) -> None:
    store = NetworkSegmentStore(f"sqlite:///{tmp_path / 'segments.db'}")
    segment = store.create(
        "provedor-um",
        {"label": "POP Centro", "latitude": -12.24, "longitude": -38.94},
        {"cto_id": "cto-a", "latitude": -12.25, "longitude": -38.95},
        "backbone",
        12,
        "Rota principal",
    )
    assert segment["from_cto_id"] is None
    assert segment["from_label"] == "POP Centro"
    assert segment["to_cto_id"] == "cto-a"
    assert segment["notes"] == "Rota principal"


def test_segment_rejects_invalid_cable_type(tmp_path) -> None:
    store = NetworkSegmentStore(f"sqlite:///{tmp_path / 'segments.db'}")
    with pytest.raises(ValueError):
        store.create(
            "provedor-um",
            {"label": "A", "latitude": 0, "longitude": 0},
            {"label": "B", "latitude": 1, "longitude": 1},
            "tipo-invalido",
            None,
            None,
        )


def test_deactivated_segment_no_longer_appears_in_active_list(tmp_path) -> None:
    store = NetworkSegmentStore(f"sqlite:///{tmp_path / 'segments.db'}")
    segment = store.create(
        "provedor-um",
        {"label": "A", "latitude": 0, "longitude": 0},
        {"label": "B", "latitude": 1, "longitude": 1},
        "drop",
        None,
        None,
    )
    store.deactivate("provedor-um", segment["id"])
    assert store.list_active("provedor-um") == []


def test_deactivating_a_missing_segment_raises(tmp_path) -> None:
    store = NetworkSegmentStore(f"sqlite:///{tmp_path / 'segments.db'}")
    with pytest.raises(KeyError):
        store.deactivate("provedor-um", "segment-que-nao-existe")


def test_segments_are_isolated_by_organization(tmp_path) -> None:
    store = NetworkSegmentStore(f"sqlite:///{tmp_path / 'segments.db'}")
    store.create(
        "provedor-um",
        {"label": "A", "latitude": 0, "longitude": 0},
        {"label": "B", "latitude": 1, "longitude": 1},
        "drop",
        None,
        None,
    )
    assert store.list_active("provedor-dois") == []


def test_central_can_create_a_segment_between_two_real_ctos() -> None:
    admin_client = TestClient(app)
    admin_client.post(
        "/central/login", data={"username": "admin", "password": "Bancada@2026"}
    )
    cto_a = admin_client.post(
        "/central/ftth/ctos",
        data={
            "code": "CTO-SEG-A", "latitude": "-12.25", "longitude": "-38.95",
            "total_ports": "8", "splitter_ratio": "1:8",
        },
        follow_redirects=False,
    )
    assert cto_a.status_code == 303
    cto_b = admin_client.post(
        "/central/ftth/ctos",
        data={
            "code": "CTO-SEG-B", "latitude": "-12.26", "longitude": "-38.96",
            "total_ports": "8", "splitter_ratio": "1:8",
        },
        follow_redirects=False,
    )
    assert cto_b.status_code == 303

    dashboard = admin_client.get("/central")
    from app.core.cto_store import cto_store

    ctos = {
        item["code"]: item["id"]
        for item in cto_store.list_active("g7-networks")
    }
    assert "CTO-SEG-A" in ctos and "CTO-SEG-B" in ctos

    created = admin_client.post(
        "/central/ftth/segmentos",
        data={
            "from_cto_id": ctos["CTO-SEG-A"],
            "to_cto_id": ctos["CTO-SEG-B"],
            "cable_type": "distribuicao",
            "fiber_count": "6",
        },
        follow_redirects=False,
    )
    assert created.status_code == 303

    from app.core.network_segment_store import network_segment_store

    segments = network_segment_store.list_active("g7-networks")
    assert any(
        s["from_cto_id"] == ctos["CTO-SEG-A"] and s["to_cto_id"] == ctos["CTO-SEG-B"]
        for s in segments
    )

    updated_dashboard = admin_client.get("/central")
    assert "CTO-SEG-A" in updated_dashboard.text
    assert '"cable_type": "distribuicao"' in updated_dashboard.text


def test_central_can_create_a_segment_to_a_free_point_pop() -> None:
    admin_client = TestClient(app)
    admin_client.post(
        "/central/login", data={"username": "admin", "password": "Bancada@2026"}
    )
    cto = admin_client.post(
        "/central/ftth/ctos",
        data={
            "code": "CTO-SEG-POP", "latitude": "-12.27", "longitude": "-38.97",
            "total_ports": "8", "splitter_ratio": "1:8",
        },
        follow_redirects=False,
    )
    assert cto.status_code == 303

    from app.core.cto_store import cto_store

    cto_id = next(
        item["id"] for item in cto_store.list_active("g7-networks")
        if item["code"] == "CTO-SEG-POP"
    )

    created = admin_client.post(
        "/central/ftth/segmentos",
        data={
            "from_label": "POP Teste",
            "from_latitude": "-12.24",
            "from_longitude": "-38.94",
            "to_cto_id": cto_id,
            "cable_type": "backbone",
        },
        follow_redirects=False,
    )
    assert created.status_code == 303

    from app.core.network_segment_store import network_segment_store

    segments = network_segment_store.list_active("g7-networks")
    match = next(s for s in segments if s["to_cto_id"] == cto_id)
    assert match["from_label"] == "POP Teste"
    assert match["from_cto_id"] is None


def test_central_can_deactivate_a_segment() -> None:
    from app.core.network_segment_store import network_segment_store

    admin_client = TestClient(app)
    admin_client.post(
        "/central/login", data={"username": "admin", "password": "Bancada@2026"}
    )
    segment = network_segment_store.create(
        "g7-networks",
        {"label": "A", "latitude": 0, "longitude": 0},
        {"label": "B", "latitude": 1, "longitude": 1},
        "drop",
        None,
        None,
    )
    response = admin_client.post(
        f"/central/ftth/segmentos/{segment['id']}/desativar", follow_redirects=False
    )
    assert response.status_code == 303
    remaining = [
        s for s in network_segment_store.list_active("g7-networks")
        if s["id"] == segment["id"]
    ]
    assert remaining == []
