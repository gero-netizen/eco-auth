import asyncio
from datetime import datetime, timedelta
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.api.routes.central_auth import require_central_session
from app.core.config import get_settings
from app.core.pix_simulation_store import PixSimulationStore
from app.core.trust_unlock_store import TrustUnlockStore
from app.api.routes.notifications import record_simulated_payment_message
from app.integrations.mkauth.api_client import MkAuthApiClient
from app.integrations.routeros.client import RouterOsReadOnlyClient

router = APIRouter(
    prefix="/integrations",
    tags=["integrations"],
    dependencies=[Depends(require_central_session)],
)


class TrustUnlockRequest(BaseModel):
    client_uuid: str = Field(min_length=8, max_length=80)
    login: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=5, max_length=250)
    confirmed: bool


class TrustUnlockCancelRequest(BaseModel):
    confirmed: bool


class PixSimulationRequest(BaseModel):
    title_uuid: str = Field(min_length=8, max_length=80)
    login: str = Field(min_length=1, max_length=64)
    confirmed: bool


class PixRealPaymentRequest(BaseModel):
    title_uuid: str = Field(min_length=8, max_length=80)
    login: str = Field(min_length=1, max_length=64)
    confirmation_text: str = Field(min_length=1, max_length=20)
    confirmed: bool


def _trust_unlock_store() -> TrustUnlockStore:
    return TrustUnlockStore(get_settings().database_url)


def _pix_simulation_store() -> PixSimulationStore:
    return PixSimulationStore(get_settings().database_url)


@router.post("/mkauth/pix-simulations")
async def create_mkauth_pix_simulation(request: PixSimulationRequest) -> dict:
    if not request.confirmed:
        return {"status": "confirmation_required"}
    settings = get_settings()
    if settings.mkauth_mode != "real":
        return {"status": "integration_unavailable"}
    try:
        client = MkAuthApiClient(
            settings.mkauth_base_url,
            settings.mkauth_client_id,
            settings.mkauth_client_secret,
            settings.mkauth_verify_ssl,
            settings.mkauth_allow_http and settings.app_env == "development",
        )
        titles = await client.list_titles()
        title = next(
            (
                item
                for item in titles
                if str(item.get("uuid") or "") == request.title_uuid
                and str(item.get("login") or "").casefold() == request.login.casefold()
            ),
            None,
        )
        if title is None:
            return {"status": "title_not_found"}
        title_status = str(title.get("status") or "").strip().casefold()
        if title_status in {"pago", "liquidado", "recebido", "baixado"}:
            return {"status": "title_already_paid"}
        record = _pix_simulation_store().create(
            request.title_uuid,
            str(title.get("titulo") or title.get("numero") or "-"),
            request.login,
            str(title.get("valor") or "0.00"),
        )
    except (ValueError, httpx.HTTPError) as error:
        return {"status": "error", "reason": str(error) or "mkauth_pix_simulation_failed"}
    return {"status": "simulated", "write_performed": False, "record": record}


@router.get("/mkauth/pix-simulations")
async def list_mkauth_pix_simulations() -> dict:
    records = _pix_simulation_store().list_recent()
    return {"status": "ok", "count": len(records), "records": records}


