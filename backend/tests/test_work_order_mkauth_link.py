import asyncio
from types import SimpleNamespace

import pytest

from app.integrations.mkauth import client as gateway_module


def test_created_work_order_keeps_mkauth_customer_uuid(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "linked-work-orders.db"
    monkeypatch.setattr(
        gateway_module,
        "get_settings",
        lambda: SimpleNamespace(
            database_url=f"sqlite:///{database_path}",
            default_organization_id="g7-networks",
        ),
    )
    gateway = gateway_module.SimulatedMkAuthGateway()

    created = asyncio.run(
        gateway.create_work_order(
            "Cliente MK-AUTH",
            "Rua da Bancada, 20",
            -12.9,
            -38.5,
            external_customer_id="customer-uuid-1",
            external_ticket_id="ticket-uuid-1",
        )
    )
    stored = asyncio.run(gateway.list_work_orders(None))
    recovered = next(item for item in stored if item.id == created.id)

    assert recovered.external_customer_id == "customer-uuid-1"
    assert recovered.external_ticket_id == "ticket-uuid-1"

    closed = asyncio.run(gateway.mark_external_ticket_closed(created.id))
    assert closed.external_ticket_closed_at is not None
    with pytest.raises(ValueError, match="external_ticket_already_closed"):
        asyncio.run(gateway.mark_external_ticket_closed(created.id))

    asyncio.run(
        gateway.transition_work_order(
            created.id, gateway_module.WorkOrderStatus.COMPLETED, None
        )
    )
    archived = asyncio.run(gateway.set_work_order_archived(created.id, True))
    assert archived.archived_at is not None
    restored = asyncio.run(gateway.set_work_order_archived(created.id, False))
    assert restored.archived_at is None

    removable = asyncio.run(
        gateway.create_work_order("Resolvido remoto", "Atendimento remoto")
    )
    deleted = asyncio.run(
        gateway.delete_unstarted_work_order(
            removable.id, "Resolvido remotamente sem visita"
        )
    )
    assert deleted.deleted_at is not None
    assert deleted.deletion_reason == "Resolvido remotamente sem visita"
    with pytest.raises(ValueError, match="work_order_already_deleted"):
        asyncio.run(
            gateway.delete_unstarted_work_order(removable.id, "Tentativa repetida")
        )
