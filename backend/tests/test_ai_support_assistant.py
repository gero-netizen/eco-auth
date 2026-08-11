from app.api.routes.support import list_support_requests
from app.core.ai_support_store import ai_support_store
from app.core.audit_store import audit_store
from app.main import app
from fastapi.testclient import TestClient

ORG_ID = "g7-networks"


def _central_client() -> TestClient:
    client = TestClient(app)
    login = client.post(
        "/central/login",
        data={"username": "admin", "password": "Bancada@2026"},
    )
    assert login.status_code in (200, 303)
    return client


def _latest_ticket_id() -> int:
    tickets = list_support_requests(customer_id="sim-customer-1", organization_id=ORG_ID)
    return tickets[0]["id"]


def test_ticket_creation_prepares_a_draft_automatically() -> None:
    client = _central_client()
    client.post(
        "/cliente/chamados",
        data={
            "subject": "Sem conexão desde ontem",
            "description": "O roteador está com todas as luzes apagadas.",
        },
    )
    ticket_id = _latest_ticket_id()

    draft = ai_support_store.get_draft_for_request(ORG_ID, str(ticket_id))
    assert draft is not None
    assert draft["status"] == "pending"
    assert draft["support_request_id"] == str(ticket_id)


def test_low_confidence_draft_cannot_be_approved_without_editing() -> None:
    client = _central_client()
    client.post(
        "/cliente/chamados",
        data={
            "subject": "Pergunta muito fora do comum e específica",
            "description": "Um problema nunca antes catalogado em nenhuma base de conhecimento.",
        },
    )
    ticket_id = _latest_ticket_id()
    draft = ai_support_store.get_draft_for_request(ORG_ID, str(ticket_id))
    assert draft["confidence"] == "low"

    blocked = client.post(
        f"/central/chamados/{ticket_id}/ia/aprovar",
        data={"edited_answer": ""},
    )
    assert blocked.status_code == 422

    ticket = next(
        item
        for item in list_support_requests(customer_id="sim-customer-1", organization_id=ORG_ID)
        if item["id"] == ticket_id
    )
    assert ticket["response"] is None


def test_approving_a_draft_answers_the_ticket_and_records_audit() -> None:
    ai_support_store.create_knowledge(
        ORG_ID,
        "Lentidão no Wi-Fi",
        "Reposicione o roteador longe de paredes e eletrodomésticos.",
        category="lentidao",
    )
    client = _central_client()
    client.post(
        "/cliente/chamados",
        data={
            "subject": "Internet lenta no Wi-Fi",
            "description": "A lentidão no wifi começou essa semana em casa toda.",
        },
    )
    ticket_id = _latest_ticket_id()
    draft_before = ai_support_store.get_draft_for_request(ORG_ID, str(ticket_id))
    assert draft_before["confidence"] in {"medium", "high"}

    approved = client.post(
        f"/central/chamados/{ticket_id}/ia/aprovar",
        data={"edited_answer": "Reposicione o roteador e teste novamente, por favor."},
    )
    assert approved.status_code in (200, 303)

    ticket = next(
        item
        for item in list_support_requests(customer_id="sim-customer-1", organization_id=ORG_ID)
        if item["id"] == ticket_id
    )
    assert ticket["status"] == "answered"
    assert ticket["response"] == "Reposicione o roteador e teste novamente, por favor."

    draft_after = ai_support_store.get_draft_for_request(ORG_ID, str(ticket_id))
    assert draft_after["status"] == "approved"

    events = audit_store.list_recent(ORG_ID, limit=5)
    assert any(event["action"] == "ai_draft_approved" for event in events)

    # A resposta aprovada deve aparecer para o cliente no portal.
    portal_page = client.get(f"/cliente/chamados/{ticket_id}")
    assert "Reposicione o roteador e teste novamente" in portal_page.text


def test_rejecting_a_draft_leaves_the_ticket_open_for_manual_handling() -> None:
    client = _central_client()
    client.post(
        "/cliente/chamados",
        data={
            "subject": "Cobrança indevida na fatura",
            "description": "Fui cobrado duas vezes no mesmo mês por engano.",
        },
    )
    ticket_id = _latest_ticket_id()

    rejected = client.post(f"/central/chamados/{ticket_id}/ia/rejeitar")
    assert rejected.status_code in (200, 303)

    ticket = next(
        item
        for item in list_support_requests(customer_id="sim-customer-1", organization_id=ORG_ID)
        if item["id"] == ticket_id
    )
    assert ticket["response"] is None
    assert ticket["status"] != "answered"

    draft = ai_support_store.get_draft_for_request(ORG_ID, str(ticket_id))
    assert draft["status"] == "rejected"

    events = audit_store.list_recent(ORG_ID, limit=5)
    assert any(event["action"] == "ai_draft_rejected" for event in events)


def test_forwarding_a_draft_tags_the_ticket_without_answering_it() -> None:
    client = _central_client()
    client.post(
        "/cliente/chamados",
        data={
            "subject": "Preciso mudar o endereço da instalação",
            "description": "Vamos mudar de casa no próximo mês e preciso reagendar.",
        },
    )
    ticket_id = _latest_ticket_id()

    forwarded = client.post(
        f"/central/chamados/{ticket_id}/ia/encaminhar",
        data={"forwarded_to": "mudanca_endereco"},
    )
    assert forwarded.status_code in (200, 303)

    ticket = next(
        item
        for item in list_support_requests(customer_id="sim-customer-1", organization_id=ORG_ID)
        if item["id"] == ticket_id
    )
    assert ticket["response"] is None
    assert ticket["forwarded_to"] == "mudanca_endereco"

    draft = ai_support_store.get_draft_for_request(ORG_ID, str(ticket_id))
    assert draft["status"] == "forwarded"
    assert draft["forwarded_to"] == "mudanca_endereco"


def test_a_reviewed_draft_cannot_be_reviewed_twice() -> None:
    client = _central_client()
    client.post(
        "/cliente/chamados",
        data={
            "subject": "Preciso da segunda via do boleto",
            "description": "Não recebi o boleto deste mês por e-mail.",
        },
    )
    ticket_id = _latest_ticket_id()
    client.post(f"/central/chamados/{ticket_id}/ia/rejeitar")

    second_attempt = client.post(f"/central/chamados/{ticket_id}/ia/rejeitar")
    assert second_attempt.status_code == 422