@router.post("/mkauth/pix-payments")
async def create_mkauth_pix_payment(request: PixRealPaymentRequest) -> dict:
    settings = get_settings()
    if not request.confirmed or request.confirmation_text.strip().upper() != "BAIXAR":
        return {"status": "confirmation_required"}
    if settings.mkauth_mode != "real" or not settings.mkauth_writes_enabled:
        return {"status": "writes_disabled"}
    store = _pix_simulation_store()
    if store.has_real_payment(request.title_uuid):
        return {"status": "duplicate_blocked"}
    try:
        client = MkAuthApiClient(
            settings.mkauth_base_url,
            settings.mkauth_client_id,
            settings.mkauth_client_secret,
            settings.mkauth_verify_ssl,
            settings.mkauth_allow_http and settings.app_env == "development",
        )
        title = await client.get_title(request.title_uuid)
        if str(title.get("login") or "").casefold() != request.login.casefold():
            return {"status": "title_owner_mismatch"}
        paid_statuses = {"pago", "liquidado", "recebido", "baixado"}
        if str(title.get("status") or "").strip().casefold() in paid_statuses or title.get("datapag"):
            return {"status": "title_already_paid"}
        amount = str(title.get("valor") or "").strip()
        if not amount:
            return {"status": "title_amount_missing"}
        await client.receive_title(request.title_uuid, amount, "API", "pix")
        updated = await client.get_title(request.title_uuid)
        updated_status = str(updated.get("status") or "").strip().casefold()
        if updated_status not in paid_statuses and not updated.get("datapag"):
            return {"status": "error", "reason": "mkauth_payment_not_confirmed"}
        record = store.create(
            request.title_uuid,
            str(title.get("titulo") or title.get("numero") or title.get("id") or "-"),
            request.login,
            amount,
            status="real_paid",
        )
        remaining_titles = await client.list_payable_titles(request.login)
        access_resolution = "pending_titles_remain"
        if not remaining_titles:
            client_details = await client.get_client_details(request.login)
            observation = str(client_details.get("observacao") or "").strip().casefold()
            if observation in {"s", "sim", "1", "true", "ativo"}:
                client_uuid = str(client_details.get("uuid") or "").strip()
                if client_uuid:
                    await client.set_client_trust_observation(client_uuid, False)
            active_unlock = _trust_unlock_store().get_active_by_login(request.login)
            if active_unlock:
                _trust_unlock_store().mark_paid(active_unlock["id"])
            access_resolution = "no_pending_titles"
        notification = record_simulated_payment_message(
            request.login,
            str(title.get("titulo") or title.get("numero") or title.get("id") or "-"),
            amount,
            len(remaining_titles),
        )
    except (ValueError, httpx.HTTPError) as error:
        return {"status": "error", "reason": str(error) or "mkauth_pix_payment_failed"}
    return {
        "status": "paid",
        "write_performed": True,
        "access_resolution": access_resolution,
        "remaining_titles": len(remaining_titles),
        "notification": {
            "status": notification["status"],
            "template": notification["template"],
        },
        "record": record,
    }


@router.post("/mkauth/trust-unlock")
async def create_mkauth_trust_unlock(request: TrustUnlockRequest) -> dict:
    settings = get_settings()
    if not request.confirmed:
        return {"status": "confirmation_required"}
    if settings.mkauth_mode != "real" or not settings.mkauth_writes_enabled:
        return {"status": "writes_disabled"}
    try:
        client = MkAuthApiClient(
            settings.mkauth_base_url,
            settings.mkauth_client_id,
            settings.mkauth_client_secret,
            settings.mkauth_verify_ssl,
            settings.mkauth_allow_http and settings.app_env == "development",
        )
        details = await client.get_client_details(request.login)
        blocked = str(details.get("bloqueado") or "").strip().casefold()
        cut_status = str(details.get("status_corte") or "").strip().casefold()
        blocked_indicators = {"s", "sim", "1", "true", "bloq", "bloqueado"}
        if blocked not in blocked_indicators and cut_status not in blocked_indicators:
            return {"status": "not_blocked"}
        expires_at = datetime.now() + timedelta(hours=48)
        await client.set_client_trust_observation(
            request.client_uuid,
            True,
            expires_at,
        )
        updated_details = await client.get_client_details(request.login)
        observation = str(updated_details.get("observacao") or "").strip().casefold()
        if observation not in {"s", "sim", "1", "true", "ativo"}:
            return {"status": "error", "reason": "mkauth_unblock_not_confirmed"}
        audit = _trust_unlock_store().create(
            request.client_uuid, request.login, request.reason.strip()
        )
    except (ValueError, httpx.HTTPError) as error:
        return {"status": "error", "reason": str(error) or "mkauth_trust_unlock_failed"}
    return {"status": "unlocked", "valid_hours": 48, "audit": audit}


@router.get("/mkauth/trust-unlocks")
async def list_mkauth_trust_unlocks() -> dict:
    records = _trust_unlock_store().list_recent()
    return {"status": "ok", "count": len(records), "records": records}


