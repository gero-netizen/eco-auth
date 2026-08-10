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
from app.core.pix_simulation_store import PixSimulationStore
from app.core.trust_unlock_store import TrustUnlockStore
from app.api.routes.support import (
    create_support_request,
    list_support_requests,
    save_rating,
)
from app.domain.models import OperationResult
from app.api.routes.financial import list_financial_accounts
from app.api.routes.network import (
    create_network_incident,
    list_active_alerts,
    resolve_network_incidents,
)
from app.api.routes.notifications import (
    list_simulated_messages,
    record_simulated_payment_message,
    simulated_messages,
)
from app.core.tenant_context import set_current_organization


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


def test_financial_simulator_is_isolated_by_organization() -> None:
    default_id = get_settings().default_organization_id

    assert len(list_financial_accounts(default_id)) == 1
    assert list_financial_accounts("provedor-financeiro-vazio") == []


def test_network_alerts_are_isolated_by_organization() -> None:
    first_id = f"network-first-{uuid4()}"
    second_id = f"network-second-{uuid4()}"
    try:
        created = create_network_incident(organization_id=first_id)

        assert [item.id for item in list_active_alerts(first_id)] == [created.id]
        assert list_active_alerts(second_id) == []
    finally:
        resolve_network_incidents(first_id)
        resolve_network_incidents(second_id)


def test_simulated_notifications_are_isolated_by_organization() -> None:
    first_id = f"notifications-first-{uuid4()}"
    second_id = f"notifications-second-{uuid4()}"
    initial_count = len(simulated_messages)
    try:
        set_current_organization(first_id)
        created = record_simulated_payment_message("cliente-1", "100", "49.90", 0)

        assert [item["id"] for item in list_simulated_messages(first_id)] == [
            created["id"]
        ]
        assert list_simulated_messages(second_id) == []
    finally:
        del simulated_messages[initial_count:]
        set_current_organization(get_settings().default_organization_id)


def test_financial_histories_are_isolated_by_organization(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'financial-history.db'}"
    pix_store = PixSimulationStore(database_url)
    trust_store = TrustUnlockStore(database_url)
    try:
        set_current_organization("provedor-financeiro-um")
        pix = pix_store.create("title-uuid-1", "100", "cliente-1", "49.90")
        unlock = trust_store.create("client-uuid-1", "cliente-1", "Teste seguro")

        assert [item["id"] for item in pix_store.list_recent()] == [pix["id"]]
        assert [item["id"] for item in trust_store.list_recent()] == [unlock["id"]]

        set_current_organization("provedor-financeiro-dois")
        assert pix_store.list_recent() == []
        assert trust_store.list_recent() == []
        assert pix_store.has_real_payment("title-uuid-1") is False
        assert trust_store.get_active(unlock["id"]) is None
    finally:
        set_current_organization(get_settings().default_organization_id)


def test_support_requests_are_isolated_by_organization() -> None:
    first_id = f"support-first-{uuid4()}"
    second_id = f"support-second-{uuid4()}"
    first_request_id = create_support_request(
        "customer-1", "Sem conexão", "Teste do provedor um", first_id
    )
    second_request_id = create_support_request(
        "customer-1", "Sinal baixo", "Teste do provedor dois", second_id
    )
    database_path = get_settings().database_url.removeprefix("sqlite:///")
    try:
        assert [item["id"] for item in list_support_requests(
            organization_id=first_id
        )] == [first_request_id]
        assert [item["id"] for item in list_support_requests(
            organization_id=second_id
        )] == [second_request_id]
        try:
            save_rating(first_request_id, 5, "Ótimo", second_id)
        except Exception as error:
            assert getattr(error, "status_code", None) == 404
        else:
            raise AssertionError("cross-organization support access was allowed")
    finally:
        with sqlite3.connect(database_path) as connection:
            connection.execute(
                "DELETE FROM support_requests WHERE organization_id IN (?, ?)",
                (first_id, second_id),
            )
