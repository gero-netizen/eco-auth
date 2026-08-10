from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from app.api.routes.central_auth import require_central_access
from app.core.config import get_settings
from app.core.tenant_context import get_current_organization

router = APIRouter(
    prefix="/financial",
    tags=["financial-simulator"],
    dependencies=[Depends(require_central_access)],
)

simulated_financial_accounts: dict[str, dict] = {
    "sim-customer-1": {
        "id": "sim-customer-1",
        "customer_name": "Cliente Financeiro de Bancada",
        "access_status": "blocked",
        "invoice_id": "sim-invoice-1",
        "invoice_amount": 129.90,
        "invoice_status": "overdue",
        "trust_until": None,
        "simulated": True,
    }
}

_accounts_by_organization: dict[str, dict[str, dict]] = {
    get_settings().default_organization_id: simulated_financial_accounts,
}


def _organization_accounts(organization_id: str | None = None) -> dict[str, dict]:
    current_organization_id = organization_id or get_current_organization()
    return _accounts_by_organization.setdefault(current_organization_id, {})


def list_financial_accounts(organization_id: str | None = None) -> list[dict]:
    return list(_organization_accounts(organization_id).values())


def ensure_simulated_account(
    organization_id: str,
    organization_name: str,
    customer_id: str = "sim-customer-1",
) -> dict:
    accounts = _organization_accounts(organization_id)
    if customer_id not in accounts:
        accounts[customer_id] = {
            "id": customer_id,
            "customer_name": f"Cliente de Bancada — {organization_name}",
            "access_status": "blocked",
            "invoice_id": f"sim-invoice-{organization_id}",
            "invoice_amount": 129.90,
            "invoice_status": "overdue",
            "trust_until": None,
            "simulated": True,
        }
    return accounts[customer_id]


def reset_simulated_account(
    customer_id: str, organization_id: str | None = None
) -> dict:
    account = _account(customer_id, organization_id)
    account.update(
        {
            "access_status": "blocked",
            "invoice_status": "overdue",
            "trust_until": None,
        }
    )
    account.pop("paid_at", None)
    return account


def _account(customer_id: str, organization_id: str | None = None) -> dict:
    account = _organization_accounts(organization_id).get(customer_id)
    if account is None:
        raise HTTPException(404, "simulated_customer_not_found")
    return account


@router.get("/accounts")
async def list_accounts() -> list[dict]:
    return list_financial_accounts()


@router.post("/accounts/{customer_id}/trust-unlock")
async def trust_unlock(customer_id: str, redirect: bool = False):
    account = trust_unlock_account(customer_id)
    if redirect:
        return RedirectResponse("/central", status_code=303)
    return account


def trust_unlock_account(
    customer_id: str,
    organization_id: str | None = None,
) -> dict:
    account = _account(customer_id, organization_id)
    account["access_status"] = "trust_released"
    account["trust_until"] = (
        datetime.now(timezone.utc) + timedelta(hours=48)
    ).isoformat()
    return account


@router.post("/accounts/{customer_id}/simulate-pix")
async def simulate_pix(customer_id: str, redirect: bool = False):
    account = simulate_pix_account(customer_id)
    if redirect:
        return RedirectResponse("/central", status_code=303)
    return account


def simulate_pix_account(
    customer_id: str,
    organization_id: str | None = None,
) -> dict:
    account = _account(customer_id, organization_id)
    account["invoice_status"] = "paid"
    account["access_status"] = "active"
    account["trust_until"] = None
    account["paid_at"] = datetime.now(timezone.utc).isoformat()
    return account