@router.post("/mkauth/trust-unlocks/{record_id}/cancel")
async def cancel_mkauth_trust_unlock(
    record_id: str,
    request: TrustUnlockCancelRequest,
) -> dict:
    settings = get_settings()
    if not request.confirmed:
        return {"status": "confirmation_required"}
    if settings.mkauth_mode != "real" or not settings.mkauth_writes_enabled:
        return {"status": "writes_disabled"}
    store = _trust_unlock_store()
    record = store.get_active(record_id)
    if record is None:
        return {"status": "not_active"}
    try:
        client = MkAuthApiClient(
            settings.mkauth_base_url,
            settings.mkauth_client_id,
            settings.mkauth_client_secret,
            settings.mkauth_verify_ssl,
            settings.mkauth_allow_http and settings.app_env == "development",
        )
        await client.set_client_trust_observation(record["client_uuid"], False)
        details = await client.get_client_details(record["login"])
        observation = str(details.get("observacao") or "").strip().casefold()
        if observation not in {"n", "nao", "não", "0", "false", "inativo"}:
            return {"status": "error", "reason": "mkauth_observation_removal_not_confirmed"}
        store.mark_cancelled(record_id)
    except (ValueError, httpx.HTTPError) as error:
        return {"status": "error", "reason": str(error) or "mkauth_trust_unlock_cancel_failed"}
    return {"status": "cancelled", "record_id": record_id}


async def reconcile_expired_trust_unlocks() -> int:
    settings = get_settings()
    if settings.mkauth_mode != "real" or not settings.mkauth_writes_enabled:
        return 0
    store = _trust_unlock_store()
    expired = store.list_expired_active()
    if not expired:
        return 0
    client = MkAuthApiClient(
        settings.mkauth_base_url,
        settings.mkauth_client_id,
        settings.mkauth_client_secret,
        settings.mkauth_verify_ssl,
        settings.mkauth_allow_http and settings.app_env == "development",
    )
    completed = 0
    for record in expired:
        try:
            await client.set_client_trust_observation(record["client_uuid"], False)
        except (ValueError, httpx.HTTPError):
            continue
        store.mark_expired(record["id"])
        completed += 1
    return completed


@router.get("/routeros/diagnostic")
async def diagnose_routeros() -> dict:
    settings = get_settings()
    if settings.routeros_mode != "real":
        return {"status": "simulated", "read_only": True, "message": "RouterOS real is disabled"}
    if not settings.routeros_username or not settings.routeros_password:
        return {"status": "configuration_error", "read_only": True, "reason": "routeros_credentials_missing"}
    try:
        client = RouterOsReadOnlyClient(
            settings.routeros_host,
            settings.routeros_port,
            settings.routeros_username,
            settings.routeros_password,
        )
        diagnostic = await asyncio.to_thread(client.diagnose)
    except Exception:
        return {"status": "connection_error", "read_only": True, "reason": "routeros_unavailable"}
    radius_entries = diagnostic.get("radius", [])
    enabled_ppp_radius = [
        item
        for item in radius_entries
        if not item.get("disabled") and "ppp" in str(item.get("services") or "").casefold()
    ]
    mkauth_host = urlparse(settings.mkauth_base_url).hostname or ""
    checks = [
        {
            "name": "PPP AAA usando RADIUS",
            "status": "ok" if diagnostic.get("ppp_aaa", {}).get("use_radius") else "warning",
            "detail": "Habilitado" if diagnostic.get("ppp_aaa", {}).get("use_radius") else "Desabilitado no MikroTik",
        },
        {
            "name": "Servidor RADIUS para PPP",
            "status": "ok" if enabled_ppp_radius else "warning",
            "detail": f"{len(enabled_ppp_radius)} entrada(s) ativa(s)" if enabled_ppp_radius else "Nenhuma entrada ativa para PPP",
        },
        {
            "name": "Endereço RADIUS corresponde ao MK-AUTH",
            "status": "ok" if mkauth_host and any(item.get("address") == mkauth_host for item in enabled_ppp_radius) else "warning",
            "detail": (
                f"Correto: {mkauth_host}"
                if mkauth_host and any(item.get("address") == mkauth_host for item in enabled_ppp_radius)
                else f"Esperado: {mkauth_host or 'MK-AUTH não configurado'}"
            ),
        },
        {
            "name": "Accounting PPP",
            "status": "ok" if diagnostic.get("ppp_aaa", {}).get("accounting") else "warning",
            "detail": "Habilitado" if diagnostic.get("ppp_aaa", {}).get("accounting") else "Desabilitado no MikroTik",
        },
    ]
    return {"status": "connected", "read_only": True, "checks": checks, **diagnostic}


