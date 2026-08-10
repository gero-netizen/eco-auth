from app.core.organization_store import OrganizationStore
from app.core.technician_store import TechnicianStore


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
