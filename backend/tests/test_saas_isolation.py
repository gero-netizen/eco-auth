import asyncio
import sqlite3
from uuid import uuid4

from app.core.organization_store import OrganizationStore
from app.core.technician_store import TechnicianStore
from app.domain.models import WorkOrderStatus
from app.integrations.mkauth.client import SimulatedMkAuthGateway
from app.core.integration_config_store import (
    IntegrationConfigStore,
    TenantIntegrationSettings,
)
from app.core.central_user_store import CentralUserStore
from app.core.audit_store import AuditStore
from app.core.subscription_store import SubscriptionStore
from app.core.config import get_settings
from app.integrations.mkauth.inventory import SimulatedInventoryGateway
from app.core.sync_store import SyncOperationStore
from app.domain.models import OperationResult


def test_technicians_are_isolated_by_organization(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'saas-isolation.db'}"
    organizations = OrganizationStore(database_url)
    technicians = TechnicianStore(database_url)

    first = organizations.create("Provedor Um", "provedor-um")
    second = organizations.create("Provedor Dois", "provedor-dois")

    first_technician = technicians.create(
        "Técnico Um", "campo", "Senha@123", first["id"]
    )
    second_technician = technicians.create(
        "Técnico Dois", "campo", "Senha@456", second["id"]
    )

    assert technicians.authenticate("campo", "Senha@123", first["id"])["id"] == first_technician["id"]
    assert technicians.authenticate("campo", "Senha@456", second["id"])["id"] == second_technician["id"]
    assert technicians.authenticate("campo", "Senha@456", first["id"]) is None
    assert [item["id"] for item in technicians.list_all(first["id"])] == [
        first_technician["id"]
    ]
    assert [item["id"] for item in technicians.list_all(second["id"])] == [
        second_technician["id"]
    ]


def test_organization_can_be_deactivated_without_affecting_another(tmp_path) -> None:
    organizations = OrganizationStore(f"sqlite:///{tmp_path / 'organizations.db'}")
    first = organizations.create("Provedor Um", "provedor-um")
    second = organizations.create("Provedor Dois", "provedor-dois")

    organizations.set_active(first["id"], False)

    assert organizations.get_active(first["id"]) is None
    assert organizations.get(first["id"])["active"] == 0
    assert organizations.get_active(second["id"])["id"] == second["id"]


def test_inventory_is_isolated_by_organization(tmp_path) -> None:
    gateway = SimulatedInventoryGateway(f"sqlite:///{tmp_path / 'inventory.db'}")
    default_id = get_settings().default_organization_id

    default_items = asyncio.run(gateway.list_items("tech-1", default_id))
    other_items = asyncio.run(gateway.list_items("tech-2", "provedor-dois"))

    assert len(default_items) == 3
    assert other_items == []
    before = next(item for item in default_items if item.id == "fast-connector")
    asyncio.run(
        gateway.consume(
            "fast-connector", 1, before.version, organization_id=default_id
        )
    )
    assert asyncio.run(gateway.list_items("tech-2", "provedor-dois")) == []


def test_mobile_sync_journal_is_isolated_by_organization(tmp_path) -> None:
    store = SyncOperationStore(f"sqlite:///{tmp_path / 'sync-isolation.db'}")
    operation_id = uuid4()
    result = OperationResult(
        operation_id=operation_id, status="accepted", server_version=1
    )
    change = {
        "entity_type": "inventory_item",
        "entity_id": "item-1",
        "kind": "upsert",
        "payload": {"id": "item-1"},
    }
    store.save(result, change, "provedor-um")

    assert store.get(str(operation_id), "provedor-um") is not None
    assert store.get(str(operation_id), "provedor-dois") is None
    assert len(store.changes_after(0, organization_id="provedor-um")[0]) == 1
    assert store.changes_after(0, organization_id="provedor-dois")[0] == []


def test_work_orders_are_isolated_by_organization(tmp_path) -> None:
    asyncio.run(_assert_work_order_isolation(tmp_path))


async def _assert_work_order_isolation(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'saas-orders.db'}"
    gateway = SimulatedMkAuthGateway(database_url)

    first_order = await gateway.create_work_order(
        "Cliente Provedor Um",
        "Rua Um, 10",
        organization_id="provedor-um",
    )
    second_order = await gateway.create_work_order(
        "Cliente Provedor Dois",
        "Rua Dois, 20",
        organization_id="provedor-dois",
    )

    first_orders = await gateway.list_work_orders(None, "provedor-um")
    second_orders = await gateway.list_work_orders(None, "provedor-dois")

    assert [order.id for order in first_orders] == [first_order.id]
    assert [order.id for order in second_orders] == [second_order.id]

    try:
        await gateway.transition_work_order(
            first_order.id,
            WorkOrderStatus.TRAVELING,
            first_order.version,
            "provedor-dois",
        )
    except KeyError as error:
        assert error.args[0] == "work_order_not_found"
    else:
        raise AssertionError("cross-organization work order access was allowed")