@router.get("/mkauth/probe")
async def probe_mkauth() -> dict:
    settings = get_settings()
    if settings.mkauth_mode == "simulated":
        return {
            "status": "simulated",
            "read_only": True,
            "message": "MK-AUTH real is disabled",
        }
    try:
        client = MkAuthApiClient(
            settings.mkauth_base_url,
            settings.mkauth_client_id,
            settings.mkauth_client_secret,
            settings.mkauth_verify_ssl,
            settings.mkauth_allow_http and settings.app_env == "development",
        )
        diagnostic = await client.diagnose()
    except ValueError as error:
        return {
            "status": "configuration_error",
            "read_only": True,
            "reason": str(error),
        }
    except httpx.TimeoutException:
        return {
            "status": "timeout",
            "read_only": True,
            "reason": "mkauth_connection_timeout",
        }
    except httpx.ConnectError:
        return {
            "status": "connection_error",
            "read_only": True,
            "reason": "mkauth_connection_failed",
        }
    except httpx.HTTPStatusError as error:
        return {
            "status": "http_error",
            "read_only": True,
            "http_status": error.response.status_code,
            "reason": "mkauth_rejected_request",
        }
    except httpx.HTTPError:
        return {
            "status": "protocol_error",
            "read_only": True,
            "reason": "mkauth_protocol_failed",
        }
    return {
        "status": "connected",
        "read_only": True,
        **diagnostic,
    }


@router.get("/mkauth/plans")
async def list_mkauth_plans() -> dict:
    settings = get_settings()
    if settings.mkauth_mode != "real":
        return {"status": "simulated", "read_only": True, "plans": []}
    try:
        client = MkAuthApiClient(
            settings.mkauth_base_url,
            settings.mkauth_client_id,
            settings.mkauth_client_secret,
            settings.mkauth_verify_ssl,
            settings.mkauth_allow_http and settings.app_env == "development",
        )
        raw_plans = await client.list_plans()
    except (ValueError, httpx.HTTPError):
        return {
            "status": "unavailable",
            "read_only": True,
            "reason": "mkauth_plans_unavailable",
            "plans": [],
        }

    plans = [
        {
            "uuid": str(item.get("uuid") or ""),
            "name": str(item.get("nome") or item.get("name") or "Sem nome"),
            "price": str(item.get("valor") or item.get("price") or "0.00"),
            "download": str(item.get("veldown") or item.get("download") or "-"),
            "upload": str(item.get("velup") or item.get("upload") or "-"),
        }
        for item in raw_plans
        if isinstance(item, dict)
    ]
    return {
        "status": "connected",
        "read_only": True,
        "count": len(plans),
        "plans": plans,
    }


@router.get("/mkauth/clients")
async def list_mkauth_clients() -> dict:
    settings = get_settings()
    if settings.mkauth_mode != "real":
        return {"status": "simulated", "read_only": True, "clients": []}
    try:
        client = MkAuthApiClient(
            settings.mkauth_base_url,
            settings.mkauth_client_id,
            settings.mkauth_client_secret,
            settings.mkauth_verify_ssl,
            settings.mkauth_allow_http and settings.app_env == "development",
        )
        raw_clients = await client.list_clients()
    except (ValueError, httpx.HTTPError):
        return {
            "status": "unavailable",
            "read_only": True,
            "reason": "mkauth_clients_unavailable",
            "clients": [],
        }

    clients = [
        {
            "uuid": str(item.get("uuid") or ""),
            "name": str(item.get("nome") or item.get("nome_res") or "Sem nome"),
            "login": str(item.get("login") or "-"),
            "connection_type": str(item.get("tipo") or "-"),
            "active": str(item.get("cli_ativado") or "")
            .strip()
            .casefold()
            not in {"n", "nao", "não", "0", "false", "inativo", "desativado"},
            "blocked": str(item.get("bloqueado") or "").strip().casefold()
            in {"s", "sim", "1", "true", "bloq", "bloqueado"}
            or str(item.get("status_corte") or "").strip().casefold()
            in {"s", "sim", "1", "true", "bloq", "bloqueado"},
            "city": str(item.get("cidade") or "-"),
            "state": str(item.get("estado") or "-"),
            "coordinates": str(item.get("coordenadas") or "-"),
            "address": ", ".join(
                part
                for part in (
                    str(item.get("endereco") or "").strip(),
                    str(item.get("numero") or "").strip(),
                    str(item.get("bairro") or "").strip(),
                    str(item.get("cidade") or "").strip(),
                    str(item.get("estado") or "").strip(),
                )
                if part
            ),
        }
        for item in raw_clients
        if isinstance(item, dict)
    ]
    return {
        "status": "connected",
        "read_only": True,
        "count": len(clients),
        "clients": clients,
    }


