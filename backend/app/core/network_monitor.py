import asyncio

from app.api.routes.network import (
    create_network_incident,
    get_active_incident_by_kind,
    resolve_incidents_by_kind,
)
from app.core.integration_config_store import get_integration_settings
from app.core.network_metrics_store import network_metrics_store
from app.core.portal_customer_store import portal_customer_store
from app.core.whatsapp_orchestrator import send_whatsapp_message
from app.integrations.routeros.client import RouterOsReadOnlyClient

_BASELINE_WINDOW_MINUTES = 30
_MIN_BASELINE_SESSIONS = 3
_DROP_RATIO_THRESHOLD = 0.6
_RECOVERY_RATIO_THRESHOLD = 0.9


def _notify_affected_customers(organization_id: str, message: str) -> None:
    """Aviso em massa por falta de mapeamento geográfico (CTO/bairro) ainda
    não existir — quando o item de mapas FTTH for concluído, isso pode virar
    um aviso só para os clientes da área realmente afetada."""
    for customer in portal_customer_store.list_all(organization_id):
        phone = customer.get("phone")
        if not phone:
            continue
        send_whatsapp_message(
            organization_id,
            message,
            "network_incident_notice",
            phone=phone,
            login=customer.get("external_login"),
        )


async def check_network_health(organization_id: str) -> dict:
    """Consulta o MikroTik real deste provedor, registra a métrica no
    histórico e abre ou encerra incidentes automaticamente conforme o
    estado observado. Chamado periodicamente (ver main.py) para cada
    provedor com integração MikroTik real habilitada."""
    settings = get_integration_settings(organization_id)
    if settings.routeros_mode != "real" or not settings.routeros_username:
        return {"status": "skipped"}

    client = RouterOsReadOnlyClient(
        settings.routeros_host,
        settings.routeros_port,
        settings.routeros_username,
        settings.routeros_password,
    )
    try:
        diagnostic = await asyncio.to_thread(client.diagnose)
    except Exception:
        network_metrics_store.record(organization_id, router_reachable=False)
        if get_active_incident_by_kind(organization_id, "router_down") is None:
            create_network_incident(
                organization_id=organization_id,
                kind="router_down",
                severity="critical",
                title="Roteador MikroTik indisponível",
                area="Infraestrutura geral",
                auto_detected=True,
            )
            _notify_affected_customers(
                organization_id,
                "Detectamos uma instabilidade na rede e já estamos trabalhando "
                "para normalizar o quanto antes.",
            )
        return {"status": "router_down"}

    resolve_incidents_by_kind(organization_id, "router_down")

    active_sessions = len(diagnostic.get("sessions", []))
    cpu_load_raw = str(diagnostic.get("router", {}).get("cpu_load", "")).rstrip("%")
    try:
        cpu_load = int(cpu_load_raw)
    except ValueError:
        cpu_load = None

    radius_entries = diagnostic.get("radius", [])
    enabled_radius = [item for item in radius_entries if not item.get("disabled")]
    radius_ok = bool(diagnostic.get("ppp_aaa", {}).get("use_radius")) and bool(enabled_radius)

    baseline = network_metrics_store.average_sessions(
        organization_id, window_minutes=_BASELINE_WINDOW_MINUTES
    )
    network_metrics_store.record(
        organization_id,
        router_reachable=True,
        active_sessions=active_sessions,
        cpu_load=cpu_load,
        radius_ok=radius_ok,
    )

    if not radius_ok:
        if get_active_incident_by_kind(organization_id, "radius_down") is None:
            create_network_incident(
                organization_id=organization_id,
                kind="radius_down",
                severity="warning",
                title="RADIUS sem resposta ou desabilitado no MikroTik",
                area="Autenticação PPPoE",
                auto_detected=True,
            )
    else:
        resolve_incidents_by_kind(organization_id, "radius_down")

    if (
        baseline is not None
        and baseline >= _MIN_BASELINE_SESSIONS
        and active_sessions <= baseline * _DROP_RATIO_THRESHOLD
    ):
        if get_active_incident_by_kind(organization_id, "disconnection_spike") is None:
            create_network_incident(
                organization_id=organization_id,
                kind="disconnection_spike",
                severity="warning",
                title="Aumento anormal de desconexões PPPoE",
                area="Clientes conectados",
                auto_detected=True,
            )
            _notify_affected_customers(
                organization_id,
                "Notamos quedas de conexão acima do normal na sua região. "
                "Nossa equipe já está verificando.",
            )
    elif baseline is not None and active_sessions >= baseline * _RECOVERY_RATIO_THRESHOLD:
        resolve_incidents_by_kind(organization_id, "disconnection_spike")

    return {
        "status": "ok",
        "active_sessions": active_sessions,
        "cpu_load": cpu_load,
        "radius_ok": radius_ok,
    }
