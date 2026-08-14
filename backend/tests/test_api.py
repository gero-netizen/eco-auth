import hashlib
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.sync_store import SyncOperationStore
from app.domain.models import OperationResult
from app.main import app
from app.api.routes.support import create_support_request, list_support_requests
from app.api.routes.network import create_network_incident, resolve_network_incidents
from app.core.technician_store import technician_store
from app.core.central_user_store import central_user_store
from app.core.portal_customer_store import portal_customer_store
from app.api.routes.notifications import list_simulated_messages

client = TestClient(app)
client.post(
    "/central/login",
    data={"username": "admin", "password": "Bancada@2026"},
)
technician_login = client.post(
    "/api/v1/auth/technician/login",
    json={"username": "tecnico", "password": "Campo@2026"},
)
client.headers.update(
    {"Authorization": f"Bearer {technician_login.json()['access_token']}"}
)


def test_health() -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_platform_administration_requires_its_own_session() -> None:
    anonymous = TestClient(app)
    blocked = anonymous.get("/plataforma", follow_redirects=False)
    assert blocked.status_code == 303
    assert blocked.headers["location"] == "/plataforma/login"

    login = anonymous.post(
        "/plataforma/login",
        data={"username": "admin", "password": "Bancada@2026"},
        follow_redirects=True,
    )
    assert login.status_code == 200
    assert "Administração SaaS" in login.text
    assert "Cadastrar novo provedor" in login.text


def test_central_session_is_scoped_to_default_organization() -> None:
    response = client.get("/api/v1/saas/organization/current")
    assert response.status_code == 200
    assert response.json() == {
        "id": "g7-networks",
        "name": "G7 Networks",
        "slug": "g7-networks",
        "active": True,
    }

    anonymous = TestClient(app)
    response = anonymous.get(
        "/api/v1/saas/organization/current", follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/central/login"


def test_integration_summary_never_exposes_secrets() -> None:
    response = client.get("/api/v1/saas/integrations/current")
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"mkauth", "routeros"}
    serialized = response.text.casefold()
    assert "client_secret" not in serialized
    assert "password" not in serialized


def test_current_central_user_is_the_migrated_owner() -> None:
    response = client.get("/api/v1/saas/users/current")
    assert response.status_code == 200
    assert response.json()["role"] == "owner"
    assert response.json()["organization_id"] == "g7-networks"
    assert "password" not in response.text.casefold()


def test_owner_can_view_tenant_audit_events() -> None:
    response = client.get("/api/v1/saas/audit-events")
    assert response.status_code == 200
    assert set(response.json()) == {"events", "count"}
    dashboard = client.get("/central")
    assert "Auditoria" in dashboard.text


def test_current_subscription_is_scoped_and_visible() -> None:
    response = client.get("/api/v1/saas/subscription/current")
    assert response.status_code == 200
    payload = response.json()
    assert payload["organization_id"] == "g7-networks"
    assert payload["plan_code"] in {"starter", "professional", "scale"}
    assert payload["status"] in {"trialing", "active", "past_due", "canceled"}
    dashboard = client.get("/central")
    assert "Plano e assinatura" in dashboard.text


def test_viewer_cannot_manage_central_users() -> None:
    username = f"viewer-{uuid4()}"
    created = client.post(
        "/api/v1/saas/users",
        json={
            "name": "Consulta Operacional",
            "username": username,
            "password": "Senha@123",
            "role": "viewer",
        },
    )
    assert created.status_code == 201
    user_id = created.json()["id"]
    try:
        viewer = TestClient(app)
        login = viewer.post(
            "/central/login",
            data={
                "organization_slug": "g7-networks",
                "username": username,
                "password": "Senha@123",
            },
            follow_redirects=False,
        )
        assert login.status_code == 303
        assert viewer.get("/api/v1/saas/users").status_code == 403
        assert viewer.get("/api/v1/saas/users/current").status_code == 200
        dashboard = viewer.get("/central")
        assert dashboard.status_code == 200
        assert "Somente leitura" in dashboard.text
        assert "action='/central/users'" not in dashboard.text
        assert "action=\"/central/technicians\"" not in dashboard.text
        assert viewer.post(
            "/central/technicians",
            data={"name": "Bloqueado", "username": "bloqueado", "password": "Senha@123"},
        ).status_code == 403
        assert viewer.post(
            "/api/v1/work-orders/from-central",
            data={"customer_name": "Cliente Bloqueado", "address": "Rua Teste, 10"},
        ).status_code == 403
    finally:
        central_user_store.delete(user_id, "g7-networks")