@router.get("/mkauth/client-details")
async def get_mkauth_client_details(
    login: str = Query(min_length=1, max_length=64),
) -> dict:
    settings = get_settings()
    if settings.mkauth_mode != "real":
        return {"status": "simulated", "read_only": True, "client": None}
    try:
        client = MkAuthApiClient(
            settings.mkauth_base_url,
            settings.mkauth_client_id,
            settings.mkauth_client_secret,
            settings.mkauth_verify_ssl,
            settings.mkauth_allow_http and settings.app_env == "development",
        )
        item = await client.get_client_details(login)
    except (ValueError, httpx.HTTPError):
        return {
            "status": "unavailable",
            "read_only": True,
            "reason": "mkauth_client_details_unavailable",
            "client": None,
        }
    return {
        "status": "connected",
        "read_only": True,
        "client": {
            "name": str(item.get("nome") or item.get("nome_res") or "Sem nome"),
            "login": str(item.get("login") or login),
            "connection_type": str(item.get("tipo") or "-"),
            "plan": str(item.get("plano") or "-"),
            "activated": str(item.get("cli_ativado") or "-"),
            "blocked": str(item.get("bloqueado") or "-"),
            "cut_status": str(item.get("status_corte") or "-"),
            "ip": str(item.get("ip") or item.get("user_ip") or "-"),
            "mac": str(item.get("mac") or item.get("user_mac") or "-"),
            "onu_ont": str(item.get("onu_ont") or "-"),
            "olt_port": str(item.get("porta_olt") or "-"),
            "coordinates": str(item.get("coordenadas") or "-"),
        },
    }


@router.get("/mkauth/additional-clients")
async def list_mkauth_additional_clients() -> dict:
    settings = get_settings()
    if settings.mkauth_mode != "real":
        return {"status": "simulated", "read_only": True, "additional_clients": []}
    try:
        client = MkAuthApiClient(
            settings.mkauth_base_url,
            settings.mkauth_client_id,
            settings.mkauth_client_secret,
            settings.mkauth_verify_ssl,
            settings.mkauth_allow_http and settings.app_env == "development",
        )
        raw_items = await client.list_additional_clients()
    except (ValueError, httpx.HTTPError) as error:
        return {
            "status": "unavailable",
            "read_only": True,
            "reason": str(error) or "mkauth_additional_clients_unavailable",
            "additional_clients": [],
        }
    items = []
    for item in raw_items:
        additional_login = str(
            item.get("login_adicional")
            or item.get("usuario_adicional")
            or item.get("usuario")
            or item.get("user")
            or item.get("username")
            or item.get("adicional")
            or item.get("login")
            or "-"
        )
        owner_login = str(item.get("login") or "-")
        main_login = str(
            item.get("login_principal")
            or item.get("login_titular")
            or item.get("cliente_login")
            or item.get("cliente")
            or item.get("titular")
            or (owner_login if additional_login != owner_login else "-")
        )
        items.append(
            {
                "uuid": str(item.get("uuid") or item.get("uuid_adicional") or ""),
                "name": str(item.get("nome") or item.get("descricao") or "Adicional"),
                "login": additional_login,
                "main_login": main_login,
                "plan": str(item.get("plano") or "-"),
                "active": str(item.get("cli_ativado") or item.get("ativo") or "")
                .strip()
                .casefold()
                not in {"n", "nao", "não", "0", "false", "inativo", "desativado"},
            }
        )
    return {
        "status": "connected",
        "read_only": True,
        "count": len(items),
        "additional_clients": items,
    }