def test_integration_credentials_are_encrypted_and_isolated(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'saas-integrations.db'}"
    store = IntegrationConfigStore(database_url)
    first = TenantIntegrationSettings(
        app_env="development",
        mkauth_mode="real",
        mkauth_base_url="https://mkauth.provedor-um.test",
        mkauth_client_id="cliente-um",
        mkauth_client_secret="segredo-um",
        mkauth_verify_ssl=True,
        mkauth_allow_http=False,
        mkauth_writes_enabled=False,
        routeros_mode="real",
        routeros_host="10.0.0.1",
        routeros_port=8728,
        routeros_username="api-um",
        routeros_password="senha-um",
    )
    second = TenantIntegrationSettings(
        **{
            **first.__dict__,
            "mkauth_base_url": "https://mkauth.provedor-dois.test",
            "mkauth_client_id": "cliente-dois",
            "mkauth_client_secret": "segredo-dois",
            "routeros_host": "10.0.0.2",
            "routeros_username": "api-dois",
            "routeros_password": "senha-dois",
        }
    )

    store.save("provedor-um", first)
    store.save("provedor-dois", second)

    assert store.get("provedor-um").mkauth_client_id == "cliente-um"
    assert store.get("provedor-dois").routeros_host == "10.0.0.2"
    with sqlite3.connect(tmp_path / "saas-integrations.db") as connection:
        stored = connection.execute(
            """
            SELECT mkauth_client_secret_encrypted, routeros_password_encrypted
            FROM organization_integrations WHERE organization_id = ?
            """,
            ("provedor-um",),
        ).fetchone()
    assert "segredo-um" not in stored[0]
    assert "senha-um" not in stored[1]


def test_new_organization_integrations_never_inherit_default_credentials(tmp_path) -> None:
    store = IntegrationConfigStore(f"sqlite:///{tmp_path / 'new-tenant-integrations.db'}")
    store.ensure_unconfigured("provedor-novo")
    current = store.get("provedor-novo")

    assert current.mkauth_mode == "simulated"
    assert current.mkauth_client_id == ""
    assert current.mkauth_client_secret == ""
    assert current.mkauth_writes_enabled is False
    assert current.routeros_mode == "simulated"
    assert current.routeros_username == ""
    assert current.routeros_password == ""


def test_central_users_are_isolated_by_organization(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'saas-central-users.db'}"
    users = CentralUserStore(database_url)
    first = users.create(
        "provedor-um", "Atendente Um", "atendimento", "Senha@123", "attendant"
    )
    second = users.create(
        "provedor-dois", "Atendente Dois", "atendimento", "Senha@456", "viewer"
    )

    assert users.authenticate("provedor-um", "atendimento", "Senha@123")["id"] == first["id"]
    assert users.authenticate("provedor-dois", "atendimento", "Senha@456")["id"] == second["id"]
    assert users.authenticate("provedor-um", "atendimento", "Senha@456") is None
    assert [item["id"] for item in users.list_all("provedor-um")] == [first["id"]]


def test_audit_events_are_isolated_by_organization(tmp_path) -> None:
    store = AuditStore(f"sqlite:///{tmp_path / 'saas-audit.db'}")
    first_user = {
        "id": "user-1", "name": "Atendente Um", "username": "atendente",
        "role": "attendant",
    }
    second_user = {
        "id": "user-2", "name": "Administrador Dois", "username": "admin",
        "role": "admin",
    }
    first = store.record("provedor-um", first_user, "POST", "/central/work-orders")
    second = store.record("provedor-dois", second_user, "POST", "/central/users")

    assert [item["id"] for item in store.list_recent("provedor-um")] == [first["id"]]
    assert [item["id"] for item in store.list_recent("provedor-dois")] == [second["id"]]
    assert store.get(second["id"], "provedor-um") is None


def test_subscriptions_and_limits_are_isolated_by_organization(tmp_path) -> None:
    store = SubscriptionStore(f"sqlite:///{tmp_path / 'saas-subscriptions.db'}")
    first = store.get_or_create("provedor-um")
    second = store.simulate_plan_change("provedor-dois", "starter")

    assert first["plan_code"] == "professional"
    assert second["plan_code"] == "starter"
    assert store.get_or_create("provedor-um")["plan_code"] == "professional"
    store.ensure_capacity("provedor-dois", "central_users", 2)
    try:
        store.ensure_capacity("provedor-dois", "central_users", 3)
    except ValueError as error:
        assert str(error) == "saas_central_users_limit_reached"
    else:
        raise AssertionError("subscription user limit was not enforced")
