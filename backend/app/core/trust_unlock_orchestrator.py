from datetime import datetime, timedelta, timezone

import httpx

from app.core.trust_unlock_rules_store import trust_unlock_rules_store
from app.core.trust_unlock_store import TrustUnlockStore
from app.integrations.mkauth.api_client import MkAuthApiClient

_BLOCKED_INDICATORS = {"s", "sim", "1", "true", "bloq", "bloqueado"}
_ACTIVE_INDICATORS = {"s", "sim", "1", "true", "ativo"}


async def request_trust_unlock(
    organization_id: str,
    trust_unlock_store: TrustUnlockStore,
    client: MkAuthApiClient,
    login: str,
    reason: str,
) -> dict:
    """Avalia as regras comerciais do provedor e, se todas passarem, libera o
    cliente de verdade no MK-AUTH por tempo limitado. Nenhuma etapa aqui é
    pulada — cada regra reprovada interrompe o processo antes de qualquer
    escrita remota."""
    rules = trust_unlock_rules_store.get(organization_id)

    details = await client.get_client_details(login)
    active = str(details.get("cli_ativado") or details.get("ativo") or "").strip().casefold()
    if active and active not in _ACTIVE_INDICATORS:
        return {"status": "client_disabled"}

    blocked = str(details.get("bloqueado") or "").strip().casefold()
    cut_status = str(details.get("status_corte") or "").strip().casefold()
    if blocked not in _BLOCKED_INDICATORS and cut_status not in _BLOCKED_INDICATORS:
        return {"status": "not_blocked"}

    last_request = trust_unlock_store.get_most_recent_by_login(login)
    if last_request:
        unlocked_at = datetime.fromisoformat(last_request["unlocked_at"])
        if unlocked_at.tzinfo is None:
            unlocked_at = unlocked_at.replace(tzinfo=timezone.utc)
        elapsed_hours = (datetime.now(timezone.utc) - unlocked_at).total_seconds() / 3600
        if elapsed_hours < rules.min_interval_hours:
            return {
                "status": "interval_not_elapsed",
                "hours_remaining": round(rules.min_interval_hours - elapsed_hours, 1),
            }

    since = datetime.now(timezone.utc) - timedelta(days=30)
    unlocks_this_month = trust_unlock_store.count_since(login, since)
    if unlocks_this_month >= rules.max_unlocks_per_month:
        return {"status": "monthly_limit_reached", "limit": rules.max_unlocks_per_month}

    try:
        overdue_titles = await client.list_titles_by_situation(login, "vencido")
    except (ValueError, httpx.HTTPError):
        overdue_titles = []
    if len(overdue_titles) > rules.max_overdue_titles:
        return {
            "status": "too_many_overdue_titles",
            "count": len(overdue_titles),
            "limit": rules.max_overdue_titles,
        }
    total_debt = sum(
        float(str(item.get("valor") or "0").replace(",", ".") or 0)
        for item in overdue_titles
    )
    if total_debt > rules.max_debt_amount:
        return {
            "status": "debt_too_high",
            "amount": round(total_debt, 2),
            "limit": rules.max_debt_amount,
        }

    client_uuid = str(details.get("uuid") or "").strip()
    if not client_uuid:
        return {"status": "error", "reason": "mkauth_client_uuid_missing"}
    expires_at = datetime.now(timezone.utc) + timedelta(hours=rules.duration_hours)
    await client.set_client_trust_observation(client_uuid, True, expires_at)
    updated_details = await client.get_client_details(login)
    observation = str(updated_details.get("observacao") or "").strip().casefold()
    if observation not in _ACTIVE_INDICATORS:
        return {"status": "error", "reason": "mkauth_unblock_not_confirmed"}

    record = trust_unlock_store.create(
        client_uuid, login, reason, duration_hours=rules.duration_hours
    )
    return {
        "status": "unlocked",
        "valid_hours": rules.duration_hours,
        "record": record,
    }