@router.get("/mkauth/titles")
async def list_mkauth_titles(
    login: str | None = None,
) -> dict:
    settings = get_settings()
    if settings.mkauth_mode != "real":
        return {"status": "simulated", "read_only": True, "titles": []}
    try:
        client = MkAuthApiClient(
            settings.mkauth_base_url,
            settings.mkauth_client_id,
            settings.mkauth_client_secret,
            settings.mkauth_verify_ssl,
            settings.mkauth_allow_http and settings.app_env == "development",
        )
        raw_clients = await client.list_clients()
        inactive_values = {"n", "nao", "não", "0", "false", "inativo", "desativado"}
        active_logins = {
            str(item.get("login") or "").strip().casefold()
            for item in raw_clients
            if str(item.get("cli_ativado") or "").strip().casefold() not in inactive_values
        }
        if login and login.strip().casefold() not in active_logins:
            raw_titles = []
        elif login:
            raw_titles = await client.list_payable_titles(login.strip())
        else:
            raw_titles = [
                item
                for item in await client.list_titles()
                if str(item.get("status") or "").strip().casefold() in {"aberto", "vencido"}
                and str(item.get("login") or "").strip().casefold() in active_logins
            ]
        raw_titles.sort(
            key=lambda item: (
                0 if str(item.get("status") or "").strip().casefold() == "vencido" else 1,
                str(item.get("datavenc") or item.get("vencimento") or "9999-12-31"),
            )
        )
    except (ValueError, httpx.HTTPError) as error:
        return {
            "status": "unavailable",
            "read_only": True,
            "reason": str(error) or "mkauth_titles_unavailable",
            "titles": [],
        }
    titles = [
        {
            "uuid": str(item.get("uuid") or ""),
            "login": str(item.get("login") or "-"),
            "number": str(item.get("titulo") or item.get("numero") or "-"),
            "status": str(item.get("status") or "-").strip().casefold(),
            "type": str(item.get("tipo") or "-"),
            "amount": str(item.get("valor") or "0.00"),
            "due_date": str(item.get("datavenc") or item.get("vencimento") or "-"),
        }
        for item in raw_titles
    ]
    return {
        "status": "connected",
        "read_only": True,
        "count": len(titles),
        "titles": titles,
    }


@router.get("/mkauth/tickets")
async def list_mkauth_tickets() -> dict:
    settings = get_settings()
    if settings.mkauth_mode != "real":
        return {"status": "simulated", "read_only": True, "tickets": []}
    try:
        client = MkAuthApiClient(
            settings.mkauth_base_url,
            settings.mkauth_client_id,
            settings.mkauth_client_secret,
            settings.mkauth_verify_ssl,
            settings.mkauth_allow_http and settings.app_env == "development",
        )
        raw_tickets = await client.list_support_tickets()
    except ValueError as error:
        return {
            "status": "unavailable",
            "read_only": True,
            "reason": str(error),
            "tickets": [],
        }
    except httpx.HTTPStatusError as error:
        return {
            "status": "unavailable",
            "read_only": True,
            "reason": f"mkauth_tickets_http_{error.response.status_code}",
            "tickets": [],
        }
    except httpx.HTTPError:
        return {
            "status": "unavailable",
            "read_only": True,
            "reason": "mkauth_tickets_connection_error",
            "tickets": [],
        }

    closed_statuses = {
        "fechado",
        "fechada",
        "encerrado",
        "encerrada",
        "finalizado",
        "finalizada",
        "closed",
    }
    tickets = [
        {
            "uuid": str(item.get("uuid") or ""),
            "number": str(item.get("chamado") or item.get("id") or "-"),
            "opened_at": str(item.get("abertura") or "-"),
            "login": str(item.get("login") or "-"),
            "priority": str(item.get("prioridade") or "normal"),
            "status": str(item.get("status") or "-"),
            "subject": str(item.get("assunto") or "Sem assunto"),
        }
        for item in raw_tickets
        if isinstance(item, dict)
        and str(item.get("status") or "").strip().casefold() not in closed_statuses
    ]
    return {
        "status": "connected",
        "read_only": True,
        "count": len(tickets),
        "tickets": tickets,
    }
