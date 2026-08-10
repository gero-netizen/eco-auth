import asyncio
import sqlite3

from app.core.organization_store import OrganizationStore
from app.core.technician_store import TechnicianStore
from app.domain.models import WorkOrderStatus
from app.integrations.mkauth.client import SimulatedMkAuthGateway
from app.core.integration_config_store import (
    IntegrationConfigStore,
    TenantIntegrationSettings,
)
from app.core.central_user_store import CentralUserStore


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