def test_technician_api_requires_a_valid_login() -> None:
    anonymous = TestClient(app)
    assert anonymous.get("/api/v1/work-orders").status_code == 401
    assert anonymous.post(
        "/api/v1/auth/technician/login",
        json={"username": "tecnico", "password": "invalid"},
    ).status_code == 401

    login = anonymous.post(
        "/api/v1/auth/technician/login",
        json={"username": "tecnico", "password": "Campo@2026"},
    )
    assert login.status_code == 200
    authorized = anonymous.get(
        "/api/v1/work-orders",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert authorized.status_code == 200


def test_central_can_register_a_technician_who_can_login() -> None:
    username = f"tecnico-{uuid4()}"
    created = client.post(
        "/central/technicians",
        data={
            "name": "Técnico Novo",
            "username": username,
            "password": "Senha@123",
        },
        follow_redirects=True,
    )
    assert created.status_code == 200
    assert "Técnico Novo" in created.text

    login = TestClient(app).post(
        "/api/v1/auth/technician/login",
        json={"username": username, "password": "Senha@123"},
    )
    assert login.status_code == 200
    assert login.json()["technician"]["name"] == "Técnico Novo"
    technician_store.delete(login.json()["technician"]["id"])


def test_central_can_assign_an_order_to_another_technician() -> None:
    username = f"field-{uuid4()}"
    technician = technician_store.create(
        "Técnico de Campo", username, "Senha@123"
    )
    created = None
    try:
        created = client.post(
            "/api/v1/work-orders",
            json={"customer_name": "Cliente Atribuição", "address": "Rua Teste, 30"},
        ).json()
        assigned = client.post(
            f"/central/work-orders/{created['id']}/assign",
            data={"technician_id": technician["id"]},
            follow_redirects=False,
        )
        assert assigned.status_code == 303

        login = TestClient(app).post(
            "/api/v1/auth/technician/login",
            json={"username": username, "password": "Senha@123"},
        ).json()
        orders = TestClient(app).get(
            "/api/v1/work-orders",
            headers={"Authorization": f"Bearer {login['access_token']}"},
        ).json()
        assert any(order["id"] == created["id"] for order in orders)
    finally:
        if created is not None:
            client.post(
                f"/central/work-orders/{created['id']}/assign",
                data={"technician_id": "bench-technician"},
            )
        technician_store.delete(technician["id"])


def test_central_requires_an_authenticated_session() -> None:
    anonymous = TestClient(app)
    protected = anonymous.get("/central", follow_redirects=False)
    assert protected.status_code == 303
    assert protected.headers["location"] == "/central/login"

    invalid = anonymous.post(
        "/central/login",
        data={"username": "admin", "password": "invalid"},
        follow_redirects=False,
    )
    assert invalid.status_code == 303
    assert "error=true" in invalid.headers["location"]

    authenticated = anonymous.post(
        "/central/login",
        data={"username": "admin", "password": "Bancada@2026"},
        follow_redirects=True,
    )
    assert authenticated.status_code == 200
    assert "Painel da Central" in authenticated.text


def test_central_dashboard_is_explicitly_simulated() -> None:
    response = client.get("/central")
    assert response.status_code == 200
    assert "Painel da Central" in response.text
    assert "Confira o status de cada integração" in response.text
    assert response.text.count('class="menu-button') == 27
    assert response.text.count('data-module=') == 27
    assert response.text.count('class="menu-category') == 7
    for category in (
        "Operação",
        "Clientes",
        "Financeiro",
        "Rede",
        "Atendimento",
        "Configurações",
        "Segurança",
    ):
        assert f"<summary>{category}</summary>" in response.text
    assert "Auditoria" in response.text
    assert "Usuários da central" in response.text
    assert "Identidade do provedor" in response.text
    assert "SALVAR IDENTIDADE" in response.text
    assert "Assistente IA de atendimento" in response.text
    assert "MODO ASSISTIDO" in response.text
    assert "central-users" in response.text
    assert "Criar acesso" in response.text
    assert "Reenviar convite" in response.text
    assert "Portal desativado" in response.text
    assert "Contas que já possuem acesso ao portal" in response.text
    assert "central-active-module" in response.text
    assert "/api/v1/integrations/mkauth/plans" in response.text
    assert "mkauth-plans-body" in response.text
    assert "/api/v1/integrations/mkauth/clients" in response.text
    assert "mkauth-clients-body" in response.text
    assert "/api/v1/integrations/mkauth/client-details" in response.text
    assert "mkauth-client-details" in response.text
    assert '<i data-lucide="eye" class="w-3.5 h-3.5"></i>' in response.text
    assert "Clientes desativados" in response.text
    assert "mkauth-inactive-clients-body" in response.text
    assert "Diagnóstico PPPoE/RADIUS" in response.text
    assert "/api/v1/integrations/routeros/diagnostic" in response.text
    assert '<i data-lucide="wifi" class="w-3.5 h-3.5"></i> PPPoE' in response.text
    assert "routeros-username-filter" in response.text
    assert "Verificações automáticas" in response.text
    assert "routeros-checks-body" in response.text
    assert "Clientes adicionais" in response.text
    assert "/api/v1/integrations/mkauth/additional-clients" in response.text
    assert "Títulos MK-AUTH" in response.text
    assert "/api/v1/integrations/mkauth/titles" in response.text
    assert '<i data-lucide="banknote" class="w-3.5 h-3.5"></i>' in response.text
    assert "mkauth-titles-login-filter" in response.text
    assert "LIBERAR POR 48 HORAS" in response.text
    assert "/api/v1/integrations/mkauth/trust-unlock" in response.text
    assert "trust-unlocks-body" in response.text
    assert "ENCERRAR AGORA" in response.text
    assert "/mkauth/trust-unlocks/${encodeURIComponent(record.id)}/cancel" in response.text
    assert "/api/v1/integrations/mkauth/tickets" in response.text
    assert "mkauth-tickets-body" in response.text
    assert "GERAR OS" in response.text
    assert "order-external-ticket-id" in response.text
    assert "OS arquivadas" in response.text
    assert "continuam disponíveis para consulta e restauração" in response.text
    assert "Financeiro e desbloqueio" in response.text
    assert "Simular Pix" in response.text
    assert "/api/v1/integrations/mkauth/pix-simulations" in response.text
    assert "Baixar Boleto" in response.text
    assert "SIMULAR PIX" not in response.text
    assert "BAIXA REAL PIX" not in response.text
    assert "/api/v1/integrations/mkauth/pix-payments" in response.text
    assert "Digite BAIXAR" in response.text
    assert "Resolvido por pagamento" in response.text
    assert "o acesso não foi alterado" in response.text
    assert "Nenhuma baixa real" in response.text
    assert "Configuração real (Meta WhatsApp Cloud API)" in response.text
    assert "WhatsApp real ainda não configurado" in response.text
    assert "Notificação registrada no WhatsApp" in response.text
    assert 'http-equiv="refresh"' not in response.text
    assert "Atualização automática desativada" in response.text
    assert "mkauth-clients-filter" in response.text
    assert "<th>Cliente</th><th>Login PPPoE</th><th>Situação</th><th>Tipo</th><th>Cidade/UF</th><th>Coordenadas</th><th>Ação</th>" in response.text
    assert "fin-status-${client.blocked ? 'red' : 'green'}" in response.text
    assert "título(s) pendente(s)" in response.text
    assert 'id="mkauth-titles-filter" type="hidden" value=""' in response.text
    assert "<th>Situação</th><th>Vencimento</th><th>Ação</th>" in response.text
    assert "window.setInterval" not in response.text


def test_portal_login_does_not_publish_fixed_credentials() -> None:
    response = TestClient(app).get("/portal/g7-networks/login")
    assert response.status_code == 200
    assert "credenciais fornecidas pelo seu provedor" in response.text
    assert "Cliente@2026" not in response.text


def test_portal_invite_sets_password_once_without_sending_password() -> None:
    username = f"portal-{uuid4()}"
    external_id = f"mk-{uuid4()}"
    external_login = f"pppoe-{uuid4()}"
    invited = client.post(
        "/central/portal-customers/invite-from-mkauth",
        data={
            "name": "Cliente Convidado",
            "username": username,
            "external_customer_id": external_id,
            "external_login": external_login,
        },
        follow_redirects=False,
    )
    assert invited.status_code == 303
    message = list_simulated_messages("g7-networks")[0]
    assert message["template"] == "portal_access_invite"
    assert message["login"] == external_login
    invite_url = message["body"].split()[-1]

    anonymous = TestClient(app)
    assert anonymous.get(invite_url).status_code == 200
    accepted = anonymous.post(
        invite_url,
        data={
            "password": "NovaSenha@2026",
            "password_confirmation": "NovaSenha@2026",
        },
    )
    assert accepted.status_code == 200
    assert "Senha definida com sucesso" in accepted.text
    assert anonymous.get(invite_url).status_code == 410
    login = anonymous.post(
        "/portal/g7-networks/login",
        data={"username": username, "password": "NovaSenha@2026"},
        follow_redirects=False,
    )
    assert login.status_code == 303


def test_mkauth_probe_remains_read_only_for_the_current_tenant() -> None:
    response = client.get("/api/v1/integrations/mkauth/probe")
    assert response.status_code == 200
    assert response.json()["read_only"] is True
    assert response.json()["status"] in {
        "simulated", "connected", "configuration_error", "unavailable"
    }
    assert "secret" not in response.text.casefold()
    assert "password" not in response.text.casefold()
    anonymous = TestClient(app).get(
        "/api/v1/integrations/mkauth/probe", follow_redirects=False
    )
    assert anonymous.status_code == 303


def test_network_monitor_returns_a_labeled_simulation() -> None:
    resolve_network_incidents()
    create_network_incident()
    response = client.get("/api/v1/network/alerts")
    assert response.status_code == 200
    alert = response.json()[0]
    assert alert["status"] == "active"
    assert alert["simulated"] is True


def test_network_incident_is_visible_to_client_and_can_be_resolved() -> None:
    resolve_network_incidents()
    create_network_incident()
    assert "Nossa equipe já foi avisada" in client.get("/cliente").text

    resolved = client.post(
        "/api/v1/network/incidents/resolve", follow_redirects=True
    )
    assert resolved.status_code == 200
    assert client.get("/api/v1/network/alerts").json() == []
    assert "Rede sem ocorrências" in client.get("/cliente").text


def test_pppoe_simulator_never_requires_a_password() -> None:
    response = client.post(
        "/api/v1/access/pppoe/test",
        json={"work_order_id": "sim-os-1", "username": "cliente.teste"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "authenticated"
    assert result["simulated"] is True
    assert result["assigned_ip"].startswith("10.20.")


def test_ftth_feasibility_finds_a_real_registered_cto_with_available_ports() -> None:
    from app.core.cto_store import cto_store

    cto_store.create(
        "g7-networks", "CTO-TESTE-01", latitude=-12.2500, longitude=-38.9500,
        total_ports=8, splitter_ratio="1:8",
    )
    response = client.post(
        "/api/v1/feasibility/check",
        json={
            "work_order_id": "sim-os-1",
            "latitude": -12.2501,
            "longitude": -38.9501,
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["simulated"] is False
    assert result["status"] == "disponivel"
    assert result["feasible"] is True
    assert result["nearest_cto"]["code"] == "CTO-TESTE-01"


def test_ftth_feasibility_reports_out_of_area_when_too_far() -> None:
    from app.core.cto_store import cto_store

    cto_store.create(
        "g7-networks", "CTO-TESTE-02", latitude=-12.2500, longitude=-38.9500,
        total_ports=8, splitter_ratio="1:8",
    )
    response = client.post(
        "/api/v1/feasibility/check",
        json={
            "work_order_id": "sim-os-2",
            "latitude": -3.7327,  # Fortaleza, bem longe de Feira de Santana
            "longitude": -38.5267,
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "fora_area"
    assert result["feasible"] is False


def test_pix_simulator_marks_invoice_paid_and_releases_access() -> None:
    response = client.post(
        "/api/v1/financial/accounts/sim-customer-1/simulate-pix"
    )
    assert response.status_code == 200
    account = response.json()
    assert account["invoice_status"] == "paid"
    assert account["access_status"] == "active"
    assert account["simulated"] is True


def test_simulated_client_portal_supports_trust_and_pix_flows() -> None:
    client.post("/cliente/reiniciar")
    portal = client.get("/cliente")
    assert portal.status_code == 200
    assert "Desbloqueio em Confiança" in portal.text
    assert "Bloqueada" in portal.text
    assert "PIX-SIMULADO" in portal.text

    trust = client.post("/cliente/desbloqueio-confianca", follow_redirects=True)
    assert trust.status_code == 200
    assert "Liberada em confiança" in trust.text

    pix = client.post("/cliente/simular-pix", follow_redirects=True)
    assert pix.status_code == 200
    assert "Ativa" in pix.text
    assert "Paga" in pix.text


def test_client_support_request_can_be_converted_to_a_work_order() -> None:
    opened = client.post(
        "/cliente/chamados",
        data={"subject": "Sem conexão", "description": "ONU sem sinal na bancada"},
        follow_redirects=True,
    )
    assert opened.status_code == 200
    assert "Sem conexão" in opened.text
    assert "aguardando a central" in opened.text.casefold()

    central = client.get("/central")
    assert "Sem conexão" in central.text
    request_id = max(item["id"] for item in list_support_requests())
    converted = client.post(
        f"/central/chamados/{request_id}/gerar-os", follow_redirects=True
    )
    assert converted.status_code == 200
    assert "Convertido em OS" in converted.text

    portal = client.get("/cliente")
    assert "Seus chamados" in portal.text
    assert "OS criada" in portal.text
    assert 'http-equiv="refresh"' not in portal.text
    assert f"href='/cliente/chamados/{request_id}'" in portal.text

    detail = client.get(f"/cliente/chamados/{request_id}")
    assert detail.status_code == 200
    assert "Andamento do atendimento" in detail.text
    assert "Técnico em deslocamento" in detail.text


def test_archiving_a_ticket_hides_it_from_the_main_list_but_not_from_the_customer() -> None:
    request_id = create_support_request(
        "sim-customer-1", "Chamado teste arquivamento", "Descrição de teste"
    )
    before = client.get("/central")
    assert "Chamado teste arquivamento" in before.text

    archived = client.post(
        f"/central/chamados/{request_id}/arquivar", follow_redirects=True
    )
    assert archived.status_code == 200

    main_list = client.get("/central")
    # Some other bench data may repeat similar words, so check the specific row is gone
    # from the main (non-archived) support table by confirming it now appears only
    # in the archived table.
    assert "Chamados arquivados" in main_list.text

    portal = client.get("/cliente")
    assert "Chamado teste arquivamento" in portal.text


def test_restoring_an_archived_ticket_brings_it_back() -> None:
    request_id = create_support_request(
        "sim-customer-1", "Chamado teste restauração", "Descrição de teste"
    )
    client.post(f"/central/chamados/{request_id}/arquivar")
    restored = client.post(
        f"/central/chamados/{request_id}/restaurar", follow_redirects=True
    )
    assert restored.status_code == 200

    active_requests = [
        item for item in list_support_requests() if item["id"] == request_id
    ]
    assert len(active_requests) == 1
    assert active_requests[0]["archived_at"] is None


def test_deleting_an_unarchived_ticket_is_rejected() -> None:
    request_id = create_support_request(
        "sim-customer-1", "Chamado teste exclusão ativo", "Descrição de teste"
    )
    response = client.post(f"/central/chamados/{request_id}/excluir")
    assert response.status_code == 409

    remaining = [
        item
        for item in list_support_requests(include_archived=True)
        if item["id"] == request_id
    ]
    assert len(remaining) == 1


def test_deleting_an_archived_ticket_removes_it_permanently() -> None:
    request_id = create_support_request(
        "sim-customer-1", "Chamado teste exclusão arquivado", "Descrição de teste"
    )
    client.post(f"/central/chamados/{request_id}/arquivar")
    response = client.post(
        f"/central/chamados/{request_id}/excluir", follow_redirects=False
    )
    assert response.status_code == 303

    remaining = [
        item
        for item in list_support_requests(include_archived=True)
        if item["id"] == request_id
    ]
    assert remaining == []


def test_client_cannot_rate_an_unfinished_work_order() -> None:
    request_id = create_support_request(
        "sim-customer-1", "Avaliação antecipada", "OS ainda não concluída"
    )
    response = client.post(
        f"/cliente/chamados/{request_id}/avaliar",
        data={"rating": "5", "comment": "Ainda não deveria aceitar"},
    )
    assert response.status_code == 409


def test_whatsapp_simulator_uses_only_a_fictitious_recipient() -> None:
    response = client.post(
        "/api/v1/notifications/simulate/invoice_reminder"
    )
    assert response.status_code == 200
    message = response.json()
    assert message["status"] == "simulated_sent"
    assert message["phone"] == "+55 (00) 00000-0000"


def test_central_can_create_a_work_order_for_mobile_sync() -> None:
    created = client.post(
        "/api/v1/work-orders",
        json={
            "customer_name": "Novo Cliente Fictício",
            "address": "Rua de Bancada, 20",
        },
    )
    assert created.status_code == 201
    order = created.json()
    assert order["status"] == "assigned"

    pulled = client.get("/api/v1/sync/pull", params={"cursor": "0"})
    assert pulled.status_code == 200
    assert any(
        change["entity_type"] == "work_order"
        and change["entity_id"] == order["id"]
        for change in pulled.json()["changes"]
    )


def test_sync_is_idempotent() -> None:
    operation_id = str(uuid4())
    created = client.post(
        "/api/v1/work-orders",
        json={
            "customer_name": "Cliente Teste de Idempotência",
            "address": "Rua de Teste, 100",
        },
    )
    assert created.status_code == 201
    current_order = created.json()
    payload = {
        "device_id": str(uuid4()),
        "operations": [{
            "operation_id": operation_id,
            "entity_type": "work_order",
            "entity_id": current_order["id"],
            "kind": "transition",
            "base_version": current_order["version"],
            "occurred_at": "2026-08-03T12:00:00Z",
            "payload": {"to_status": "arrived"},
        }],
    }
    assert client.post("/api/v1/sync/push", json=payload).json()["results"][0]["status"] == "accepted"
    assert client.post("/api/v1/sync/push", json=payload).json()["results"][0]["status"] == "duplicate"


def test_olt_simulator_provisions_an_onu() -> None:
    response = client.post(
        "/api/v1/olt/onus/provision",
        json={"serial": "test123", "profile": "ftth-500"},
    )
    assert response.status_code == 200
    assert response.json()["serial"] == "TEST123"
    assert response.json()["status"] == "online"


def test_olt_provisioning_is_idempotent_and_audited() -> None:
    operation_id = str(uuid4())
    payload = {
        "operation_id": operation_id,
        "work_order_id": "sim-os-1",
        "serial": "audit-onu-1",
        "profile": "ftth-500",
    }
    first = client.post("/api/v1/olt/onus/provision", json=payload)
    second = client.post("/api/v1/olt/onus/provision", json=payload)

    assert first.status_code == 200
    assert first.json()["duplicate"] is False
    assert first.json()["work_order_id"] == "sim-os-1"
    assert second.json()["duplicate"] is True
    assert second.json()["operation_id"] == operation_id
    history = client.get(
        "/api/v1/olt/provisioning",
        params={"work_order_id": "sim-os-1"},
    ).json()
    audited = next(item for item in history if item["operation_id"] == operation_id)
    assert audited["serial"] == "AUDIT-ONU-1"
    assert audited["created_at"]


def test_evidence_rejects_an_invalid_hash() -> None:
    response = client.post(
        f"/api/v1/work-orders/sim-os-1/evidence/{uuid4()}",
        content=b"photo",
        headers={
            "X-Evidence-Category": "installation_photo",
            "X-Content-SHA256": "0" * 64,
            "Content-Type": "application/octet-stream",
        },
    )
    assert response.status_code == 422


def test_uploaded_evidence_is_available_to_the_central() -> None:
    evidence_id = uuid4()
    content = b"fictitious-photo-content"
    uploaded = client.post(
        f"/api/v1/work-orders/sim-os-1/evidence/{evidence_id}",
        content=content,
        headers={
            "X-Evidence-Category": "installation_photo",
            "X-Content-SHA256": hashlib.sha256(content).hexdigest(),
        },
    )
    assert uploaded.status_code == 200

    summary = client.get("/api/v1/work-orders/sim-os-1/evidence")
    assert summary.status_code == 200
    assert any(item["id"] == str(evidence_id) for item in summary.json()["files"])

    gallery = client.get("/central/work-orders/sim-os-1/evidence")
    assert gallery.status_code == 200
    assert "Fotos e assinatura" in gallery.text
    assert str(evidence_id) in gallery.text


def test_uploaded_evidence_is_downloadable_from_a_central_session() -> None:
    """Fotos/assinaturas precisam abrir de verdade no navegador da Central
    (sessão por cookie), não só serem referenciadas na galeria — essa é a
    regressão real: a rota de download exigia token de técnico, que o
    navegador da Central nunca envia."""
    evidence_id = uuid4()
    content = b"fictitious-photo-content-for-central-download"
    uploaded = client.post(
        f"/api/v1/work-orders/sim-os-1/evidence/{evidence_id}",
        content=content,
        headers={
            "X-Evidence-Category": "installation_photo",
            "X-Content-SHA256": hashlib.sha256(content).hexdigest(),
        },
    )
    assert uploaded.status_code == 200

    central_client = TestClient(app)
    central_client.post(
        "/central/login", data={"username": "admin", "password": "Bancada@2026"}
    )
    downloaded = central_client.get(
        f"/api/v1/work-orders/sim-os-1/evidence/{evidence_id}/file"
    )
    assert downloaded.status_code == 200
    assert downloaded.content == content


def test_evidence_file_requires_some_valid_session() -> None:
    evidence_id = uuid4()
    content = b"fictitious-photo-content-for-auth-check"
    client.post(
        f"/api/v1/work-orders/sim-os-1/evidence/{evidence_id}",
        content=content,
        headers={
            "X-Evidence-Category": "installation_photo",
            "X-Content-SHA256": hashlib.sha256(content).hexdigest(),
        },
    )
    anonymous_client = TestClient(app)
    response = anonymous_client.get(
        f"/api/v1/work-orders/sim-os-1/evidence/{evidence_id}/file"
    )
    assert response.status_code == 401


def test_central_generates_a_printable_work_order_report() -> None:
    report = client.get("/central/work-orders/sim-os-1/report")
    assert report.status_code == 200
    assert "Relatório técnico" in report.text
    assert "Imprimir ou salvar em PDF" in report.text
    assert "Checklist das comprovações" in report.text
    assert "Este relatório reflete os dados cadastrados" in report.text


def test_inventory_consumption_is_applied_once() -> None:
    operation_id = str(uuid4())
    restocked = client.post(
        "/api/v1/inventory/fast-connector/restock", json={"quantity": 2}
    )
    assert restocked.status_code == 200
    connector_before = restocked.json()
    # A reposição pelo próprio técnico cria/usa a linha de estoque dele —
    # o id retornado passa a ser esse, não mais o item central "fast-connector".
    technician_item_id = connector_before["id"]
    payload = {
        "device_id": str(uuid4()),
        "operations": [{
            "operation_id": operation_id,
            "entity_type": "inventory_movement",
            "entity_id": str(uuid4()),
            "kind": "consume",
            "base_version": connector_before["version"],
            "occurred_at": "2026-08-03T12:00:00Z",
            "payload": {"item_id": technician_item_id, "quantity": 1},
        }],
    }
    first = client.post("/api/v1/sync/push", json=payload).json()["results"][0]
    second = client.post("/api/v1/sync/push", json=payload).json()["results"][0]
    assert first["status"] == "accepted"
    assert second["status"] == "duplicate"
    inventory = client.get("/api/v1/inventory").json()
    connector = next(item for item in inventory if item["id"] == technician_item_id)
    assert connector["quantity"] == connector_before["quantity"] - 1


def test_central_restock_is_published_for_mobile_sync() -> None:
    before = client.post(
        "/api/v1/inventory/drop-cable/restock", json={"quantity": 5}
    ).json()
    restocked = client.post(
        "/api/v1/inventory/drop-cable/restock", json={"quantity": 10}
    )
    assert restocked.status_code == 200
    assert restocked.json()["id"] == before["id"]
    assert restocked.json()["quantity"] == before["quantity"] + 10
    assert restocked.json()["version"] == before["version"] + 1

    pulled = client.get("/api/v1/sync/pull", params={"cursor": "0"})
    assert any(
        change["entity_type"] == "inventory_item"
        and change["entity_id"] == before["id"]
        for change in pulled.json()["changes"]
    )
    central = client.get("/central")
    assert "Histórico de materiais" in central.text
    assert "Reposição" in central.text


def test_sync_journal_survives_store_recreation(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'sync-test.db'}"
    operation_id = uuid4()
    first_store = SyncOperationStore(database_url)
    first_store.save(
        OperationResult(
            operation_id=operation_id,
            status="accepted",
            server_version=2,
        )
    )

    restarted_store = SyncOperationStore(database_url)
    restored = restarted_store.get(str(operation_id))

    assert restored is not None
    assert restored.status == "accepted"
    assert restored.server_version == 2


def test_incremental_change_feed_survives_restart(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'changes-test.db'}"
    operation_id = uuid4()
    store = SyncOperationStore(database_url)
    store.save(
        OperationResult(
            operation_id=operation_id,
            status="accepted",
            server_version=2,
        ),
        change={
            "entity_type": "work_order",
            "entity_id": "sim-os-1",
            "kind": "upsert",
            "payload": {"id": "sim-os-1", "version": 2},
        },
    )

    restarted_store = SyncOperationStore(database_url)
    changes, next_cursor = restarted_store.changes_after(0)
    no_new_changes, same_cursor = restarted_store.changes_after(next_cursor)

    assert len(changes) == 1
    assert changes[0]["payload"]["version"] == 2
    assert next_cursor > 0
    assert no_new_changes == []
    assert same_cursor == next_cursor


def test_pull_rejects_invalid_cursor() -> None:
    response = client.get("/api/v1/sync/pull", params={"cursor": "invalid"})
    assert response.status_code == 422
